"""
Metadata Manager: chunk 元数据管理。

提供元数据统计、过滤、导出功能，支持后续按 element_type/section/source 做过滤检索。
"""

from typing import List, Dict, Any
from app.schemas.chunk import DocChunk


def get_element_type_distribution(chunks: List[DocChunk]) -> Dict[str, int]:
    """统计各 element_type 的 chunk 数量。"""
    dist: Dict[str, int] = {}
    for c in chunks:
        dist[c.element_type] = dist.get(c.element_type, 0) + 1
    return dist


def get_source_distribution(chunks: List[DocChunk]) -> Dict[str, int]:
    """统计各文档的 chunk 数量。"""
    dist: Dict[str, int] = {}
    for c in chunks:
        dist[c.doc_id] = dist.get(c.doc_id, 0) + 1
    return dist


def get_section_distribution(chunks: List[DocChunk]) -> Dict[str, int]:
    """统计各 section_path 的 chunk 数量。"""
    dist: Dict[str, int] = {}
    for c in chunks:
        key = " > ".join(c.section_path) if c.section_path else "root"
        dist[key] = dist.get(key, 0) + 1
    return dist


def filter_by_element_type(chunks: List[DocChunk], types: List[str]) -> List[DocChunk]:
    """按 element_type 过滤 chunk。"""
    return [c for c in chunks if c.element_type in types]


def filter_by_source(chunks: List[DocChunk], doc_id: str) -> List[DocChunk]:
    """按 doc_id 过滤 chunk。"""
    return [c for c in chunks if c.doc_id == doc_id]


def filter_by_section(chunks: List[DocChunk], section_keyword: str) -> List[DocChunk]:
    """按 section_path 关键词过滤 chunk。"""
    return [c for c in chunks if any(section_keyword in s for s in c.section_path)]


def build_metadata_summary(chunks: List[DocChunk]) -> Dict[str, Any]:
    """生成元数据摘要，用于 trace 和展示。"""
    return {
        "total_chunks": len(chunks),
        "total_tokens": sum(c.token_count for c in chunks),
        "element_types": get_element_type_distribution(chunks),
        "sources": get_source_distribution(chunks),
        "top_sections": dict(sorted(get_section_distribution(chunks).items(), key=lambda x: x[1], reverse=True)[:10]),
    }
