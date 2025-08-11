import os
import uuid
import json
import time
import re
import sys
from openai import OpenAI

import pandas as pd
import warnings
warnings.simplefilter(action='ignore', category=pd.errors.SettingWithCopyWarning)

import argparse
import asyncio 
import functools
from typing import Callable, Any, TypeVar, Awaitable
from datetime import datetime
from flask import Flask, request, jsonify
from flask_cors import CORS
from pathlib import Path

from question_rewriter import QuestionRewriter
from schema_generator import SchemaGenerator
from utils import format_message, parse_schema_text, add_semicolon_if_missing
from prompts.xiyan_template_prompt import xiyan_template_en
from db_utils import execute_query
# from text2sql.udf_exec_json import LLMEnhancedDBExecutor

CURR_DIR = Path(__file__).resolve().parent
PARENT_DIR = CURR_DIR.parent
sys.path.insert(0, str(PARENT_DIR))

db_path = str((CURR_DIR / "../MINIDEV/dev_databases").resolve())
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# memory-resident session related data
sessions = {}

def sql_generator(question, evidence, schema):
    client = OpenAI(
        base_url='https://api-inference.modelscope.cn/v1/',
        api_key='YOUR_MODELSCOPE_API_KEY', # ModelScope API_KEY
    )

    prompt_raw = xiyan_template_en.format(
        dialect="SQLite",
        question=question,
        db_schema=schema,
        evidence= None
    )
    
    prompt_with_evidence = xiyan_template_en.format(
        dialect="SQLite",
        question=question,
        db_schema=schema,
        evidence= evidence
    )
    
    response_raw = client.chat.completions.create(
        model='XGenerationLab/XiYanSQL-QwenCoder-32B-2504', # ModelScope Model-Id
        messages=[
            {
                'role': 'system',
                'content': 'You are a helpful assistant.'
            },
            {
                'role': 'user',
                'content': prompt_raw
            }
        ]
    )
    sql_raw = response_raw.choices[0].message.content
    
    response_clarified = client.chat.completions.create(
        model='XGenerationLab/XiYanSQL-QwenCoder-32B-2504',
        messages=[
            {
                'role': 'system',
                'content': 'You are a helpful assistant.'
            },
            {
                'role': 'user',
                'content': prompt_with_evidence
            }
        ]
    )
    sql_clarified = response_clarified.choices[0].message.content
    return sql_raw, sql_clarified
    
    
class ChatSession:
    def __init__(self, session_id):
        self.session_id = session_id
        self.db_name = None
        self.question = None
        self.created_at = datetime.now().isoformat()
        self.last_accessed = datetime.now().isoformat()
        self.messages = []
        self.question_rewriter_instance = None  # QuestionRewriter Instance
        self.text2sql_agent = None

    def add_message(self, role, content):
        """Add message to session history"""
        timestamp = datetime.now().isoformat()
        message = {
            "id": str(uuid.uuid4()),
            "role": role,
            "content": content,
            "timestamp": timestamp,
        }
        self.messages.append(message)
        self.last_accessed = timestamp
        return message

    def get_history(self):
        """Get session history"""
        return self.messages

    def clear(self):
        """Clear session history"""
        self.messages = []
        self.last_accessed = datetime.now().isoformat()

    def to_dict(self):
        """transform session object to dict"""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "message_count": len(self.messages),
        }


# Ambiguity Identification
@app.route("/api/sql/analyze", methods=["POST"])
def analyze_sql_query():
    try:
        data = request.json
        client_session_id = data.get("session_id") 

        session_id = None
        current_session = None

        if client_session_id and client_session_id in sessions:
            session_id = client_session_id
            current_session = sessions[session_id]
            current_session.last_accessed = datetime.now().isoformat() 
            print(f"Using existing session: {session_id}")
        else:
            session_id = str(uuid.uuid4())
            current_session = ChatSession(session_id)
            sessions[session_id] = current_session
            print(f"Created new session: {session_id}")

        question = data.get("question", "")
        dialect = data.get("dialect", "SQLite")
        db_name = data.get("db", "")
        current_session.db_name = db_name
        current_session.question = question
        model = "gpt"

        # Get or create session
        if session_id not in sessions:
            sessions[session_id] = ChatSession(session_id)
        current_session = sessions[session_id]

        # Create QuestionRewriter instance and store it to session
        qr_instance = QuestionRewriter(db_name, db_path, question, model)
        print("qr created")  
        current_session.question_rewriter_instance = qr_instance

        # parse schema
        schema_text = qr_instance.schema_generator.db_schema
        parsed_schema = parse_schema_text(schema_text)

        response_json = qr_instance.ambi_detection()
        print(response_json)

        response = json.loads(response_json)
        question_set = response["question_set"]

        response_data = {
            "session_id": session_id,
            "suggested_schema": parsed_schema,
            "analysis": "Schema analysis completed",
            "dialect_info": dialect,
            "ambiguities": question_set,
        }
        return jsonify(response_data), 200

    except Exception as e:
        return (
            jsonify({"error": str(e), "message": "Error processing schema analysis"}),
            500,
        )

