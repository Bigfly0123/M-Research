"""
Graph Retriever: 轻量术语图扩展检索器。

基于 LightweightGraphIndex，从查询中抽取技术术语，
沿 term graph 扩展找到相关术语和相关 chunk。
这是三路检索中的第三路，适合多跳概念关联场景。

Day4 新增模块，与 DenseRetriever、BM25Retriever 平级。
"""

import time
from typing import List, Optional
from app.retrieval.graph_index import LightweightGraphIndex, ExpansionResult
from app.schemas.retrieval import RetrievedChunk


class GraphRetriever:
    """Graph 检索器: 术语图扩展检索。"""

    def __init__(self, graph_index: LightweightGraphIndex = None, chunks_by_id: dict = None):
        self.graph_index = graph_index or LightweightGraphIndex()
        self._chunks_by_id = chunks_by_id or {}

    def set_chunks_by_id(self, chunks_by_id: dict):
        """设置 chunk_id → chunk_data 映射 (用于补充检索结果文本)。"""
        self._chunks_by_id = chunks_by_id

    def retrieve(
        self,
        query: str,
        max_hops: int = 1,
        max_terms: int = 5,
        max_chunks: int = 20,
    ) -> List[RetrievedChunk]:
        """从查询中抽取术语，做图扩展，返回相关 RetrievedChunk 列表。

        Args:
            query: 查询文本
            max_hops: 最大扩展跳数
            max_terms: 最多从查询中抽取多少术语做扩展
            max_chunks: 最多返回多少 chunk

        Returns:
            RetrievedChunk 列表，graph_score 为递减权重
        """
        start = time.time()

        # 1. 从查询中抽取术语
        query_terms = self.graph_index.extract_terms(query)[:max_terms]

        if not query_terms:
            return []

        # 2. 多术语扩展
        expansion = self.graph_index.expand_multi(query_terms, max_hops=max_hops)

        # 3. 构建 RetrievedChunk 列表
        chunks = []
        seen = set()
        # 按扩展距离分配分数: 直接命中的 chunk 分更高
        for i, cid in enumerate(expansion.related_chunks[:max_chunks]):
            if cid in seen:
                continue
            seen.add(cid)

            # 查找 chunk 原始数据
            chunk_data = self._chunks_by_id.get(cid, {})
            text = chunk_data.get("text", chunk_data.get("raw_text", ""))
            source = chunk_data.get("source_path", "")
            section_path = chunk_data.get("section_path", [])
            section_str = " > ".join(section_path) if isinstance(section_path, list) else str(section_path)

            # 分数: 随排序递减
            graph_score = 1.0 / (1.0 + i * 0.1)

            chunks.append(RetrievedChunk(
                chunk_id=cid,
                text=text,
                source=source,
                section=section_str,
                element_type=chunk_data.get("element_type", "text"),
                retrieval_sources=["graph_expand"],
                graph_score=graph_score,
                metadata={"expanded_from": query_terms[:3]},
            ))

        return chunks

    def get_expansion_info(self, query: str, max_hops: int = 1) -> ExpansionResult:
        """获取扩展信息 (不返回 chunk，只返回术语扩展路径，用于 trace)。"""
        query_terms = self.graph_index.extract_terms(query)[:5]
        if not query_terms:
            return ExpansionResult(seed_term=query, trace={"status": "no_terms_found"})
        return self.graph_index.expand_multi(query_terms, max_hops=max_hops)
