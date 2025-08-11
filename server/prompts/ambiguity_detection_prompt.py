AmbiguityDetection_prompt = """
## Task
Given a user's question(or statement), database schema, and optional evidence, identify any ambiguities and generate clarifying questions to resolve them.

## Definitions:
- A user question is identifies as ambiguous when there is more than one reasonable interpretation due to unclear, incomplete, or conflicting information.
- Level 1:
    - "DB-related ambiguity": Ambiguity that leads to incorrect or incomplete data retrieval directly from the database, due to unclear or underspecified aspects of the user query with respect to the database schema or content.
    - "LLM-related ambiguity": Ambiguity that results in the misuse of LLM external knowledge, causing difficulties in correctly retrieving or applying information beyond the database.
- Level 2 examples:
    - DB-related:
        - "Unclear schema reference": The question lacks sufficient context to determine which table or column to use for operations like filtering, ranking, or aggregation, resulting in multiple plausible interpretations (e.g., "the oldest user" could refer to 'age' column or 'registration_date' column).
        - "Unclear value reference": The question refers to a value that does not correctly correspond to the actual values stored in the database, making it unclear how to formulate the WHERE clause condition and potentially causing relevant results to be omitted or producing inaccurate results.
          - (e.g., querying posts mentioning the "R programming language" without clarifying whether to match exact phrases or variations).
          - (e.g., querying for "New York City" when the database stores "NYC" or asking for posts about "COVID-19" when the database contains "coronavirus")
        - "Missing SQL-related keywords": Key terms clarifying the intended operation are absent, leading to ambiguity about the desired SQL operation (e.g., query for top 5 popular tags's star, which can list each tag's star or the amount stars).
    - LLM-related:
        - "Unclear knowledge source": The question fails to specify whether required information should be retrieved from the database or inferred through LLM reasoning (e.g., for "female employees," whether to query a gender column or use semantic analysis of name fields).
        - "Insufficient reasoning context": The question lacks adequate information to guide LLM reasoning effectively (e.g., requesting dynamic or time-sensitive external information like "current exchange rate" without specifying the target currencies or date).
        - "Conflicting knowledge": Knowledge assumptions embedded within the question contradicts real-world facts or database contents (e.g., querying entities or participants in events that never occurred).
        - "Ambiguous temporal/spatial scope": Spatial or temporal constraints are underspecified, resulting in multiple possible interpretations at different granularities 
          - (e.g., "after the 2018 World Cup" could mean immediately after the final match or after the entire tournament year).
          - (e.g., missing countries in the list for "Middle East" due to vague or imprecise geographic constraints).

## Instructions:
1. Identify all ambiguous phrases in the question (using schema and evidence if provided).
2. For each unresolved ambiguity, write a clarifying (yes/no, binary, or multiple-choice) question for user to further clarify their intent.
3. For each, assign exactly one Level 1 and one Level 2 label.
4. For each, provide a brief user-facing description. Formulate the descroption of each ambiguity as follows:
  i. For "Unclear schema reference", list all plausible columns with relevant schema info retrieved from the input database schema.
  ii. For "Ambiguous temporal/spatial scope", include all possible answers in complete in description for user to select(Do not use such as or etc to omit some options).
  iii. For "Unclear value reference", "Missing SQL-related keywords", "Unclear knowledge source", "Insufficient reasoning context" or "Conflicting knowledge", List some possible interpretations as choices(more then 2).
5. **Important Note**: Not each input question is ambiguous. If no ambiguities remain, return an empty question_set. (e.g., If only one column in the database is plausible, it should not be an unclear schema reference)


## Response format (strict JSON):
{{
  "has_ambiguity": true/false,
  "question_set": [
    {{
      "question": "string",
      "level_1_label": "DB-related ambiguity | LLM-related ambiguity",
      "level_2_label": "string",
      "description": "string or JSON object"
    }}
  ]
}}

## Example:
User Question: List all basketball players born before the end of 2018 NBA season who got the most points.
Response:
{{
  "has_ambiguity": true,
  "question_set": [
    {{
      "question": "Which column in the 'nba_basketball_player' database should be used to determine player who got the most points?",
      "level_1_label": "DB-related ambiguity",
      "level_2_label": "Unclear schema reference",
      "description": {{
        "columns": [
          {{"table_name": "yearRecored", "column_name": "record_rank", "column_description": "pointing record the player ranked in one year."}},
          {{"table_name": "matches", "column_name": "rank", "column_description": "pointing rank of the player in a specific match."}},
          {{"table_name": "season", "column_name": "position", "column_description": "pointing record of a player in one season."}}
        ]
      }}
    }},
    {{
      "question": "Do you mean basketball players born before the start day, end day or year of the 2018 NBA season?",
      "level_1_label": "LLM-related ambiguity",
      "level_2_label": "Ambiguous temporal/spatial scope",
      "description": "The start day is 2017-10-17, the end day is 2018-06-08, the end year is 2018."
    }}
  ]
}}

Input:
Question: {question}
Schema: {schema}
Evidence: {evidence}

Respond only with the JSON answer.
"""


