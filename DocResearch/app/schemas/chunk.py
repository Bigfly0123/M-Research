"""
DocChunk schema: 结构化文档切块的数据定义。

这是 Ingestion 模块的核心输出，也是后续 Retriever、Evidence Composer、
Answer Generator 的基础数据单元。每个 chunk 必须有稳定的 chunk_id，
可追溯的 source_path/section_path，明确的 element_type，以及 contextual_text。
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field


class DocChunk(BaseModel):
    chunk_id: str = Field(description="稳定唯一标识，格式: {doc_id}-C{index:03d}")
    doc_id: str = Field(description="文档标识，通常是文件名")
    source_path: str = Field(description="文件完整路径")
    title: Optional[str] = Field(default=None, description="文档标题")
    section_path: List[str] = Field(default_factory=list, description="章节层级路径，如 ['RAG', 'Retriever', 'BM25']")
    page: Optional[int] = Field(default=None, description="PDF 页码")
    element_type: Literal["text", "heading", "code", "table", "list"] = Field(default="text", description="元素类型")
    language: Optional[str] = Field(default=None, description="代码块语言")
    text: str = Field(description="原始文本内容")
    contextual_text: str = Field(default="", description="带上下文头的文本，用于检索 embedding")
    token_count: int = Field(default=0, description="估算 token 数")
    metadata: dict = Field(default_factory=dict, description="扩展元数据")


class IngestionInput(BaseModel):
    file_paths: List[str] = Field(description="待加载的文件路径列表")
    chunk_size: int = Field(default=500, description="最大 chunk token 数")
    chunk_overlap: int = Field(default=50, description="chunk 间重叠 token 数")
    add_contextual_header: bool = Field(default=True, description="是否生成 contextual header")


class IngestionOutput(BaseModel):
    status: Literal["ok", "warn", "fail"] = Field(default="ok")
    chunks: List[DocChunk] = Field(default_factory=list)
    total_chunks: int = Field(default=0)
    total_tokens: int = Field(default=0)
    sources: List[str] = Field(default_factory=list)
    trace: dict = Field(default_factory=dict)
    next_action: Optional[str] = Field(default=None)


class ModuleResult(BaseModel):
    """通用模块输出: status + data + trace + next_action。"""
    status: Literal["ok", "warn", "fail"] = Field(default="ok")
    data: dict = Field(default_factory=dict)
    trace: dict = Field(default_factory=dict)
    next_action: Optional[str] = Field(default=None)
