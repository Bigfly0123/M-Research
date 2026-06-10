"""
Rerank Tool: CrossEncoder 重排序工具，封装 hybrid_retriever._rerank 逻辑。
"""
from typing import List
from app.tools.registry import BaseTool, ToolSpec
from app.config import config


class RerankTool(BaseTool):
    spec = ToolSpec(
        name="rerank",
        description="Re-rank retrieved chunks using CrossEncoder for query-document relevance.",
        input_schema={"query": "str", "chunks": "list[dict]"},
        output_schema={"reranked_indices": "list[int]", "scores": "list[float]"},
    )

    def run(self, query: str, chunks: List[dict], **kwargs) -> dict:
        try:
            from sentence_transformers import CrossEncoder
            reranker = CrossEncoder(config.RERANKER_MODEL)
            texts = [c.get("text", "")[:512] for c in chunks]
            pairs = [(query, t) for t in texts]
            scores = reranker.predict(pairs).tolist()
            indexed = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
            return {"reranked_indices": indexed, "scores": [scores[i] for i in indexed]}
        except Exception as e:
            return {"reranked_indices": list(range(len(chunks))), "scores": [0.0] * len(chunks)}
