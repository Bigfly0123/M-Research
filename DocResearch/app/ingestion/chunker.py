"""
Contextual / Structure-aware Chunker: 文档结构化切块主入口。

这是 Ingestion 模块的核心，把 PDF/Markdown/TXT 解析成保留标题、章节、
代码块、表格、页码和 contextual header 的结构化 chunk。

遵循 expanded 指导的 Module 设计模式:
  - 输入输出 schema 校验 (IngestionInput → IngestionOutput)
  - 关键决策写入 trace
  - 错误处理有 fallback (status: ok/warn/fail)
  - 可独立调用，也可接入 AgentState

流程: load_files → parse_structure → generate_chunks → add_contextual_header → return
"""

import os
import re
import time
from typing import List, Optional, Literal

from app.schemas.chunk import DocChunk, IngestionInput, IngestionOutput, ModuleResult
from app.ingestion.loaders import load_files, RawDocument
from app.ingestion.structure_parser import parse_markdown, parse_pdf_text, ParsedElement
from app.ingestion.metadata import build_metadata_summary


class ChunkerConfig:
    """切块配置。"""
    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 50,
        add_contextual_header: bool = True,
        min_chunk_tokens: int = 10,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.add_contextual_header = add_contextual_header
        self.min_chunk_tokens = min_chunk_tokens


def estimate_tokens(text: str) -> int:
    """粗略估算 token 数 (中文约 1.5 字/token，英文约 4 字符/token)。"""
    return max(int(len(text) / 3), 1)


def build_contextual_text(chunk: DocChunk) -> str:
    """为 chunk 构建上下文头，减少切开后上下文丢失的问题。

    格式:
    [Document: xxx]
    [Section: A > B > C]
    [Element: code]

    原始文本...
    """
    parts = []
    parts.append(f"[Document: {chunk.title or chunk.doc_id}]")
    parts.append(f"[Source: {chunk.source_path}]")
    if chunk.section_path:
        parts.append(f"[Section: {' > '.join(chunk.section_path)}]")
    parts.append(f"[Element: {chunk.element_type}]")
    if chunk.language:
        parts.append(f"[Language: {chunk.language}]")
    if chunk.page is not None:
        parts.append(f"[Page: {chunk.page}]")
    return "\n".join(parts) + "\n\n" + chunk.text


def _split_long_text(text: str, max_tokens: int, overlap: int) -> List[str]:
    """超长文本按句子边界切分，避免粗暴截断。"""
    if estimate_tokens(text) <= max_tokens:
        return [text]

    sentences = re.split(r'(?<=[。.!?！？\n])\s*', text)
    parts = []
    current = ""

    for sent in sentences:
        if not sent.strip():
            continue
        candidate = current + " " + sent if current else sent
        if estimate_tokens(candidate) > max_tokens and current:
            parts.append(current.strip())
            if overlap > 0:
                prev_tokens = current.strip().split()
                overlap_text = " ".join(prev_tokens[-overlap:]) if len(prev_tokens) > overlap else ""
                current = overlap_text + " " + sent if overlap_text else sent
            else:
                current = sent
        else:
            current = candidate

    if current.strip():
        parts.append(current.strip())

    return parts if parts else [text]


def _make_chunk(
    counter: int,
    doc_id: str,
    source_path: str,
    section_path: List[str],
    element_type: str,
    raw_text: str,
    title: str = None,
    page: int = None,
    language: str = None,
    add_contextual_header: bool = True,
) -> DocChunk:
    """创建单个 DocChunk 并生成 contextual_text。"""
    chunk = DocChunk(
        chunk_id=f"{doc_id}-C{counter:03d}",
        doc_id=doc_id,
        source_path=source_path,
        title=title or doc_id,
        section_path=list(section_path),
        page=page,
        element_type=element_type,
        language=language,
        text=raw_text,
        contextual_text="",
        token_count=estimate_tokens(raw_text),
    )
    if add_contextual_header:
        chunk.contextual_text = build_contextual_text(chunk)
    else:
        chunk.contextual_text = raw_text
    return chunk


def _elements_to_chunks(
    elements: List[ParsedElement],
    doc_id: str,
    source_path: str,
    config: ChunkerConfig = None,
) -> List[DocChunk]:
    """把 ParsedElement 列表转换为 DocChunk 列表，超长元素做切分。"""
    if config is None:
        config = ChunkerConfig()

    chunks = []
    counter = 0

    for elem in elements:
        text = elem.text.strip()
        if not text or estimate_tokens(text) < config.min_chunk_tokens:
            continue

        if estimate_tokens(text) > config.chunk_size and elem.element_type not in ("heading",):
            sub_texts = _split_long_text(text, config.chunk_size, config.chunk_overlap)
        else:
            sub_texts = [text]

        for sub_text in sub_texts:
            chunk = _make_chunk(
                counter=counter,
                doc_id=doc_id,
                source_path=source_path,
                section_path=elem.section_path,
                element_type=elem.element_type,
                raw_text=sub_text,
                page=elem.page,
                language=elem.language,
                add_contextual_header=config.add_contextual_header,
            )
            chunks.append(chunk)
            counter += 1

    return chunks


def chunk_markdown(doc: RawDocument, config: ChunkerConfig = None) -> List[DocChunk]:
    """Markdown 文档切块入口: parse_markdown → elements_to_chunks。"""
    elements = parse_markdown(doc.text)
    return _elements_to_chunks(elements, doc.doc_id, doc.source_path, config)


