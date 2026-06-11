"""
Dense Retriever (FAISS): 向量语义检索器，使用 FAISS 替代 ChromaDB。

FAISS 不依赖 SQLite，没有跨线程/上下文析构 segfault 问题。
接口与 dense_retriever.py (ChromaDB) 完全一致。
"""

import os
import json
import time
import logging
import numpy as np
from typing import List, Optional
from langchain_community.vectorstores import FAISS
from app.config import config
from app.schemas.retrieval import RetrievedChunk

logger = logging.getLogger(__name__)


def get_embeddings():
    """根据 EMBEDDING_MODE 选择 embedding 方式: api(默认) 或 local。"""
    mode = config.EMBEDDING_MODE.lower()

    if mode == "api":
        from langchain_community.embeddings import DashScopeEmbeddings

        logger.info(f"Using DashScope API embedding: {config.EMBEDDING_MODEL}")
        return DashScopeEmbeddings(
            model=config.EMBEDDING_MODEL,
            dashscope_api_key=config.DASHSCOPE_API_KEY,
        )
    elif mode == "local":
        from langchain_huggingface import HuggingFaceEmbeddings

        logger.info(f"Using local embedding: {config.EMBEDDING_MODEL}")
        return HuggingFaceEmbeddings(model_name=config.EMBEDDING_MODEL)
    else:
        raise ValueError(f"Unknown EMBEDDING_MODE: {mode}, expected 'api' or 'local'")


class DenseRetrieverFAISS:
    """Dense 检索器: FAISS 向量检索，接口与 DenseRetriever 一致。"""

    def __init__(self):
        self.index: Optional[FAISS] = None
        self._embeddings = None

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = get_embeddings()
        return self._embeddings

    def build_index(self, chunks: List[dict], persist_dir: str):
        """从 chunk 列表构建 FAISS 向量索引并保存到磁盘。"""
        texts = [c.get("contextual_text", c.get("text", "")) for c in chunks]
        metadatas = [
            {
                "chunk_id": c.get("chunk_id", ""),
                "doc_id": c.get("doc_id", ""),
                "source": c.get("source_path", ""),
                "section": " > ".join(c.get("section_path", []))
                if isinstance(c.get("section_path"), list)
                else str(c.get("section_path", "")),
                "element_type": c.get("element_type", "text"),
            }
            for c in chunks
        ]
        valid_texts, valid_metadatas = [], []
        for text, meta in zip(texts, metadatas):
            if text and len(text.strip()) > 0:
                valid_texts.append(text[:8000])
                valid_metadatas.append(meta)
        if not valid_texts:
            logger.warning("No valid texts to index")
            return
        os.makedirs(persist_dir, exist_ok=True)
        # 分批构建索引避免内存超限
        batch_size = 200
        if len(valid_texts) <= batch_size:
            self.index = FAISS.from_texts(
                texts=valid_texts,
                embedding=self.embeddings,
                metadatas=valid_metadatas,
            )
        else:
            logger.info(
                f"Building FAISS index in batches: {len(valid_texts)} texts, batch_size={batch_size}"
            )
            self.index = FAISS.from_texts(
                texts=valid_texts[:batch_size],
                embedding=self.embeddings,
                metadatas=valid_metadatas[:batch_size],
            )
            for start in range(batch_size, len(valid_texts), batch_size):
                end = min(start + batch_size, len(valid_texts))
                logger.info(f"  Adding batch {start}-{end}")
                self.index.add_texts(
                    texts=valid_texts[start:end],
                    metadatas=valid_metadatas[start:end],
                )
        self.index.save_local(persist_dir)

    def load_index(self, persist_dir: str) -> bool:
        """加载已有的 FAISS 索引。"""
        if not os.path.exists(persist_dir):
            return False
        self.index = FAISS.load_local(
            persist_dir,
            embeddings=self.embeddings,
            allow_dangerous_deserialization=True,
        )
        return True

    def retrieve(self, query: str, k: int = 20) -> List[RetrievedChunk]:
        """语义检索 top-k chunks，返回 RetrievedChunk 列表。"""
        start = time.time()
        if not self.index:
            return []

        results = self.index.similarity_search_with_score(query, k=k)
        latency = int((time.time() - start) * 1000)

        chunks = []
        for i, (doc, score) in enumerate(results):
            norm_score = 1.0 / (1.0 + float(score))
            chunks.append(
                RetrievedChunk(
                    chunk_id=doc.metadata.get("chunk_id", f"D-{i}"),
                    text=doc.page_content,
                    source=doc.metadata.get("source", ""),
                    section=doc.metadata.get("section", ""),
                    element_type=doc.metadata.get("element_type", "text"),
                    retrieval_sources=["dense"],
                    dense_score=norm_score,
                    metadata=doc.metadata,
                )
            )

        return chunks
