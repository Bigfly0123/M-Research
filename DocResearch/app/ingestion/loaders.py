"""
Document Loaders: 文件加载器。

负责从磁盘读取文件内容，返回统一格式的 RawDocument。
不负责切块和结构解析，这些分别由 structure_parser.py 和 chunker.py 处理。
"""

import os
from typing import List, Optional
from pydantic import BaseModel, Field
from pypdf import PdfReader


class RawDocument(BaseModel):
    """从文件加载的原始文档。"""
    doc_id: str = Field(description="文档标识，通常是文件名")
    source_path: str = Field(description="文件完整路径")
    text: str = Field(description="完整文本内容")
    pages: List[dict] = Field(default_factory=list, description="PDF 分页内容 [{page: int, text: str}]")
    file_type: str = Field(description="文件类型: md/pdf/txt")


def load_markdown(file_path: str) -> RawDocument:
    """加载 Markdown 文件为 RawDocument。"""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    doc_id = os.path.basename(file_path)
    return RawDocument(doc_id=doc_id, source_path=file_path, text=text, file_type="md")


def load_pdf(file_path: str) -> RawDocument:
    """加载 PDF 文件为 RawDocument，同时提取分页内容。"""
    doc_id = os.path.basename(file_path)
    full_text = ""
    page_list = []
    reader = PdfReader(file_path)
    for i, page in enumerate(reader.pages):
        text = page.extract_text().strip()
        full_text += text + "\n\n"
        page_list.append({"page": i, "text": text})
    return RawDocument(doc_id=doc_id, source_path=file_path, text=full_text.strip(), pages=page_list, file_type="pdf")


def load_text(file_path: str) -> RawDocument:
    """加载纯文本文件为 RawDocument。"""
    with open(file_path, "r", encoding="utf-8") as f:
        text = f.read()
    doc_id = os.path.basename(file_path)
    return RawDocument(doc_id=doc_id, source_path=file_path, text=text, file_type="txt")


def load_file(file_path: str) -> Optional[RawDocument]:
    """根据文件扩展名路由到对应加载器。"""
    ext = os.path.splitext(file_path)[1].lower()
    if ext == ".pdf":
        return load_pdf(file_path)
    elif ext in (".md", ".mdx"):
        return load_markdown(file_path)
    elif ext == ".txt":
        return load_text(file_path)
    else:
        return None


def load_files(file_paths: List[str]) -> List[RawDocument]:
    """批量加载文件，跳过无法识别的格式。"""
    docs = []
    for fp in file_paths:
        doc = load_file(fp)
        if doc is not None:
            docs.append(doc)
    return docs
