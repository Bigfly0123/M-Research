"""
MultiHop-RAG 评测指标函数。

指标:
- gold_doc_recall_at_k: top-k 检索结果覆盖了多少 gold documents
- all_gold_docs_hit_at_k: 是否所有 gold documents 都进入 top-k
- gold_chunk_recall_at_k: top-k chunk 是否覆盖 gold chunks
- selected_evidence_recall: Evidence Composer 是否保留了正确证据
- answer_keyword_coverage: 答案关键词覆盖率
"""
from typing import List, Optional, Set


def gold_doc_recall_at_k(
    retrieved_doc_ids: List[str],
    gold_doc_ids: List[str],
    k: int,
) -> Optional[float]:
    """top-k 检索结果覆盖了多少 gold documents。"""
    topk: Set[str] = set(retrieved_doc_ids[:k])
    gold: Set[str] = set(gold_doc_ids)
    if not gold:
        return None
    return len(topk & gold) / len(gold)


def all_gold_docs_hit_at_k(
    retrieved_doc_ids: List[str],
    gold_doc_ids: List[str],
    k: int,
) -> Optional[int]:
    """判断是否所有 gold documents 都进入 top-k。返回 0 或 1。"""
    topk: Set[str] = set(retrieved_doc_ids[:k])
    gold: Set[str] = set(gold_doc_ids)
    if not gold:
        return None
    return int(gold.issubset(topk))


def gold_chunk_recall_at_k(
    retrieved_chunk_ids: List[str],
    gold_chunk_ids: List[str],
    k: int,
) -> Optional[float]:
    """top-k chunk 是否覆盖 gold chunks。"""
    topk: Set[str] = set(retrieved_chunk_ids[:k])
    gold: Set[str] = set(gold_chunk_ids)
    if not gold:
        return None
    return len(topk & gold) / len(gold)


def selected_evidence_recall(
    selected_chunk_ids: List[str],
    gold_chunk_ids: List[str],
) -> Optional[float]:
    """Evidence Composer 是否保留了正确证据。"""
    selected: Set[str] = set(selected_chunk_ids)
    gold: Set[str] = set(gold_chunk_ids)
    if not gold:
        return None
    return len(selected & gold) / len(gold)


def answer_keyword_coverage(
    answer: str,
    expected_answer: str,
) -> float:
    """答案关键词覆盖率: expected_answer 中的词有多少出现在 answer 中。"""
    if not expected_answer or not answer:
        return 0.0

    expected_tokens = set(expected_answer.lower().split())
    answer_tokens = set(answer.lower().split())

    if not expected_tokens:
        return 0.0

    overlap = expected_tokens & answer_tokens
    return len(overlap) / len(expected_tokens)
