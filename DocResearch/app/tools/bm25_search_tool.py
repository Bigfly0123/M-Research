"""BM25 Search Tool: 关键词精确检索工具。"""
from typing import List
from app.tools.registry import BaseTool, ToolSpec
from app.retrieval.bm25_retriever import BM25Retriever


class BM25SearchTool(BaseTool):
    spec = ToolSpec(name="bm25_search", description="Keyword search using BM25 algorithm for exact term matching.", input_schema={"query": "str", "top_k": "int"}, output_schema={"chunks": "list[dict]"})

    def __init__(self, retriever: BM25Retriever):
        self.retriever = retriever

    def run(self, query: str, top_k: int = 20, **kwargs) -> dict:
        return {"chunks": self.retriever.retrieve(query, k=top_k)}
