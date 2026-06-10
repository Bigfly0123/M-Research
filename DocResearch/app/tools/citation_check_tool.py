"""Citation Check Tool: 引用合法性检查工具。"""
import re
from typing import List
from app.tools.registry import BaseTool, ToolSpec


class CitationCheckTool(BaseTool):
    spec = ToolSpec(name="citation_check", description="Validate citation IDs in answer against context_pack.", input_schema={"answer": "str", "valid_ids": "list[str]"}, output_schema={"invalid_citations": "list[str]", "missing_citations": "bool"})

    def run(self, answer: str, valid_ids: List[str], **kwargs) -> dict:
        found = re.findall(r'\[([A-Za-z0-9_-]+-C\d+)\]', answer)
        found_set = set(found)
        valid_set = set(valid_ids)
        invalid = list(found_set - valid_set)
        return {"invalid_citations": invalid, "missing_citations": len(found_set) == 0}