def chunk_pdf(doc: RawDocument, config: ChunkerConfig = None) -> List[DocChunk]:
    """PDF 文档切块入口: 逐页 parse_pdf_text → elements_to_chunks。"""
    if config is None:
        config = ChunkerConfig()

    all_chunks = []
    counter = 0

    for page_data in doc.pages:
        page_num = page_data.get("page", 0)
        page_text = page_data.get("text", "")
        if not page_text.strip():
            continue

        elements = parse_pdf_text(page_text, page=page_num)
        for elem in elements:
            text = elem.text.strip()
            if not text or estimate_tokens(text) < config.min_chunk_tokens:
                continue

            if estimate_tokens(text) > config.chunk_size:
                sub_texts = _split_long_text(text, config.chunk_size, config.chunk_overlap)
            else:
                sub_texts = [text]

            for sub_text in sub_texts:
                chunk = _make_chunk(
                    counter=counter,
                    doc_id=doc.doc_id,
                    source_path=doc.source_path,
                    section_path=elem.section_path,
                    element_type=elem.element_type,
                    raw_text=sub_text,
                    page=page_num,
                    add_contextual_header=config.add_contextual_header,
                )
                all_chunks.append(chunk)
                counter += 1

    return all_chunks


def chunk_text(doc: RawDocument, config: ChunkerConfig = None) -> List[DocChunk]:
    """纯文本文档切块: 简单按段落+长度切。"""
    if config is None:
        config = ChunkerConfig()

    paragraphs = re.split(r'\n\s*\n', doc.text)
    chunks = []
    counter = 0

    for para in paragraphs:
        para = para.strip()
        if not para or estimate_tokens(para) < config.min_chunk_tokens:
            continue

        if estimate_tokens(para) > config.chunk_size:
            sub_texts = _split_long_text(para, config.chunk_size, config.chunk_overlap)
        else:
            sub_texts = [para]

        for sub_text in sub_texts:
            chunk = _make_chunk(
                counter=counter,
                doc_id=doc.doc_id,
                source_path=doc.source_path,
                section_path=["full"],
                element_type="text",
                raw_text=sub_text,
                add_contextual_header=config.add_contextual_header,
            )
            chunks.append(chunk)
            counter += 1

    return chunks


class StructureAwareChunker:
    """Structure-aware Chunker 模块入口，遵循 Module 设计模式。

    用法:
        chunker = StructureAwareChunker()
        result = chunker.run(file_paths=["doc.md", "doc.pdf"])
        # result: IngestionOutput with chunks, trace, status
    """

    def __init__(self, config: ChunkerConfig = None):
        self.config = config or ChunkerConfig()

    def run(self, file_paths: List[str]) -> IngestionOutput:
        """主入口: 加载文件 → 解析结构 → 生成 chunks → 写 trace。"""
        start = time.time()
        trace_data = {"module": "StructureAwareChunker", "input_files": len(file_paths)}

        try:
            docs = load_files(file_paths)
        except Exception as e:
            return IngestionOutput(
                status="fail",
                trace={**trace_data, "error": str(e), "fallback_used": False},
                next_action="check_file_paths",
            )

        if not docs:
            return IngestionOutput(
                status="warn",
                trace={**trace_data, "warning": "No valid documents loaded"},
                next_action="check_file_format",
            )

        all_chunks: List[DocChunk] = []
        errors = []

        for doc in docs:
            try:
                if doc.file_type == "md":
                    chunks = chunk_markdown(doc, self.config)
                elif doc.file_type == "pdf":
                    chunks = chunk_pdf(doc, self.config)
                else:
                    chunks = chunk_text(doc, self.config)
                all_chunks.extend(chunks)
            except Exception as e:
                errors.append({"doc_id": doc.doc_id, "error": str(e)})

        latency = int((time.time() - start) * 1000)
        meta_summary = build_metadata_summary(all_chunks)

        status: Literal["ok", "warn", "fail"] = "ok"
        if errors and all_chunks:
            status = "warn"
        elif errors and not all_chunks:
            status = "fail"

        trace_data.update({
            "status": status,
            "latency_ms": latency,
            "total_chunks": len(all_chunks),
            "total_tokens": meta_summary.get("total_tokens", 0),
            "element_types": meta_summary.get("element_types", {}),
            "sources": meta_summary.get("sources", {}),
            "errors": errors,
            "fallback_used": False,
        })

        return IngestionOutput(
            status=status,
            chunks=all_chunks,
            total_chunks=len(all_chunks),
            total_tokens=meta_summary.get("total_tokens", 0),
            sources=[doc.doc_id for doc in docs],
            trace=trace_data,
            next_action=None if status == "ok" else "check_errors",
        )

    def run_from_state(self, state: dict) -> dict:
        """接入 AgentState: 从 state 取 file_paths，返回 state 更新。"""
        file_paths = state.get("file_paths", [])
        result = self.run(file_paths)

        return {
            "chunks": [c.model_dump() for c in result.chunks],
            "ingestion_status": result.status,
            "ingestion_trace": result.trace,
        }


def load_documents(file_paths: List[str], config: ChunkerConfig = None) -> List[DocChunk]:
    """兼容旧接口的快捷函数。"""
    chunker = StructureAwareChunker(config=config)
    result = chunker.run(file_paths)
    return result.chunks
