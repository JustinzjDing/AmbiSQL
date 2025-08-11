xiyan_template_en = """You are an expert in generating {dialect} SQL queries. You must carefully read and understand the following [Database Schema] descriptions and any provided [Evidence] to generate a correct SQL statement answering the [User Question].

Instructions:
- Use only the columns and tables given in the schema.
- Use [Evidence] to clarify vague or ambiguous aspects of the question.
- Output only a valid {dialect} SQL query enclosed in triple backticks, and do not write anything else.

[User Question]
{question}

[Database Schema]
{db_schema}

[Evidence]
{evidence}

[User Question]
{question}

```sql
"""