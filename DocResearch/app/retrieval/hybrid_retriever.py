"""
Hybrid Retriever: 三路混合检索器 (Day4 完善)。

融合 Dense + BM25 + Graph Expansion 三路检索，
通过多路召回 → merge/dedup → score fusion → optional rerank → top-k 生成最终排序。

Day4 增强:
- 使用 GraphRetriever 独立模块做第三路检索
- Graph 路的 chunk 也参与 dedup/merge (与 dense/bm25 命中同一 chunk 时合并分数)
- 完善三路融合权重 + 多路命中 bonus
- 支持 ablation: dense_only / bm25_only / graph_only / dense_bm25 / full
"""

import os
import time
from typing import List, Optional, Literal

from app.config import config
from app.schemas.retrieval import RetrievedChunk, HybridRetrievalConfig, RetrievalOutput
from app.retrieval.bm25_retriever import BM25Retriever
from app.retrieval.graph_retriever import GraphRetriever
from app.retrieval.graph_index import LightweightGraphIndex


def _get_dense_retriever():
    """根据 DENSE_BACKEND 配置选择 dense 后端: faiss(默认) 或 chroma。"""
    backend = config.DENSE_BACKEND.lower()
    if backend == "faiss":
        from app.retrieval.dense_retriever_faiss import DenseRetrieverFAISS
        return DenseRetrieverFAISS()
    elif backend == "chroma":
        from app.retrieval.dense_retriever import DenseRetriever
        return DenseRetriever()
    else:
        raise ValueError(f"Unknown DENSE_BACKEND: {backend}, expected 'faiss' or 'chroma'")


_reranker = None


def get_reranker():
    """懒加载 CrossEncoder reranker。"""
    global _reranker
    if _reranker is None:
        from sentence_transformers import CrossEncoder
        _reranker = CrossEncoder(config.RERANKER_MODEL)
    return _reranker