AmbiguityDetection_prompt_old = ''' 
## Task
Analyze the provided user question for potential ambiguities and, if any are found, generate clarifying questions for the user to resolve these ambiguities.

## Input
- **question**: The user's question, expressed in natural language.
- **schema**: Complete Table schema and database metadata.
- **evidence**: User-supplied notes that may clarify ambiguities in the question.

## Ambiguity Definition
Ambiguity is present when the question has more than one specific interpretations and cannot be answered precisely due to unclear, incomplete, or conflicting information. 
Ambiguities are categorized into two level as follows:

Level-1 classification label: **DB-related ambiguity** and **LLM-related ambiguity**
- **DB-related ambiguity**: Ambiguities that result in errors during plan generation, SQL construction, or execution.
- **LLM-related ambiguity**:  Ambiguities that cause LLM misuse or lead to semantic reasoning errors.

Level-2 classification labels for DB-related ambiguity:
- **Unclear column reference**: Multiple columns may be plausible choices for filtering, projection, ranking, or aggregation.
  - Example: Question: "List the username of the oldest user located in the capital city of Austria who obtained the Supporter badge?" Explanation: both the user's age and registration date could be interpreted as indicators of being "oldest."
  - Example: Question: "Which of these circuits is located closer to a capital city, Silverstone Circuit, Hockenheimring or Hungaroring?" Explanation: both "CircuitId", "CircuitName", "Latitude", "Longitutde", "Country" or combinations of these columns can be represented as the circuit.
- **Unclear value reference**: When LLM use a clasue "Like" to determine somecase where not all possible conditions might be enumerated.
  - Example: Question: "how many discuss \textit{the R programming language} in the post body". Explanation: LLMs often use a clause such as \texttt{LIKE '\%R programming language\%'}, which might not cover all possible textual variations, leading to incomplete or imprecise results.
- **Missing SQL-related keywords**:  When key terms such as “overall,” “each,” or “total” are omitted, LLM may misinterpret the user's intent. 
  - Example: Question:"What is the number of schools whose ...". Explanation: the model might enumerate school details rather than count them unless the question explicitly asks for the "total number."
  
Level-2 classification labels for LLM-related ambiguity:
- **Incorrect external knowledge retrieval**: the external knowledge retrieved by LLM might be wrong.
  - Example: Question: "list countries in the Middle East". Explanation: state-of-the-art LLMs might include Azerbaijan, which is traditionally not considered part of the Middle East.
- **Floating data retrieval**: Ambiguity arises when the query requires dynamic information such as stock prices or currency exchange rates.
  - Example: Question: "List all transanctions with a price of over 50 US dollars". Explanation: the transanction might be in EUR as unit, and LLM's knowledge about EUR's exchange rate to USD varies.
- **Unclear constraint reference**: The constraints condition which should be retrieved by LLM have multiple reasonable interpretations.
  - Example: Question: Queries like "after the 14th FIFA World Cup" or "after the Vietnam War" are ambiguous, as "after" could be interpreted as either the end year or the exact end date.
- **Unclear LLM usage**: The bountries to use either LLM or database manipulation is unclear.
  - Example: Question: querying for "football players taller than Bill Clinton," the LLM may attempt to retrieve Bill Clinton's height from the database, even though this information should be provided directly by the LLM.
- **Contradictory facts**: parts of the query are fabricated information which is not exists at all.
  - Example: In cases such as "drivers who competed in the 2008 United States Grand Prix," the LLM may attempt to fetch data for an event that never took place, resulting in fabricated answers.

## Analysis Steps
Please follow these steps precisely:
1. **Identify Inherent Ambiguities**: Analyze the user's question and the evidence, referring to the definition and classification above, to identify any inherent ambiguities.
2. **Check for Clarifications**: Determine if any evidence provided resolves these ambiguities.
3. **Generate Clarifying Questions**: For each remaining ambiguity, generate a clarifying question. Only use unary (yes/no), binary, or multiple-choice question formats that are precise and easy for a user to answer.
4. **Add labels for each question**: Each generated question should be labeled with one and only one Level-1 classification label and Level-2 classification label.
5. **Add descriptions for each question**: Each generated question should have a description of each choice option for users to refere to.

If no ambiguities remain, return an empty list for "question_set".

## Response Format
Respond strictly in this JSON format:
```json
{{
  "has_ambiguity": true/false,
  "question_set": [
      {{
        "question": "...question 1...",
        "level_1_label: "...",
        "level_2_label: "...",
        "description": "......"
      }},
      {{
        "question": "...question 2...",
        "level_1_label: "...",
        "level_2_label: "...",
        "description": "......"
      }},
      {{
        "question": "...question N..."
        "level_1_label: "...",
        "level_2_label: "...",
        "description": "......"
      }}
  ]
}}

## Clarification Questions Example
User input question:'How many drivers born after the end of Vietnam War have been ranked 2?'

Response: 
```json
{{
  "has_ambiguity": true,
  "question_set": [
    {{
        "question": "Do you want the number of drivers born after the end day or the end year of Vietnam War?",
        "level_1_label: "LLM-related ambiguity",
        "level_2_label: "Unclear constraint reference",
        "description": "the end day of Vietnam War is 1975-4-30 and the end year is 1975."
    }},
    {{
        "question": "Which column in formula_1 database do you think should be used to evaluate drivers ranking.",
        "level_1_label: "DB-related ambiguity",
        "level_2_label: "Unclear column reference",
        "description": {{
            "columns": [
                {{"table_name": "driverStandings", "column_name": "position", "column_description": "position or track of circuits"}},
                {{"table_name": "driverStandings", "column_name": "positionText", "column_description": "same with position, not quite useful"}},
                {{"table_name": "results", "column_name": "rank", "column_description": "starting rank positioned by fastest lap speed"}}
            ]
        }}
    }}   
  ]
}}

Question:{question}

Schema:{schema}

Evidence:{evidence}

Answer:
'''

