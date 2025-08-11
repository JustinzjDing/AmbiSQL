NodeMerge_prompt = """
## Task
Merge a new question-answer pair into an existing list of question-answer pairs.

## Input
- old_list: an existing list of objects, each with a `question` and `answer` field.
- new_pair: an object with a `question` and `answer` field.

## Merge Instructions
1. Compare the `question` field of `new_pair` with each item in `old_list`. If any question in `old_list` has the same or highly similar meaning as `new_pair` (e.g., the same intent, but possibly different wording), consider it a conflict.
2. If there is a conflict, remove the conflicting item from `old_list` and replace it with `new_pair`.
3. If there is no conflict, append `new_pair` at the end of `old_list`.
4. Ensure the output list contains no duplicate questions (by meaning).
5. Return ONLY the merged list as a valid JSON array, with each item in the format: {{"question": "...", "answer": "..."}}
6. Do NOT return any explanation, comments, or text outside the JSON array.

## Example

Input old_list:
[
    {{"question": "What is your favorite food?", "answer": "Pizza"}},
    {{"question": "What is your hobby?", "answer": "Reading"}}
]
Input new_pair:
{{"question": "What is your favorite food?", "answer": "Sushi"}}

Merged Output:
[
    {{"question": "What is your favorite food?", "answer": "Sushi"}},
    {{"question": "What is your hobby?", "answer": "Reading"}}
]

Input old_list:
[
    {{"question": "What is your favorite color?", "answer": "Blue"}}
]
Input new_pair:
{{"question": "How old are you?", "answer": "28"}}

Merged Output:
[
    {{"question": "What is your favorite color?", "answer": "Blue"}},
    {{"question": "How old are you?", "answer": "28"}}
]

## Now process the given input:

old_list:
{old_list}

new_pair:
{new_pair}

Merged Output:
"""