class HybridGraphRetriever:
    """
    三路混合检索器: Dense + BM25 + Graph Expansion。

    用法:
        retriever = HybridGraphRetriever()
        retriever.build_index(chunks, index_dir)
        result = retriever.retrieve("query", retrieval_plan=["dense", "bm25", "graph_expand"])
    """

    def __init__(self):
        self.dense = _get_dense_retriever()
        self.bm25 = BM25Retriever()
        self.graph_index = LightweightGraphIndex()
        self.graph_retriever = GraphRetriever(graph_index=self.graph_index)
        self._chunks_by_id: dict = {}

    def close(self):
        """安全关闭所有索引连接。"""
        if self.dense and hasattr(self.dense, 'close'):
            self.dense.close()

    def __del__(self):
        self.close()

    def build_index(self, chunks: List[dict], index_dir: str):
        """构建所有索引: Dense + BM25 + Graph。"""
        dense_dir = "faiss_index" if config.DENSE_BACKEND.lower() == "faiss" else "chroma_db"
        self.dense.build_index(chunks, persist_dir=os.path.join(index_dir, dense_dir))
        self.bm25.build_index(chunks, index_dir=index_dir)
        self.graph_index.build(chunks)
        self.graph_index.save(os.path.join(index_dir, "graph_index.json"))
        self._chunks_by_id = {c.get("chunk_id", f"idx-{i}"): c for i, c in enumerate(chunks)}
        self.graph_retriever = GraphRetriever(graph_index=self.graph_index, chunks_by_id=self._chunks_by_id)

    def load_index(self, index_dir: str) -> bool:
        """加载已有索引。"""
        dense_dir = "faiss_index" if config.DENSE_BACKEND.lower() == "faiss" else "chroma_db"
        dense_ok = self.dense.load_index(os.path.join(index_dir, dense_dir))
        bm25_ok = self.bm25.load_index(index_dir)
        graph_ok = self.graph_index.load(os.path.join(index_dir, "graph_index.json"))
        if graph_ok:
            self.graph_retriever = GraphRetriever(graph_index=self.graph_index, chunks_by_id=self._chunks_by_id)
        return dense_ok or bm25_ok or graph_ok

    def retrieve(
        self,
        query: str,
        retrieval_plan: List[str] = None,
        top_k: int = None,
        fetch_k: int = None,
        use_rerank: bool = None,
        graph_max_hops: int = 1,
        graph_max_terms: int = 5,
    ) -> RetrievalOutput:
        """主入口: 三路检索 → merge/dedup → score fusion → rerank → top-k。

        Args:
            query: 查询文本
            retrieval_plan: 启用哪些检索路 ["dense", "bm25", "graph_expand"]
            top_k: 最终返回数量
            fetch_k: dense/bm25 每路召回数量
            use_rerank: 是否 rerank
            graph_max_hops: graph 扩展最大跳数
            graph_max_terms: graph 从查询中抽取的最大术语数

        Returns:
            RetrievalOutput: 含 chunks/source_stats/trace
        """
        start = time.time()

        if retrieval_plan is None:
            retrieval_plan = ["dense", "bm25", "graph_expand"]
        if top_k is None:
            top_k = config.FINAL_TOP_K
        if fetch_k is None:
            fetch_k = config.DENSE_TOP_K
        if use_rerank is None:
            use_rerank = config.USE_RERANK

        # 1. 多路召回
        all_chunks: dict[str, RetrievedChunk] = {}
        source_stats = {"dense": 0, "bm25": 0, "graph_expand": 0}

        # Dense 路召回
        if "dense" in retrieval_plan:
            dense_results = self.dense.retrieve(query, k=fetch_k)
            source_stats["dense"] = len(dense_results)
            for chunk in dense_results:
                cid = chunk.chunk_id
                if cid in all_chunks:
                    all_chunks[cid].dense_score = chunk.dense_score
                    if "dense" not in all_chunks[cid].retrieval_sources:
                        all_chunks[cid].retrieval_sources.append("dense")
                else:
                    all_chunks[cid] = chunk

        # BM25 路召回
        if "bm25" in retrieval_plan:
            bm25_results = self.bm25.retrieve(query, k=fetch_k)
            source_stats["bm25"] = len(bm25_results)
            for chunk in bm25_results:
                cid = chunk.chunk_id
                if cid in all_chunks:
                    all_chunks[cid].bm25_score = chunk.bm25_score
                    if "bm25" not in all_chunks[cid].retrieval_sources:
                        all_chunks[cid].retrieval_sources.append("bm25")
                else:
                    all_chunks[cid] = chunk

        # Graph expansion 路召回 (Day4: 使用 GraphRetriever 独立模块)
        if "graph_expand" in retrieval_plan:
            graph_chunks = self.graph_retriever.retrieve(
                query, max_hops=graph_max_hops, max_terms=graph_max_terms, max_chunks=fetch_k,
            )
            source_stats["graph_expand"] = len(graph_chunks)
            for chunk in graph_chunks:
                cid = chunk.chunk_id
                if cid in all_chunks:
                    all_chunks[cid].graph_score = max(all_chunks[cid].graph_score or 0, chunk.graph_score or 0)
                    if "graph_expand" not in all_chunks[cid].retrieval_sources:
                        all_chunks[cid].retrieval_sources.append("graph_expand")
                else:
                    all_chunks[cid] = chunk

        # 2. Score fusion
        merged = list(all_chunks.values())
        merged = self._score_fusion(merged)

        # 3. Optional rerank
        rerank_fallback = False
        if use_rerank and merged and len(merged) > top_k:
            merged, rerank_fallback = self._rerank(query, merged)

        # 4. Top-k
        final_chunks = merged[:top_k]

        # 5. 构建 trace
        latency = int((time.time() - start) * 1000)
        trace = {
            "module": "HybridGraphRetriever",
            "query": query[:100],
            "retrieval_plan": retrieval_plan,
            "source_stats": source_stats,
            "merged_count": len(merged),
            "final_count": len(final_chunks),
            "use_rerank": use_rerank,
            "latency_ms": latency,
            "fallback_used": rerank_fallback,
        }

        status: Literal["ok", "warn", "fail"] = "ok"
        if len(final_chunks) == 0:
            status = "fail"
        elif len(final_chunks) < 3:
            status = "warn"

        return RetrievalOutput(
            status=status,
            chunks=final_chunks,
            total_retrieved=len(final_chunks),
            source_stats=source_stats,
            trace=trace,
            next_action=None if status == "ok" else "check_retrieval_quality",
        )

    def _score_fusion(self, chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
        """加权分数融合: w_d*dense + w_b*bm25 + w_g*graph + 多路命中bonus。"""
        for c in chunks:
            ds = c.dense_score or 0.0
            bs = c.bm25_score or 0.0
            gs = c.graph_score or 0.0

            c.final_score = (
                config.DENSE_WEIGHT * ds +
                config.BM25_WEIGHT * bs +
                config.GRAPH_WEIGHT * gs
            )

            if len(c.retrieval_sources) > 1:
                c.final_score += config.MULTI_SOURCE_BONUS

        return sorted(chunks, key=lambda x: x.final_score, reverse=True)

    def _rerank(self, query: str, chunks: List[RetrievedChunk]) -> tuple:
        """CrossEncoder rerank，返回 (chunks, fallback_used)。"""
        try:
            reranker = get_reranker()
            pairs = [(query, c.text[:512]) for c in chunks]
            scores = reranker.predict(pairs)

            min_s, max_s = min(scores), max(scores)
            range_s = max_s - min_s if max_s != min_s else 1.0

            for c, s in zip(chunks, scores):
                c.rerank_score = float((s - min_s) / range_s)
                c.final_score = c.rerank_score

            return sorted(chunks, key=lambda x: x.final_score, reverse=True), False
        except Exception:
            return chunks, True

    # --- Ablation 支持 ---

    def retrieve_dense_only(self, query: str, k: int = 10) -> RetrievalOutput:
        """Ablation: 仅 Dense 检索。"""
        return self.retrieve(query, retrieval_plan=["dense"], top_k=k, use_rerank=False)

    def retrieve_bm25_only(self, query: str, k: int = 10) -> RetrievalOutput:
        """Ablation: 仅 BM25 检索。"""
        return self.retrieve(query, retrieval_plan=["bm25"], top_k=k, use_rerank=False)

    def retrieve_graph_only(self, query: str, k: int = 10) -> RetrievalOutput:
        """Ablation: 仅 Graph Expansion 检索。"""
        return self.retrieve(query, retrieval_plan=["graph_expand"], top_k=k, use_rerank=False)

    def retrieve_hybrid(self, query: str, k: int = 10, use_rerank: bool = True) -> RetrievalOutput:
        """Ablation: Dense + BM25 双路混合。"""
        return self.retrieve(query, retrieval_plan=["dense", "bm25"], top_k=k, use_rerank=use_rerank)

    def retrieve_full(self, query: str, k: int = 10, use_rerank: bool = True) -> RetrievalOutput:
        """Full: Dense + BM25 + Graph 三路混合。"""
        return self.retrieve(query, retrieval_plan=["dense", "bm25", "graph_expand"], top_k=k, use_rerank=use_rerank)

    def run_from_state(self, state: dict) -> dict:
        """从 AgentState 取输入，执行检索，返回 state 更新字典。"""
        query = state.get("rewrite_query", state.get("question", ""))
        retrieval_plan = state.get("retrieval_plan", ["dense", "bm25", "graph_expand"])
        top_k = state.get("final_top_k", config.FINAL_TOP_K)

        result = self.retrieve(query, retrieval_plan=retrieval_plan, top_k=top_k)

        return {
            "retrieved_chunks": [c.model_dump() for c in result.chunks],
            "retrieval_sources": list(result.source_stats.keys()),
            "trace": [{"node": "hybrid_graph_retriever", "output": f"status={result.status}, retrieved={result.total_retrieved}", "latency_ms": result.trace.get("latency_ms", 0)}],
        }
