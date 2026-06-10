"""Graph Expand Tool: 轻量 term graph 扩展工具。"""
from typing import List
from app.tools.registry import BaseTool, ToolSpec


class GraphExpandTool(BaseTool):
    spec = ToolSpec(name="graph_expand", description="Expand related technical terms and chunks using lightweight term graph.", input_schema={"terms": "list[str]", "max_hops": "int"}, output_schema={"expanded_terms": "list[str]", "related_chunks": "list[str]"})

    def __init__(self, graph_index):
        self.graph_index = graph_index

    def run(self, terms: List[str], max_hops: int = 1, **kwargs) -> dict:
        expanded_terms = set()
        related_chunks = set()
        for term in terms:
            expansion = self.graph_index.expand(term, max_hops=max_hops)
            expanded_terms.update(expansion.expanded_terms)
            related_chunks.update(expansion.related_chunks)
        return {"expanded_terms": list(expanded_terms), "related_chunks": list(related_chunks)}
