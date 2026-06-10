"""
Citation Manager: 引用 ID 生成与校验。

为证据分配稳定的 citation_id (格式: Dx-Cyyy)，
并提供引用提取和合法性校验工具函数。
"""

import re
from typing import List


def make_citation_id(doc_index: int, chunk_index: int) -> str:
    """生成稳定 citation_id: D{doc_index}-C{chunk_index:03d}"""
    return f"D{doc_index}-C{chunk_index:03d}"


def extract_citations(answer: str) -> List[str]:
    """从答案文本中提取所有 citation_id。"""
    return re.findall(r'\[D\d+-C\d+\]', answer)


def validate_citations(cited_ids: List[str], valid_ids: set) -> dict:
    """校验引用。"""
    cited_set = set(cited_ids)
    invalid = cited_set - valid_ids
    return {
        "invalid_citations": list(invalid),
        "missing_citations": len(cited_set) == 0,
        "valid_count": len(cited_set - invalid),
    }