@app.route("/api/sql/solve", methods=["POST"])
def solve_ambiguities():
    print("[Solve] Entered solve_ambiguities route.") 
    try:
        # session management
        data = request.json
        print(f"[Solve] Request JSON data: {data}") 
        session_id = data.get('session_id')
        print(f"[Solve] Session ID: {session_id}") 

        if not session_id:
            print("[Solve] No session_id provided, returning 400.") 
            return jsonify({"error": "session_id is required"}), 400

        current_session = sessions.get(session_id)
        print(f"[Solve] Current session object: {current_session}") 
        if not current_session:
            print("[Solve] Session not found or expired, returning 404.") 
            return jsonify({"error": "Session not found or expired"}), 404

        # residual ambiguity identification and question rewrite
        qr_instance = current_session.question_rewriter_instance
        text2sql_agent = current_session.text2sql_agent
        print(f"[Solve] QuestionRewriter instance from session: {qr_instance}") 
        if not qr_instance:
            print("[Solve] QuestionRewriter instance not found in session, returning 400.") 
            return jsonify({"error": "QuestionRewriter instance not found in session. Please call /analyze first."}), 400

        clarification_list = data.get('clarificationList', [])
        print(f"[Solve] Clarification List: {clarification_list}") 
        
        qa_set = []
        for item in clarification_list:
            q_data = item.get('question', {})
            ans = item.get('answer', '')
            qa_set.append({
                "level_1_label": q_data.get('level_1_label', None),
                "level_2_label": q_data.get('level_2_label', None),
                "question": q_data.get('question', None),
                "answer": ans
            })
        print(f"[Solve] Prepared QA Set: {qa_set}") 
            
        additional_info = data.get('additional_info', '')
        print(f"[Solve] Additional Info: {additional_info}")

        formatted_message = format_message(qa_set, additional_info)
        print(f"[Solve] Formatted message: {formatted_message}")

        print("[Solve] Calling qr_instance.process_message for clarification...")
        response_json = qr_instance.ambi_correction(message = formatted_message)
        print(f"[Solve] process_message returned: {response_json}")
         
        parsed_response = json.loads(response_json) 
        print(f"[Solve]Parsed response: {parsed_response}") 
        
        response_data = None
        
        if "has_ambiguity" in parsed_response or parsed_response['is_clarified'] == False:
            response_data = {
                "is_clarified": "False",
                "session_id": session_id,
                "ambiguities": parsed_response['question_set'],
            }
        else:
            sql_raw, sql_clarified = sql_generator(parsed_response['question'], parsed_response['evidence'], qr_instance.schema_generator.formatted_full_schema)
            sql_raw = add_semicolon_if_missing(sql_raw)
            sql_clarified = add_semicolon_if_missing(sql_clarified)
            print(f"Raw SQL parsed: {sql_raw}")
            print(f"Clarified SQL parsed: {sql_clarified}")
            response_data = {
                "session_id": session_id,
                "is_clarified": "True",
                "sql_statement_raw": sql_raw,
                # "result_raw": raw_result,
                "sql_statement_clarified": sql_clarified,
                # "result_clarified": clarified_reuslt
            }

        return jsonify(response_data), 200 
    
    except Exception as e:
        print(f"[Solve Error] An exception occurred: {e}") 
        import traceback
        traceback.print_exc() # print complete traceback
        return jsonify({
            "error": str(e),
            "message": "Error processing ambiguity resolution"
        }), 500

@app.route("/")
def health_check():
    """Server API checkpoint"""
    return "Chat API is running. Use endpoints: /api/chat/start, /api/chat/send, /api/chat/history"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8765))
    app.run(host="0.0.0.0", port=port, debug=True)
