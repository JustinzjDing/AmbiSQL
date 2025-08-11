import sys
import json
from openai import OpenAI
from pathlib import Path
from question_rewriter import QuestionRewriter
from utils import format_message, add_semicolon_if_missing
from prompts.xiyan_template_prompt import xiyan_template_en

CURR_DIR = Path(__file__).resolve().parent
PARENT_DIR = CURR_DIR.parent
sys.path.insert(0, str(PARENT_DIR))  

from schema_generator import SchemaGenerator

db_path = str((CURR_DIR / '../MINIDEV/dev_databases').resolve())

questions = [
    ("db_used", "Input database name: "),
    ("question", "Input query question: "),
    ("lm_model", "Input language model name: ")
]

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

args = {}
init_flag = True
question_set = None
qr = None

while True:
    response_json = ''
    if init_flag:
        for key, prompt in questions:
            ans = input(prompt)
            args[key] = ans

        db_name = args["db_used"]
        question = args["question"]
        model = args["lm_model"]
        init_flag = False
        
        qr = QuestionRewriter(db_name, db_path, question, model)
        response_json  = qr.ambi_detection()
        # print(response_json)

    else:
        q_set = question_set
        qa_set = []
        for q in q_set:
            formatted_q = f"Question: {q['question']}\nDescription: {q['description']}\n"
            ans = input(formatted_q)
            qa_set.append({"level_1_label": q['level_1_label'], "level_2_label": q['level_2_label'] , "question": q, "answer": ans})
        additional_info = input("Do you have some additional info for this query: ")

        formatted_message = format_message(qa_set, additional_info)
        # print(formatted_message)
        response_json = qr.ambi_correction(message = formatted_message)
        
  
    response = json.loads(response_json) 
    question_set = response['question_set']
    if response['is_clarified'] == True:
        print('Disambiguous Finished')
        print(f"New Question: {response['question']}")
        print(f"Evidence: {response['evidence']}")
        
        sql_raw, sql_clarified = sql_generator(response['question'], response['evidence'], qr.schema_generator.formatted_full_schema)
    
        sql_raw = add_semicolon_if_missing(sql_raw)
        sql_clarified = add_semicolon_if_missing(sql_clarified)
        print(f"Raw SQL parsed: {sql_raw}")
        print(f"Clarified SQL parsed: {sql_clarified}")
        
        break
        