QuestionRefine_prompt = '''
# Task
To combine an `original_question` with `additional_information` into a single, coherent, and complete new question that is logically sound and easy to understand.

# Core Principles
1.  **Absolute Preservation**: You MUST preserve ALL constraints, details, and intents from the `original_question`. Nothing from the original should be omitted or altered unless it is directly and explicitly contradicted by the `additional_information`.
2.  **Full Integration**: You MUST seamlessly integrate ALL new requirements and constraints from the `additional_information` into the new question.
3.  **Conflict Resolution**: If a piece of `additional_information` directly conflicts with a part of the `original_question`, the `additional_information` takes precedence and should be used to update or replace the conflicting part. This is the **only** scenario where original information may be modified.
4.  **Natural Language**: The final output must be a single, natural-sounding question, not a list of criteria.

# Examples
Original question: List all novels published after 2000 that won a Booker Prize.
Additional information: Only include novels that were also adapted into movies and written by female authors.
Rewritten question: List all novels published after 2000 that won a Booker Prize, were adapted into movies, and were written by female authors.

Original question: Which Asian countries have a GDP per capita above $30,000 and a population under 10 million?
Additional information: Exclude countries that are island nations.
Rewritten question: Which Asian countries that are not island nations have a GDP per capita above $30,000 and a population under 10 million?

Original question: Provide the list of Olympic gold medalists in swimming events for the last three Summer Olympics, including their ages at the time of winning.
Additional information: I am only interested in male athletes from North America, and only in individual events.
Rewritten question: Provide the list of male North American Olympic gold medalists in individual swimming events for the last three Summer Olympics, including their ages at the time of winning.

# Response Format
- Return **only** the text of the rewritten question.
- Do not include any preamble, labels (like "Rewritten question:"), or explanations.

---

Original question: {question}

Additional information: {additional_info}

Rewritten question:
'''

RewriteClarificationQuestion_prompt = '''
# Role
You are an expert AI assistant that excels at simplifying complex technical information into clear, user-friendly, multiple-choice options.

# Task
Your task is to analyze a clarification question and its accompanying description. Based on this, you must generate a list of choices. 
Each choice should be a self-contained, natural language sentence that is easy for a non-technical user to understand and select.
- Make sure all choices follow similar formats (e.g, choice + explanation/evidence) 
- If there is a "Unclear column reference", list all column choices with "column_name, table_name, column_description" in a descriptive sentence.

## Input
- **Question**: The clarification question that needs to be answered.
- **Description**: The context or data containing the potential answers. This can be a simple string or a structured JSON object.

## Output format
You MUST respond with ONLY a single, valid JSON object. The object must contain a single key, "choices", which is a list of strings. Do NOT add any other text, explanations, or markdown formatting.

Input question: {question}
Input description: {description}
### Example:
---
**Input:**
- Question: "Do you mean drivers born after the end day or the end year of the Vietnam War?"
- Description: "The end day is 1975-04-30, the end year is 1975."

**Correct Output:**
```json
{{
  "choices": [
    "End Day: April 30, 1975.",
    "End Year: Dec 31, 1975."
  ]
}}
'''