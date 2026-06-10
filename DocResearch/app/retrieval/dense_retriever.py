"""
Dense Retriever: 向量语义检索器。

双模式 Embedding:
- api (默认): 调用百炼 DashScope Embedding API，不需要本地模型
- local: 使用 HuggingFaceEmbeddings 本地模型

使用 ChromaDB 存储向量索引，检索时用 contextual_text 提高质量。
输出 RetrievedChunk 列表，dense_score 归一化到 0~1 (1/(1+L2距离))。
"""

import os
import time
import logging
from typing import List, Optional
from langchain_chroma import Chroma
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


class DenseRetriever:
    """Dense 检索器: ChromaDB 向量检索，支持 API/本地双模式 embedding。"""

    def __init__(self):
        self.index: Optional[Chroma] = None
        self._embeddings = None

    def close(self):
        """安全关闭 ChromaDB 连接，避免 GC 析构时 segfault。"""
        if self.index is not None:
            try:
                _collection = getattr(self.index, "_collection", None)
                if _collection is not None:
                    _client = getattr(_collection, "_client", None)
                    if _client is not None:
                        _client.admin_client = None
            except Exception:
                pass
            self.index = None

    def __del__(self):
        self.close()

    @property
    def embeddings(self):
        if self._embeddings is None:
            self._embeddings = get_embeddings()
        return self._embeddings

    def build_index(self, chunks: List[dict], persist_dir: str):
        """从 chunk 列表构建 ChromaDB 向量索引。"""
        texts = [c.get("contextual_text", c.get("text", "")) for c in chunks]
        metadatas = [
            {
                "chunk_id": c.get("chunk_id", ""),
                "doc_id": c.get("doc_id", ""),
                "source": c.get("source_path", ""),
                "section": " > ".join(c.get("section_path", [])) if isinstance(c.get("section_path"), list) else str(c.get("section_path", "")),
                "element_type": c.get("element_type", "text"),
            }
            for c in chunks
        ]
        os.makedirs(persist_dir, exist_ok=True)
        self.index = Chroma.from_texts(
            texts=texts,
            embedding=self.embeddings,
            metadatas=metadatas,
            persist_directory=persist_dir,
        )

    def load_index(self, persist_dir: str) -> bool:
        """加载已有的 ChromaDB 索引。"""
        if not os.path.exists(persist_dir):
            return False
        self.index = Chroma(persist_directory=persist_dir, embedding_function=self.embeddings)
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
            chunks.append(RetrievedChunk(
                chunk_id=doc.metadata.get("chunk_id", f"D-{i}"),
                text=doc.page_content,
                source=doc.metadata.get("source", ""),
                section=doc.metadata.get("section", ""),
                element_type=doc.metadata.get("element_type", "text"),
                retrieval_sources=["dense"],
                dense_score=norm_score,
                metadata=doc.metadata,
            ))

        return chunks
