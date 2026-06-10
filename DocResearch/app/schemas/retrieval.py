"""
Retrieval schema: 检索模块输入输出数据结构。

定义 RetrievedChunk (单条检索结果)、RetrievalOutput (检索模块完整输出)、
HybridRetrievalConfig (混合检索配置) 等核心 schema。
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class RetrievedChunk(BaseModel):
    """单条检索结果，携带多路分数和来源标记。"""
    chunk_id: str = Field(description="chunk 唯一标识")
    text: str = Field(description="chunk 文本内容")
    source: str = Field(default="", description="文档来源")
    section: str = Field(default="", description="章节路径")
    element_type: str = Field(default="text", description="元素类型")
    retrieval_sources: List[str] = Field(default_factory=list, description="命中来源: dense/bm25/graph_expand")
    dense_score: Optional[float] = Field(default=None, description="dense 原始分数")
    bm25_score: Optional[float] = Field(default=None, description="bm25 原始分数")
    graph_score: Optional[float] = Field(default=None, description="graph 原始分数")
    rerank_score: Optional[float] = Field(default=None, description="rerank 分数")
    final_score: float = Field(default=0.0, description="最终融合分数")
    metadata: dict = Field(default_factory=dict, description="扩展元数据")


class HybridRetrievalConfig(BaseModel):
    """混合检索配置。"""
    retrieval_plan: List[str] = Field(default=["dense", "bm25", "graph_expand"], description="启用哪些检索路")
    fetch_k: int = Field(default=20, description="每路召回数量")
    final_top_k: int = Field(default=10, description="最终返回数量")
    use_rerank: bool = Field(default=True, description="是否使用 CrossEncoder rerank")
    dense_weight: float = Field(default=0.45, description="dense 分数权重")
    bm25_weight: float = Field(default=0.35, description="bm25 分数权重")
    graph_weight: float = Field(default=0.20, description="graph 分数权重")
    multi_source_bonus: float = Field(default=0.10, description="多路命中加成")


class RetrievalOutput(BaseModel):
    """检索模块完整输出，遵循 Module 模式。"""
    status: Literal["ok", "warn", "fail"] = Field(default="ok")
    chunks: List[RetrievedChunk] = Field(default_factory=list, description="检索结果列表")
    total_retrieved: int = Field(default=0, description="总检索数量")
    source_stats: dict = Field(default_factory=dict, description="各路召回统计")
    trace: dict = Field(default_factory=dict, description="trace 信息")
    next_action: Optional[str] = Field(default=None)
