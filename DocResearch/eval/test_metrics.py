"""
metrics.py 单元测试。
"""
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from eval.metrics import (
    gold_doc_recall_at_k,
    all_gold_docs_hit_at_k,
    gold_chunk_recall_at_k,
    selected_evidence_recall,
    answer_keyword_coverage,
)


def test_gold_doc_recall_at_k():
    # 全部命中
    assert gold_doc_recall_at_k(["a", "b", "c"], ["a", "b"], 3) == 1.0
    # 部分命中
    assert gold_doc_recall_at_k(["a", "b", "c"], ["b", "d"], 3) == 0.5
    # 未命中
    assert gold_doc_recall_at_k(["a", "b"], ["c", "d"], 3) == 0.0
    # gold 为空
    assert gold_doc_recall_at_k(["a"], [], 3) is None
    # k 限制
    assert gold_doc_recall_at_k(["a", "b", "c"], ["c"], 2) == 0.0
    assert gold_doc_recall_at_k(["a", "b", "c"], ["c"], 3) == 1.0
    print("test_gold_doc_recall_at_k 通过")


def test_all_gold_docs_hit_at_k():
    # 全部命中
    assert all_gold_docs_hit_at_k(["a", "b", "c"], ["a", "b"], 3) == 1
    # 未全部命中
    assert all_gold_docs_hit_at_k(["a", "b"], ["b", "c"], 3) == 0
    # gold 为空
    assert all_gold_docs_hit_at_k(["a"], [], 3) is None
    print("test_all_gold_docs_hit_at_k 通过")


def test_gold_chunk_recall_at_k():
    assert gold_chunk_recall_at_k(["c1", "c2", "c3"], ["c2", "c3"], 3) == 1.0
    assert gold_chunk_recall_at_k(["c1", "c2"], ["c2", "c3"], 3) == 0.5
    assert gold_chunk_recall_at_k([], ["c1"], 3) == 0.0
    assert gold_chunk_recall_at_k(["c1"], [], 3) is None
    print("test_gold_chunk_recall_at_k 通过")


def test_selected_evidence_recall():
    assert selected_evidence_recall(["c1", "c2"], ["c2", "c3"]) == 0.5
    assert selected_evidence_recall(["c1", "c2", "c3"], ["c2", "c3"]) == 1.0
    assert selected_evidence_recall([], ["c1"]) == 0.0
    assert selected_evidence_recall(["c1"], []) is None
    print("test_selected_evidence_recall 通过")


def test_answer_keyword_coverage():
    # 完全覆盖
    assert answer_keyword_coverage("Sam Bankman-Fried", "Sam Bankman-Fried") == 1.0
    # 部分覆盖
    r = answer_keyword_coverage("Sam was the CEO", "Sam Bankman-Fried")
    assert 0 < r < 1
    # 空值
    assert answer_keyword_coverage("", "answer") == 0.0
    assert answer_keyword_coverage("answer", "") == 0.0
    assert answer_keyword_coverage("", "") == 0.0
    print("test_answer_keyword_coverage 通过")


if __name__ == "__main__":
    test_gold_doc_recall_at_k()
    test_all_gold_docs_hit_at_k()
    test_gold_chunk_recall_at_k()
    test_selected_evidence_recall()
    test_answer_keyword_coverage()
    print("\n全部测试通过！")
