from llm_call import LLMCaller
from prompts.schema_linking_prompt import SelectColumns_prompt

import sqlite3
import os
import json
import re
import pandas as pd

class SchemaGenerator:
    def __init__(self, db_name, path, question, model):
        self.db_name = db_name
        self.path = path
        self.question = question
        self.llm_model = LLMCaller(model = model)
        self.db_schema, self.db_schema_json = self.filter_schema()
        self.formatted_full_schema, self.formatted_full_schema_json = self.obtain_db_schema(self.path, self.db_name)
        
    def filter_schema(self):
        db_schema, db_schema_json = self.obtain_db_schema(self.path, self.db_name)
        Select_Columns = [{"role": "system", "content": "You are an expert and very smart data analyst."}, {'role': 'user', 'content': SelectColumns_prompt.format(DATABASE_SCHEMA = db_schema, QUESTION = self.question)}]
        columns = self.llm_model.call(Select_Columns)
        columns_json = json.loads(columns.strip('```json\n'))
        try:
            filter_columns = f"{self.db_name} database outlines the table names and their respective columns. Each column is detailed in this order: column_name, is_PrimaryKey, data_type, column_description, value_description, and value_example. \n\n"
            for table, columns in columns_json.items():
                if table != 'explanation':
                    filter_columns += f"\nTable: {table}\n"
                    for column in columns:
                        filter_columns += (f" - {column}:" + ', '.join(re.sub(r'\s+', ' ', str(value)).strip()  for value in db_schema_json[table][column].values()) + "\n")               
            return filter_columns, db_schema_json
        except:
            return db_schema, db_schema_json

    def obtain_db_schema(self, path, db):
        conn = sqlite3.connect(f"{path}/{db}/{db}.sqlite")
        cursor = conn.cursor()
        schema_path = f'{path}/{db}/schema.csv'
        result = f"The following schema from the {db} database outlines the table names and their respective columns. Each column is detailed in this order: column_name, is_PrimaryKey, data_type, column_description, value_description, and value_example. \n\n"
        with open(schema_path, 'w') as w_file:
            w_file.write(result)
        csv_path = path+'/'+db+'/database_description/'
        table_info_str = ''
        schema_json = {}
        for filename in os.listdir(csv_path):
            if filename.endswith('.csv'):
                file_path = os.path.join(csv_path, filename)
                table = filename[:-4]
                with open(schema_path, 'a') as w_file:
                    w_file.write(f"\nTable: {table}\n")
                table_info = pd.read_csv(file_path)
                table_info = table_info.drop(columns=['column_name'])
                table_info = table_info.rename(columns={'original_column_name': 'column_name'})
                table_info = table_info[['column_name', 'column_description', 'value_description']]
                table_info['column_name'] = table_info['column_name'].astype(str).str.strip()
                cursor.execute(f"PRAGMA table_info({table});")
                columns_info = cursor.fetchall()
                columns_df = pd.DataFrame(columns_info, columns=['cid', 'name', 'type', 'notnull', 'dflt_value', 'pk'])
                columns_df = columns_df[['name', 'pk', 'type']]
                columns_df = columns_df.rename(columns={'name': 'column_name', 'type': 'data_type'})
                columns_df['pk'] = columns_df['pk'].apply(lambda x: 'Primary Key' if x == 1 else '')
                self.check_merge(set(columns_df['column_name']), set(table_info['column_name']))
                table_info = pd.merge(columns_df, table_info, on='column_name', how='left')
                table_info['value_examples'] = None
                for column_name in table_info['column_name']:
                    cursor.execute(f"SELECT DISTINCT [{column_name}] FROM {table} LIMIT 3;")
                    distinct_values = [row[0] for row in cursor.fetchall()]
                    table_info.loc[table_info['column_name'] == column_name, 'value_examples'] = str(distinct_values)

                with open(schema_path, 'a') as w_file:
                    table_info_str = table_info.to_csv(sep=',', index=False, header=False)
                    w_file.write(table_info_str)
                
                result += f"\nTable: {table}\n{table_info_str}"
                schema_json[table] = table_info.set_index('column_name').to_dict(orient='index')
        cursor.close()
        conn.close()
        return result, schema_json

    def check_merge(self,columns_in_columns_df, columns_in_table_info):
        missing_in_table_info = columns_in_columns_df - columns_in_table_info
        missing_in_columns_df = columns_in_table_info - columns_in_columns_df

        if missing_in_table_info or missing_in_columns_df:
            print("⚠️ Column mismatch detected:")
            if missing_in_table_info:
                print(f" - Missing in table_info: {sorted(missing_in_table_info)}")
                raise ValueError("Column mismatch between table_info and columns_df. See printout above.")
            if missing_in_columns_df:
                print(f"There are redundant columns in database_description:: {sorted(missing_in_columns_df)}")
                