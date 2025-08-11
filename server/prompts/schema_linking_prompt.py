SelectColumns_prompt = '''
# Column Selection Task

Your task is to identify all columns across database tables that are relevant to answering a given question.

## Database Schema
{DATABASE_SCHEMA}

## Question
{QUESTION}

## Selection Criteria
Select columns that are:
1. Directly referenced in the question (explicitly or through synonyms)
2. Logically necessary to derive the answer
3. Required join keys to connect selected tables
4. Potentially useful for downstream processing

## Important Rules
- Focus only on identifying relevant columns, not on SQL construction
- Always double-check that you've included BOTH sides of every needed join (e.g., if `TableA.key = TableB.key`, include both columns). For any two tables involved, trace the **shortest valid join path** and include **all columns used in the join**, even if they are not directly mentioned in the question.
- Only include tables that have at least one selected column
- Verify all columns actually exist in their specified tables according to the schema
- Trace the full join path when tables are not directly related

## Output Format
{{
  "explanation": "Explain clearly and concisely why each table and column was selected, and how join keys enable combining data across tables.",
  "table_name1": ["column1", "column2", ...],
  "table_name2": ["column1", "column2", ...],
  ...
}}

Your response must be a plain JSON string only, with no additional text, explanations, or formatting.
'''