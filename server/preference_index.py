import json
from collections import defaultdict
from llm_call import LLMCaller
from prompts.preference_tree_prompt import NodeMerge_prompt
from utils import parse_json_response


class TreeNode:
    def __init__(self, level1=None, level2=None, node_type="root"):
        self.level1 = level1
        self.level2 = level2
        self.node_type = node_type  # Options: "root", "level1", "level2", "leaf"
        self.children = dict()  # {index: TreeNode}
        self.qa_list = []  # Only for leaf nodes: list of question-answer dicts


class PreferenceTree:
    def __init__(self, model):
        self.root = TreeNode(node_type="root")
        self.llm_caller = LLMCaller(model=model)
        self.leaf_map = defaultdict(lambda: None)  # (level1, level2) => leaf TreeNode
    
    def update_tree(self, qa_set):
        # qa_set: List[Dict], each with level1_idx, level2_idx, question, answer
        for qa in qa_set:
            self.add_qa(qa["level_1_label"], qa["level_2_label"], qa["question"], qa["answer"])

    def add_qa(self, level1, level2, question, answer):
        """
        Add (or merge) a QA pair at (level1, level2), guaranteeing tree/node existence.
        """
        # Ensure level1 node exists
        if level1 not in self.root.children:
            self.root.children[level1] = TreeNode(level1=level1, node_type="level1")
        l1_node = self.root.children[level1]
        # Ensure level2 node exists
        if level2 not in l1_node.children:
            l1_node.children[level2] = TreeNode(
                level1=level1, level2=level2, node_type="level2"
            )
        l2_node = l1_node.children[level2]
        leaf_key = (level1, level2)
        # Ensure leaf node exists
        if "leaf" not in l2_node.children:
            l2_node.children["leaf"] = TreeNode(
                level1=level1, level2=level2, node_type="leaf"
            )
            self.leaf_map[leaf_key] = l2_node.children["leaf"]
        leaf_node = l2_node.children["leaf"]
        
        if not leaf_node.qa_list:  # is qa_list is empty
            leaf_node.qa_list.append({"question": question, "answer": answer})
        else:
            # LLM merge in leaf nodes
            leaf_node.qa_list = self.node_merge(
                leaf_node.qa_list, {"question": question, "answer": answer}
            )

    def find_leaf(self, level1, level2):
        """
        Return the leaf node at (level1, level2), or None if it doesn't exist.
        """
        return self.leaf_map.get((level1, level2), None)

    def node_merge(self, qa_list, new_qa):
        """
        Use LLM to merge a new QA pair into an existing list of QAs, removing duplicates by semantics.
        """
        node_merge_prompt = NodeMerge_prompt.format(
            old_list=json.dumps(qa_list, ensure_ascii=False, indent=2),
            new_pair=json.dumps(new_qa, ensure_ascii=False, indent=2),
        )

        query = [
            {
                "role": "system",
                "content": (
                    "You are a smart assistant for merging question-answer lists. "
                    "Given an existing list of question-answer pairs and a new question-answer pair, "
                    "your task is to merge them into a new list: "
                    "If the new pair conflicts with any in the list (that is, if their questions have the same meaning), "
                    "replace the old pair with the new one. If there is no conflict, append the new pair to the end of the list. "
                    "Return ONLY the complete merged list as a valid JSON array. Do not include any explanation, comments, or formatting outside of the JSON array."
                ),
            },
            {"role": "user", "content": node_merge_prompt},
        ]
        response = self.llm_caller.call(query)
        print(response)
        response = response.strip('`json\n ')
        print(response)
        return json.loads(response)

    def traverse(self, node=None, depth=0):
        """
        Return a string representation of the entire tree for visualization.
        """
        if node is None:
            node = self.root
        lines = []

        def _traverse(curr_node, curr_depth):
            indent = "  " * curr_depth
            if curr_node.node_type == "leaf":
                for qa in curr_node.qa_list:
                    lines.append(f"{indent}Q: {qa['question']} | A: {qa['answer']}")
            else:
                header = f"{indent}{curr_node.level1 or 'root'} {curr_node.level2 or ''}".strip()
                lines.append(header)
                for child in curr_node.children.values():
                    _traverse(child, curr_depth + 1)

        _traverse(node, depth)
        return "\n".join(lines)
