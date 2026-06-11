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
        raise ValueError(
            f"Unknown DENSE_BACKEND: {backend}, expected 'faiss' or 'chroma'"
        )


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
        if self.dense and hasattr(self.dense, "close"):
            self.dense.close()

    def __del__(self):
        self.close()

    def build_index(self, chunks: List[dict], index_dir: str):
        """构建所有索引: Dense + BM25 + Graph。"""
        dense_dir = (
            "faiss_index" if config.DENSE_BACKEND.lower() == "faiss" else "chroma_db"
        )
        self.dense.build_index(chunks, persist_dir=os.path.join(index_dir, dense_dir))
        self.bm25.build_index(chunks, index_dir=index_dir)
        self.graph_index.build(chunks)
        self.graph_index.save(os.path.join(index_dir, "graph_index.json"))
        self._chunks_by_id = {
            c.get("chunk_id", f"idx-{i}"): c for i, c in enumerate(chunks)
        }
        self.graph_retriever = GraphRetriever(
            graph_index=self.graph_index, chunks_by_id=self._chunks_by_id
        )

    def load_index(self, index_dir: str) -> bool:
        """加载已有索引。"""
        dense_dir = (
            "faiss_index" if config.DENSE_BACKEND.lower() == "faiss" else "chroma_db"
        )
        dense_ok = self.dense.load_index(os.path.join(index_dir, dense_dir))
        bm25_ok = self.bm25.load_index(index_dir)
        graph_ok = self.graph_index.load(os.path.join(index_dir, "graph_index.json"))

        # [FIX] 从 BM25 docs 重建 _chunks_by_id，供 graph retriever 使用
        if bm25_ok and self.bm25.docs:
            self._chunks_by_id = {
                c.get("chunk_id", f"idx-{i}"): c
                for i, c in enumerate(self.bm25.docs)
            }

        if graph_ok:
            self.graph_retriever = GraphRetriever(
                graph_index=self.graph_index, chunks_by_id=self._chunks_by_id
            )
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
        # [TRACE] 记录每路独立候选 (用于诊断)
        _per_source_trace = {"dense": [], "bm25": [], "graph_expand": []}

        # Dense 路召回
        if "dense" in retrieval_plan:
            dense_results = self.dense.retrieve(query, k=fetch_k)
            source_stats["dense"] = len(dense_results)
            for rank, chunk in enumerate(dense_results):
                cid = chunk.chunk_id
                doc_id = chunk.metadata.get("doc_id", "") if chunk.metadata else ""
                if not doc_id and "-c" in cid:
                    doc_id = cid.rsplit("-c", 1)[0]
                _per_source_trace["dense"].append({
                    "rank": rank + 1, "chunk_id": cid, "doc_id": doc_id,
                    "score": chunk.dense_score,
                })
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
            for rank, chunk in enumerate(bm25_results):
                cid = chunk.chunk_id
                doc_id = chunk.metadata.get("doc_id", "") if chunk.metadata else ""
                if not doc_id and "-c" in cid:
                    doc_id = cid.rsplit("-c", 1)[0]
                _per_source_trace["bm25"].append({
                    "rank": rank + 1, "chunk_id": cid, "doc_id": doc_id,
                    "score": chunk.bm25_score,
                })
                if cid in all_chunks:
                    all_chunks[cid].bm25_score = chunk.bm25_score
                    if "bm25" not in all_chunks[cid].retrieval_sources:
                        all_chunks[cid].retrieval_sources.append("bm25")
                else:
                    all_chunks[cid] = chunk

        # Graph expansion 路召回 (Day4: 使用 GraphRetriever 独立模块)
        if "graph_expand" in retrieval_plan:
            graph_chunks = self.graph_retriever.retrieve(
                query,
                max_hops=graph_max_hops,
                max_terms=graph_max_terms,
                max_chunks=fetch_k,
            )
            source_stats["graph_expand"] = len(graph_chunks)
            for rank, chunk in enumerate(graph_chunks):
                cid = chunk.chunk_id
                doc_id = chunk.metadata.get("doc_id", "") if chunk.metadata else ""
                if not doc_id and "-c" in cid:
                    doc_id = cid.rsplit("-c", 1)[0]
                _per_source_trace["graph_expand"].append({
                    "rank": rank + 1, "chunk_id": cid, "doc_id": doc_id,
                    "score": chunk.graph_score,
                    "has_text": len(chunk.text) > 0,
                })
                if cid in all_chunks:
                    all_chunks[cid].graph_score = max(
                        all_chunks[cid].graph_score or 0, chunk.graph_score or 0
                    )
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
            # [TRACE] 每路独立候选 (诊断用)
            "per_source_candidates": _per_source_trace,
            # [TRACE] fusion 后 top-k (rerank 前)
            "fusion_topk": [
                {"chunk_id": c.chunk_id, "final_score": c.final_score,
                 "sources": c.retrieval_sources}
                for c in merged[:top_k]
            ],
            # [TRACE] final top-k (rerank 后)
            "final_topk": [
                {"chunk_id": c.chunk_id, "doc_id": c.metadata.get("doc_id", "") if c.metadata else (c.chunk_id.rsplit("-c", 1)[0] if "-c" in c.chunk_id else ""),
                 "final_score": c.final_score, "sources": c.retrieval_sources,
                 "dense_score": c.dense_score, "bm25_score": c.bm25_score,
                 "graph_score": c.graph_score, "rerank_score": c.rerank_score}
                for c in final_chunks
            ],
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

    def _score_fusion(
        self, chunks: List[RetrievedChunk], weights: dict = None
    ) -> List[RetrievedChunk]:
        """Reciprocal Rank Fusion (RRF): 基于排名融合，天然免疫分数尺度差异。

        RRF(d) = Σ_{r∈retrievers} w_r / (k + rank_r(d))
        k=60 是标准参数。多路命中的文档自然获得更高分。

        Args:
            chunks: 候选 chunk 列表
            weights: 可选自定义权重 {"dense": w, "bm25": w, "graph": w}。
                     不传则使用 config 默认值。
        """
        rrf_k = 60

        dense_by_score = sorted(chunks, key=lambda c: c.dense_score or 0, reverse=True)
        bm25_by_score = sorted(chunks, key=lambda c: c.bm25_score or 0, reverse=True)
        graph_by_score = sorted(chunks, key=lambda c: c.graph_score or 0, reverse=True)

        dense_rank = {
            c.chunk_id: i + 1
            for i, c in enumerate(dense_by_score)
            if c.dense_score and c.dense_score > 0
        }
        bm25_rank = {
            c.chunk_id: i + 1
            for i, c in enumerate(bm25_by_score)
            if c.bm25_score and c.bm25_score > 0
        }
        graph_rank = {
            c.chunk_id: i + 1
            for i, c in enumerate(graph_by_score)
            if c.graph_score and c.graph_score > 0
        }

        if weights is None:
            weights = {
                "dense": config.DENSE_WEIGHT,
                "bm25": config.BM25_WEIGHT,
                "graph": config.GRAPH_WEIGHT,
            }

        for c in chunks:
            score = 0.0
            if c.chunk_id in dense_rank:
                score += weights["dense"] / (rrf_k + dense_rank[c.chunk_id])
            if c.chunk_id in bm25_rank:
                score += weights["bm25"] / (rrf_k + bm25_rank[c.chunk_id])
            if c.chunk_id in graph_rank:
                score += weights["graph"] / (rrf_k + graph_rank[c.chunk_id])
            c.final_score = score

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
        return self.retrieve(
            query, retrieval_plan=["graph_expand"], top_k=k, use_rerank=False
        )

    def retrieve_hybrid(
        self, query: str, k: int = 10, use_rerank: bool = True
    ) -> RetrievalOutput:
        """Ablation: Dense + BM25 双路混合。"""
        return self.retrieve(
            query, retrieval_plan=["dense", "bm25"], top_k=k, use_rerank=use_rerank
        )

    def retrieve_full(
        self, query: str, k: int = 10, use_rerank: bool = True
    ) -> RetrievalOutput:
        """Full: Dense + BM25 + Graph 三路混合。"""
        return self.retrieve(
            query,
            retrieval_plan=["dense", "bm25", "graph_expand"],
            top_k=k,
            use_rerank=use_rerank,
        )

    # --- Adaptive Hybrid (Phase 2.2) ---

    def retrieve_adaptive_hybrid(
        self, query: str, k: int = 10, use_rerank: bool = False, fetch_k: int = None
    ) -> RetrievalOutput:
        """Adaptive Hybrid: 根据 query 和检索置信信号动态选择融合权重。

        核心思路:
        - 如果 BM25 置信度高 (top1 分数高且 top1-top5 gap 大) -> BM25 主导
        - 如果 Dense 置信度高且 BM25 低 -> Dense 主导
        - 如果两者重叠度高 -> 平衡融合
        - 否则 -> 带多样性控制的融合
        """
        if fetch_k is None:
            fetch_k = config.DENSE_TOP_K
        start = time.time()

        # 1. 双路召回
        dense_results = self.dense.retrieve(query, k=fetch_k)
        bm25_results = self.bm25.retrieve(query, k=fetch_k)

        # 2. Query 分析 + 自适应权重
        weights, strategy_label = self._analyze_and_choose_weights(
            query, dense_results, bm25_results
        )

        # 3. Merge
        all_chunks: dict[str, RetrievedChunk] = {}
        source_stats = {"dense": len(dense_results), "bm25": len(bm25_results), "graph_expand": 0}
        _per_source_trace = {"dense": [], "bm25": [], "graph_expand": []}

        for rank, chunk in enumerate(dense_results):
            cid = chunk.chunk_id
            doc_id = chunk.metadata.get("doc_id", "") if chunk.metadata else ""
            if not doc_id and "-c" in cid:
                doc_id = cid.rsplit("-c", 1)[0]
            _per_source_trace["dense"].append({
                "rank": rank + 1, "chunk_id": cid, "doc_id": doc_id, "score": chunk.dense_score,
            })
            if cid in all_chunks:
                all_chunks[cid].dense_score = chunk.dense_score
                if "dense" not in all_chunks[cid].retrieval_sources:
                    all_chunks[cid].retrieval_sources.append("dense")
            else:
                all_chunks[cid] = chunk

        for rank, chunk in enumerate(bm25_results):
            cid = chunk.chunk_id
            doc_id = chunk.metadata.get("doc_id", "") if chunk.metadata else ""
            if not doc_id and "-c" in cid:
                doc_id = cid.rsplit("-c", 1)[0]
            _per_source_trace["bm25"].append({
                "rank": rank + 1, "chunk_id": cid, "doc_id": doc_id, "score": chunk.bm25_score,
            })
            if cid in all_chunks:
                all_chunks[cid].bm25_score = chunk.bm25_score
                if "bm25" not in all_chunks[cid].retrieval_sources:
                    all_chunks[cid].retrieval_sources.append("bm25")
            else:
                all_chunks[cid] = chunk

        # 4. Adaptive fusion
        merged = list(all_chunks.values())
        merged = self._score_fusion(merged, weights=weights)

        # 5. Optional rerank
        rerank_fallback = False
        if use_rerank and merged and len(merged) > k:
            merged, rerank_fallback = self._rerank(query, merged)

        final_chunks = merged[:k]
        latency = int((time.time() - start) * 1000)

        trace = {
            "module": "HybridGraphRetriever",
            "strategy": "adaptive_hybrid",
            "adaptive_label": strategy_label,
            "adaptive_weights": weights,
            "query": query[:100],
            "retrieval_plan": ["dense", "bm25"],
            "source_stats": source_stats,
            "merged_count": len(merged),
            "final_count": len(final_chunks),
            "use_rerank": use_rerank,
            "latency_ms": latency,
            "fallback_used": rerank_fallback,
            "per_source_candidates": _per_source_trace,
            "final_topk": [
                {"chunk_id": c.chunk_id,
                 "doc_id": c.metadata.get("doc_id", "") if c.metadata else (c.chunk_id.rsplit("-c", 1)[0] if "-c" in c.chunk_id else ""),
                 "final_score": c.final_score, "sources": c.retrieval_sources,
                 "dense_score": c.dense_score, "bm25_score": c.bm25_score}
                for c in final_chunks
            ],
        }

        status = "ok" if len(final_chunks) >= 3 else ("warn" if final_chunks else "fail")
        return RetrievalOutput(
            status=status, chunks=final_chunks, total_retrieved=len(final_chunks),
            source_stats=source_stats, trace=trace,
        )

    def _analyze_and_choose_weights(
        self, query: str, dense_results: List, bm25_results: List
    ) -> tuple:
        """分析 query 和检索置信信号，返回 (weights_dict, strategy_label)。"""
        import re as _re

        # Query 特征
        q_words = query.split()
        query_length = len(q_words)
        capitalized_terms = len([w for w in q_words if w[0:1].isupper() and len(w) > 1])
        code_like = len([w for w in q_words if _re.match(r'^[a-z]+_[a-z]+$', w) or _re.match(r'^[A-Z][a-z]+[A-Z]', w)])
        has_exact_entity = any(w in query for w in ["'", '"', '(', ')'])

        # BM25 置信度
        bm25_scores = [c.bm25_score for c in bm25_results[:10] if c.bm25_score]
        bm25_top1 = bm25_scores[0] if bm25_scores else 0
        bm25_top5_avg = sum(bm25_scores[:5]) / max(len(bm25_scores[:5]), 1)
        bm25_gap = bm25_top1 - (bm25_scores[4] if len(bm25_scores) > 4 else 0)
        bm25_confident = bm25_top1 > 0.5 and bm25_gap > 0.15

        # Dense 置信度
        dense_scores = [c.dense_score for c in dense_results[:10] if c.dense_score]
        dense_top1 = dense_scores[0] if dense_scores else 0
        dense_gap = dense_top1 - (dense_scores[4] if len(dense_scores) > 4 else 0)
        dense_confident = dense_top1 > 0.4 and dense_gap > 0.1

        # 双路重叠度 (top-10 doc_id 重叠)
        dense_doc_ids = set()
        for c in dense_results[:10]:
            did = c.metadata.get("doc_id", "") if c.metadata else ""
            if not did and "-c" in c.chunk_id:
                did = c.chunk_id.rsplit("-c", 1)[0]
            if did:
                dense_doc_ids.add(did)

        bm25_doc_ids = set()
        for c in bm25_results[:10]:
            did = c.metadata.get("doc_id", "") if c.metadata else ""
            if not did and "-c" in c.chunk_id:
                did = c.chunk_id.rsplit("-c", 1)[0]
            if did:
                bm25_doc_ids.add(did)

        overlap = len(dense_doc_ids & bm25_doc_ids) / max(len(dense_doc_ids | bm25_doc_ids), 1)

        # [Phase 3] 增强 BM25 弱信号检测 (dense_strong_bm25_weak 分支)
        bm25_very_weak = bm25_top1 < 0.3 or (bm25_gap < 0.08 and bm25_top5_avg < 0.35)
        dense_strong = dense_top1 > 0.45 and dense_gap > 0.1

        # 决策逻辑
        if bm25_confident and not dense_confident:
            # BM25 强势，Dense 弱 -> BM25 主导
            weights = {"dense": 0.25, "bm25": 0.65, "graph": 0.10}
            label = "bm25_dominant"
        elif dense_strong and bm25_very_weak:
            # [Phase 3] Dense 很强 + BM25 很弱 -> 几乎纯 Dense (StratRAG 场景)
            weights = {"dense": 0.90, "bm25": 0.00, "graph": 0.10}
            label = "dense_strong_bm25_weak"
        elif dense_confident and not bm25_confident:
            # Dense 强势，BM25 弱 -> Dense 主导 (极少 BM25)
            weights = {"dense": 0.80, "bm25": 0.10, "graph": 0.10}
            label = "dense_dominant"
        elif overlap > 0.5:
            # 高重叠 -> 平衡融合
            weights = {"dense": 0.45, "bm25": 0.45, "graph": 0.10}
            label = "balanced_high_overlap"
        elif overlap < 0.2 and dense_top1 > bm25_top1:
            # 低重叠且 Dense 更强 -> Dense 主导
            weights = {"dense": 0.75, "bm25": 0.15, "graph": 0.10}
            label = "dense_dominant_low_overlap"
        elif has_exact_entity or capitalized_terms >= 3 or code_like >= 2:
            # 多实体/精确匹配型 query -> BM25 偏向
            weights = {"dense": 0.30, "bm25": 0.60, "graph": 0.10}
            label = "bm25_entity_bias"
        else:
            # 默认: 均衡略偏 Dense
            weights = {"dense": 0.45, "bm25": 0.45, "graph": 0.10}
            label = "default_balanced"

        return weights, label

    # --- Selective Graph (Phase 2.3) ---

    def retrieve_selective_graph(
        self, query: str, k: int = 10, use_rerank: bool = False, fetch_k: int = None
    ) -> RetrievalOutput:
        """Selective Graph: 先跑 adaptive_hybrid，只在需要时触发 graph expansion。

        触发条件 (满足任一):
        1. query 含多跳/关系意图词 (compare, difference, relation, how, why...)
        2. adaptive_hybrid 的 top-k 覆盖不足 (< 3 个不同 doc)
        3. BM25 和 Dense 分歧大且各自置信度都不高
        """
        if fetch_k is None:
            fetch_k = config.DENSE_TOP_K
        start = time.time()

        # 1. 先跑 adaptive hybrid 获取 base results
        base_result = self.retrieve_adaptive_hybrid(query, k=k, use_rerank=use_rerank, fetch_k=fetch_k)
        base_chunks = base_result.chunks

        # 2. 判断是否需要 graph expansion
        should_expand, expand_reason = self._should_trigger_graph(query, base_chunks, base_result.trace)

        if not should_expand:
            # 不触发，直接返回 base result
            base_result.trace["selective_graph"] = {
                "triggered": False, "reason": expand_reason
            }
            return base_result

        # 3. 触发 graph expansion
        graph_chunks = self.graph_retriever.retrieve(
            query, max_hops=1, max_terms=5, max_chunks=fetch_k
        )

        # 4. 过滤 graph candidates: 只保留与 query 有交集的
        q_terms = set(query.lower().split())
        filtered_graph = []
        for gc in graph_chunks:
            gc_terms = set(gc.text.lower().split()) if gc.text else set()
            term_overlap = len(q_terms & gc_terms) / max(len(q_terms), 1)
            if term_overlap > 0.05 and gc.text:  # 至少有 5% 的 term 重叠
                filtered_graph.append(gc)

        # 5. 将 graph candidates 作为 supplement 合并
        base_ids = {c.chunk_id for c in base_chunks}
        supplement = [gc for gc in filtered_graph if gc.chunk_id not in base_ids]

        # 合并到 base (graph 不替换，只补充)
        all_chunks_dict = {c.chunk_id: c for c in base_chunks}
        for gc in supplement:
            if gc.chunk_id not in all_chunks_dict:
                all_chunks_dict[gc.chunk_id] = gc

        merged = list(all_chunks_dict.values())
        # 用 standard weights 做融合
        merged = self._score_fusion(merged)
        final_chunks = merged[:k]

        latency = int((time.time() - start) * 1000)
        source_stats = base_result.source_stats.copy()
        source_stats["graph_expand"] = len(graph_chunks)

        trace = base_result.trace.copy()
        trace["strategy"] = "selective_graph"
        trace["selective_graph"] = {
            "triggered": True,
            "reason": expand_reason,
            "graph_candidates": len(graph_chunks),
            "filtered_graph": len(filtered_graph),
            "supplement_added": len(supplement),
        }
        trace["latency_ms"] = latency
        trace["final_topk"] = [
            {"chunk_id": c.chunk_id,
             "doc_id": c.metadata.get("doc_id", "") if c.metadata else (c.chunk_id.rsplit("-c", 1)[0] if "-c" in c.chunk_id else ""),
             "final_score": c.final_score, "sources": c.retrieval_sources}
            for c in final_chunks
        ]

        status = "ok" if len(final_chunks) >= 3 else ("warn" if final_chunks else "fail")
        return RetrievalOutput(
            status=status, chunks=final_chunks, total_retrieved=len(final_chunks),
            source_stats=source_stats, trace=trace,
        )

    def _should_trigger_graph(self, query: str, base_chunks: List, trace: dict) -> tuple:
        """判断是否需要触发 graph expansion，返回 (should_trigger, reason)。"""
        import re as _re

        # 条件1: 多跳/关系意图词
        multi_hop_terms = [
            "compare", "difference", "relation", "relationship", "between",
            "while", "versus", "vs", "how", "why", "cause", "effect",
            "contrast", "similar", "different", "connection",
            "对比", "区别", "关系", "为什么", "如何", "触发",
        ]
        q_lower = query.lower()
        has_multi_hop = any(term in q_lower for term in multi_hop_terms)

        # 条件2: top-k 覆盖不足 (< 3 个不同 doc)
        doc_ids = set()
        for c in base_chunks:
            did = c.metadata.get("doc_id", "") if c.metadata else ""
            if not did and "-c" in c.chunk_id:
                did = c.chunk_id.rsplit("-c", 1)[0]
            if did:
                doc_ids.add(did)
        low_coverage = len(doc_ids) < 3

        # 条件3: adaptive label 显示低置信
        adaptive_label = trace.get("adaptive_label", "")
        low_confidence = adaptive_label in ("default_balanced", "dense_dominant_low_overlap") and len(base_chunks) < 5

        if has_multi_hop:
            return True, f"multi_hop_query_detected"
        if low_coverage:
            return True, f"low_doc_coverage ({len(doc_ids)} docs)"
        if low_confidence:
            return True, f"low_confidence (label={adaptive_label})"

        return False, "no_trigger_condition_met"

    def run_from_state(self, state: dict) -> dict:
        """从 AgentState 取输入，执行检索，返回 state 更新字典。"""
        query = state.get("rewrite_query", state.get("question", ""))
        retrieval_plan = state.get("retrieval_plan", ["dense", "bm25", "graph_expand"])
        top_k = state.get("final_top_k", config.FINAL_TOP_K)

        result = self.retrieve(query, retrieval_plan=retrieval_plan, top_k=top_k)

        return {
            "retrieved_chunks": [c.model_dump() for c in result.chunks],
            "retrieval_sources": list(result.source_stats.keys()),
            "trace": [
                {
                    "node": "hybrid_graph_retriever",
                    "output": f"status={result.status}, retrieved={result.total_retrieved}",
                    "latency_ms": result.trace.get("latency_ms", 0),
                }
            ],
        }
