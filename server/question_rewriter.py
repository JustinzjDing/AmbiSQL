from prompts.ambiguity_detection_prompt import (
    QuestionRefine_prompt,
    AmbiguityDetection_prompt,
    RewriteClarificationQuestion_prompt
)
from schema_generator import SchemaGenerator
from preference_index import PreferenceTree
from utils import format_response, parse_json_response

import time
import json

class QuestionRewriter:
    def __init__(self, db_name, path, question, model):
        self.db_name = db_name
        self.path = path
        self.question = question
        self.model = model
        self.schema_generator = SchemaGenerator(db_name, path, question, model)
        self.intention_model = PreferenceTree(model)
        
    def ambi_detection(self):
        flag, question_set = self.check_ambiguity('')
        if flag:          
            question_set = self.rewrite_clarification_question(question_set)
            return format_response(is_clarified=False, q_set=question_set)
        else:
            return self.format_response(self.question, self.intention_model)
        

    def ambi_correction(self, message):
        flag = None
        message_parsed = json.loads(message)
        self.intention_model.update_tree(message_parsed["qa_set"])
        if message_parsed['additional_info'].strip() == '':
            flag = False
        else:
            flag, question_set = self.check_ambiguity(message)
        
        if flag:
            question_set = self.rewrite_clarification_question(question_set)
            return format_response(is_clarified=False, q_set=question_set)
        else:
            return self.format_response(self.question, self.intention_model)
        
    def check_ambiguity(self, message):
        ambiguity_detection_prompt = ""

        if message == '':
            ambiguity_detection_prompt = AmbiguityDetection_prompt.format(
                question=self.question,
                schema=self.schema_generator.db_schema_json,
                evidence=None,
            )
        else:
            message_dict = json.loads(message)
            
            self.question = self.question_refine(message_dict["additional_info"])
            
            ambiguity_detection_prompt = AmbiguityDetection_prompt.format(
                question=message_dict["additional_info"],
                schema=self.schema_generator.db_schema_json,
                evidence=self.intention_model.traverse(),
            )
        query = [
            {
                "role": "system",
                "content": "You are a helpful assistant to find out inherent ambiguity in a natural language statement. Return only the result with no explanation.",
            },
            {"role": "user", "content": ambiguity_detection_prompt},
        ]
        # print(ambiguity_detection_prompt)
        response = self.schema_generator.llm_model.call(query)
        print(response)
        res = parse_json_response(response)

        if res["has_ambiguity"]:
            return res["has_ambiguity"], res["question_set"]
        else:
            return res["has_ambiguity"], None

    def question_refine(self, additional_info):
        # Rewrite question based on new additional info
        question_refine_prompt = QuestionRefine_prompt.format(
            question=self.question, additional_info=additional_info
        )
        query = [
            {
                "role": "system",
                "content": (
                    "You are an expert AI assistant specializing in query refinement. Your purpose is to merge and consolidate user questions with new information."
                    "Respond ONLY with the refined question. Do not add any explanation, formatting, or extra text."
                ),
            },
            {"role": "user", "content": question_refine_prompt},
        ]
        response = self.schema_generator.llm_model.call(query)
        print(response)
        return response

    def rewrite_clarification_question(self, question_set):
        for item in question_set:
            description_str = ""
            if isinstance(item.get('description'), dict):
                description_str = json.dumps(item['description'], indent=2)
            elif isinstance(item.get('description'), str):
                description_str = item['description']

            rewrite_clarification_question_prompt = RewriteClarificationQuestion_prompt.format(
                question=item['question'], description=description_str
            )

            query = [
                {
                    "role": "system",
                    "content": (
                        "You are an AI assistant that strictly follows instructions. "
                        "Your sole task is to output a single, valid JSON object containing a list of strings, "
                        "without any additional text, comments, or markdown."
                    ),
                },
                {"role": "user", "content": rewrite_clarification_question_prompt},
            ]

            try:
                response_str = self.schema_generator.llm_model.call(query)
                
                if "```json" in response_str:
                    response_str = response_str.split("```json")[1].split("```")[0].strip()

                parsed_response = json.loads(response_str)
                
                choices_list = parsed_response.get('choices', [])
                
                if isinstance(choices_list, list) and all(isinstance(c, str) for c in choices_list):
                    item['choices'] = choices_list
                else:
                    print(f"Warning: LLM response for 'choices' was not a list of strings. Got: {choices_list}")
                    item['choices'] = [] 

            except json.JSONDecodeError as e:
                print(f"Error: Failed to decode JSON from LLM response. Error: {e}")
                print(f"Raw response was: {response_str}")
                item['choices'] = []
            except Exception as e:
                print(f"An unexpected error occurred: {e}")
                item['choices'] = []

        return question_set
    
    def format_response(self, question, intention_model):
        response = {
            "is_clarified" : True,
            "question": question,
            "question_set" : None,
            "evidence": intention_model.traverse()
        }
        return json.dumps(response, ensure_ascii=False) 