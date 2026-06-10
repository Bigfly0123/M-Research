"""Dense Search Tool: 向量语义检索工具。"""
from typing import List
from app.tools.registry import BaseTool, ToolSpec
from app.retrieval.dense_retriever import DenseRetriever


class DenseSearchTool(BaseTool):
    spec = ToolSpec(name="dense_search", description="Semantic similarity search using vector embeddings via ChromaDB.", input_schema={"query": "str", "top_k": "int"}, output_schema={"chunks": "list[dict]"})

    def __init__(self, retriever: DenseRetriever):
        self.retriever = retriever

    def run(self, query: str, top_k: int = 20, **kwargs) -> dict:
        return {"chunks": self.retriever.retrieve(query, k=top_k)}
