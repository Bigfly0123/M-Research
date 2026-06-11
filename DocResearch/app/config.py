"""
config.py: 全局配置管理。

从 .env 加载环境变量，提供 LLM、检索、评测等模块的统一配置入口。
避免各模块各自读取 os.getenv，集中管理便于后续调参。
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    PROJECT_NAME: str = "DocResearch-Agent 2026"

    # --- LLM ---
    OPENAI_API_KEY: str = os.getenv("OPENAI_API_KEY", "")
    OPENAI_API_BASE: str = os.getenv(
        "OPENAI_API_BASE", "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    FAST_MODEL: str = os.getenv("FAST_MODEL", "qwen-max")
    SMART_MODEL: str = os.getenv("SMART_MODEL", "deepseek-r1")

    # --- Embedding ---
    EMBEDDING_MODE: str = os.getenv("EMBEDDING_MODE", "api")
    EMBEDDING_MODEL: str = os.getenv("EMBEDDING_MODEL", "text-embedding-v3")
    DASHSCOPE_API_KEY: str = os.getenv(
        "DASHSCOPE_API_KEY", os.getenv("OPENAI_API_KEY", "")
    )

    # --- Retrieval ---
    DENSE_BACKEND: str = os.getenv("DENSE_BACKEND", "faiss")
    DENSE_TOP_K: int = 40
    BM25_TOP_K: int = 40
    GRAPH_TOP_K: int = 40
    FINAL_TOP_K: int = 10
    USE_RERANK: bool = True
    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    # --- Score Fusion Weights ---
    DENSE_WEIGHT: float = 0.45
    BM25_WEIGHT: float = 0.35
    GRAPH_WEIGHT: float = 0.20
    MULTI_SOURCE_BONUS: float = 0.10

    # --- Context ---
    DEFAULT_CONTEXT_BUDGET: int = 3500

    # --- Judge Thresholds ---
    ANSWER_RELEVANCE_THRESHOLD: float = 0.75
    CITATION_SUPPORT_THRESHOLD: float = 0.75
    FAITHFULNESS_THRESHOLD: float = 0.75
    CONTEXT_SUFFICIENCY_THRESHOLD: float = 0.65

    # --- Repair ---
    MAX_REPAIR_COUNT: int = 1

    # --- Paths ---
    DATA_DIR: str = os.path.join(os.path.dirname(__file__), "..", "data")
    RAW_DOCS_DIR: str = os.path.join(DATA_DIR, "raw_docs")
    INDEX_DIR: str = os.path.join(DATA_DIR, "index")
    EVAL_DIR: str = os.path.join(os.path.dirname(__file__), "..", "eval")
    REPORTS_DIR: str = os.path.join(os.path.dirname(__file__), "..", "reports")
    SKILLS_DIR: str = os.path.join(os.path.dirname(__file__), "..", "skills")


config = Config()
