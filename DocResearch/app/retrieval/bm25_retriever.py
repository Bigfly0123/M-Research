"""
BM25 Retriever: 关键词精确检索器。

使用 rank_bm25 实现 BM25 算法，适合函数名、参数名、缩写等精确匹配。
与 dense retriever 互补，构成 hybrid retrieval 的第二路。
输出 RetrievedChunk 列表，bm25_score 归一化到 0~1。
"""

import os
import pickle
import time
from typing import List, Optional
from rank_bm25 import BM25Okapi
from app.schemas.retrieval import RetrievedChunk


class BM25Retriever:
    """BM25 检索器: 关键词精确匹配。"""

    def __init__(self):
        self.bm25_index: Optional[BM25Okapi] = None
        self.docs: List[dict] = []
        self.tokenized: List[List[str]] = []
        self.max_score: float = 1.0

    def build_index(self, chunks: List[dict], index_dir: str):
        """从 chunk 列表构建 BM25 索引并持久化。"""
        self.docs = chunks
        self.tokenized = [c.get("text", c.get("raw_text", "")).split() for c in chunks]
        self.bm25_index = BM25Okapi(self.tokenized)

        # 采样估计最大分数用于归一化
        self.max_score = 1.0
        if len(self.tokenized) > 0:
            sample_scores = self.bm25_index.get_scores(self.tokenized[0])
            if len(sample_scores) > 0 and max(sample_scores) > 0:
                self.max_score = max(sample_scores)

        os.makedirs(index_dir, exist_ok=True)
        with open(os.path.join(index_dir, "bm25_docs.pkl"), "wb") as f:
            pickle.dump(self.docs, f)
        with open(os.path.join(index_dir, "bm25_tokenized.pkl"), "wb") as f:
            pickle.dump(self.tokenized, f)
        with open(os.path.join(index_dir, "bm25_max_score.pkl"), "wb") as f:
            pickle.dump(self.max_score, f)

    def load_index(self, index_dir: str) -> bool:
        """加载已有的 BM25 索引。"""
        docs_pkl = os.path.join(index_dir, "bm25_docs.pkl")
        tok_pkl = os.path.join(index_dir, "bm25_tokenized.pkl")
        max_pkl = os.path.join(index_dir, "bm25_max_score.pkl")
        if not os.path.exists(docs_pkl) or not os.path.exists(tok_pkl):
            return False
        with open(docs_pkl, "rb") as f:
            self.docs = pickle.load(f)
        with open(tok_pkl, "rb") as f:
            self.tokenized = pickle.load(f)
        self.bm25_index = BM25Okapi(self.tokenized)
        if os.path.exists(max_pkl):
            with open(max_pkl, "rb") as f:
                self.max_score = pickle.load(f)
        else:
            self.max_score = 1.0
        return True

    def retrieve(self, query: str, k: int = 20) -> List[RetrievedChunk]:
        """BM25 关键词检索 top-k chunks，返回 RetrievedChunk 列表。"""
        start = time.time()
        if not self.bm25_index:
            return []

        scores = self.bm25_index.get_scores(query.split())
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
        latency = int((time.time() - start) * 1000)

        chunks = []
        for i in top_indices:
            if scores[i] <= 0:
                continue
            doc = self.docs[i]
            section_path = doc.get("section_path", [])
            section_str = " > ".join(section_path) if isinstance(section_path, list) else str(section_path)

            # 归一化到 0~1
            norm_score = min(float(scores[i]) / self.max_score, 1.0) if self.max_score > 0 else 0.0

            chunks.append(RetrievedChunk(
                chunk_id=doc.get("chunk_id", f"BM-{i}"),
                text=doc.get("text", doc.get("raw_text", "")),
                source=doc.get("source_path", ""),
                section=section_str,
                element_type=doc.get("element_type", "text"),
                retrieval_sources=["bm25"],
                bm25_score=norm_score,
                metadata={
                    "doc_id": doc.get("doc_id", ""),
                    "source": doc.get("source_path", ""),
                    "section": section_str,
                },
            ))

        return chunks
