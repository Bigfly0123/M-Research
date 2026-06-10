"""
Evidence Composer 单元测试: 去重、角色分类、budget截断、schema、trace。
"""

import sys
import os
from unittest.mock import MagicMock

import types

def _make_mock_package(name):
    parts = name.split('.')
    for i in range(len(parts)):
        subname = '.'.join(parts[:i+1])
        if subname not in sys.modules:
            sys.modules[subname] = MagicMock()

for pkg in [
    "langchain_community.vectorstores",
    "langchain_community.document_loaders",
    "langchain_huggingface",
    "langchain_openai",
    "langgraph.graph",
    "rank_bm25",
    "sentence_transformers",
    "sentence_transformers.cross_encoder",
]:
    _make_mock_package(pkg)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.evidence.evidence_composer import (
    EvidenceItem, ContextPack, deduplicate, classify_role,
    compose_context_pack, run_from_state,
)


SAMPLE_CHUNKS = [
    {"chunk_id": "D1-C001", "text": "HybridRetriever is defined as a class that combines dense and BM25 retrieval.", "source": "retriever.md", "section": "Retriever > Hybrid", "final_score": 0.9},
    {"chunk_id": "D1-C002", "text": "To use the retriever, follow these steps: 1. Build index 2. Call retrieve", "source": "retriever.md", "section": "Retriever > Usage", "final_score": 0.8},
    {"chunk_id": "D1-C003", "text": "Example: retriever.retrieve('query') returns RetrievalOutput", "source": "retriever.md", "section": "Retriever > Example", "final_score": 0.7},
    {"chunk_id": "D1-C004", "text": "The system has a limitation: it cannot handle real-time streaming.", "source": "system.md", "section": "System > Limits", "final_score": 0.6},
    {"chunk_id": "D1-C005", "text": "def build_index(chunks, index_dir): self.dense.build_index(chunks)", "source": "retriever.md", "section": "Retriever > Code", "final_score": 0.75},
]


def test_evidence_item_schema():
    item = EvidenceItem(citation_id="D1-C001", chunk_id="D1-C001", evidence_text="test", role="definition", support_score=0.9)
    assert item.role == "definition"
    d = item.model_dump()
    assert "section_path" in d
    assert "compressed_text" in d


def test_deduplicate():
    chunks = [{"chunk_id": "A"}, {"chunk_id": "B"}, {"chunk_id": "A"}]
    kept, dropped = deduplicate(chunks)
    assert len(kept) == 2
    assert len(dropped) == 1


def test_classify_role_definition():
    chunk = {"text": "BM25 is defined as a keyword retrieval algorithm."}
    assert classify_role(chunk, "") == "definition"


def test_classify_role_procedure():
    chunk = {"text": "To configure, follow these steps: step 1, step 2"}
    assert classify_role(chunk, "") == "procedure"


def test_classify_role_comparison():
    chunk = {"text": "Compare dense vs BM25 retrieval differences"}
    assert classify_role(chunk, "") == "comparison"


def test_classify_role_example():
    chunk = {"text": "For example, you can use retriever.retrieve()"}
    assert classify_role(chunk, "") == "example"


def test_classify_role_code():
    chunk = {"text": "def retrieve(query, k=10): return results"}
    assert classify_role(chunk, "") == "code"


def test_classify_role_limitation():
    chunk = {"text": "This approach has a limitation: it does not support streaming."}
    assert classify_role(chunk, "") == "limitation"


def test_compose_context_pack_ok():
    result = compose_context_pack(SAMPLE_CHUNKS, "how to use retriever", context_budget=5000)
    assert result.status in ("ok", "warn")
    assert len(result.context_pack) > 0
    assert result.total_context_tokens > 0
    assert "fallback_used" in result.trace


def test_compose_context_pack_empty():
    result = compose_context_pack([], "test", context_budget=3500)
    assert result.status == "fail"


def test_compose_context_pack_budget():
    result = compose_context_pack(SAMPLE_CHUNKS, "test", context_budget=10)
    assert len(result.dropped_chunks) > 0


def test_compose_context_pack_roles():
    result = compose_context_pack(SAMPLE_CHUNKS, "test", context_budget=5000)
    roles = {item.role for item in result.context_pack}
    assert len(roles) > 0


def test_context_pack_serialization():
    result = compose_context_pack(SAMPLE_CHUNKS, "test", context_budget=5000)
    d = result.model_dump()
    assert isinstance(d, dict)
    assert isinstance(d["context_pack"], list)


def test_run_from_state():
    state = {"retrieved_chunks": SAMPLE_CHUNKS, "question": "how to use", "context_budget": 5000}
    update = run_from_state(state)
    assert "context_pack" in update
    assert "dropped_chunks" in update


def run_all_tests():
    tests = [
        test_evidence_item_schema,
        test_deduplicate,
        test_classify_role_definition,
        test_classify_role_procedure,
        test_classify_role_comparison,
        test_classify_role_example,
        test_classify_role_code,
        test_classify_role_limitation,
        test_compose_context_pack_ok,
        test_compose_context_pack_empty,
        test_compose_context_pack_budget,
        test_compose_context_pack_roles,
        test_context_pack_serialization,
        test_run_from_state,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS: {test.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL: {test.__name__} - {e}")
        except Exception as e:
            failed += 1
            print(f"  ERROR: {test.__name__} - {e}")
    print(f"\nResults: {passed} passed, {failed} failed, {len(tests)} total")
    return failed == 0


if __name__ == "__main__":
    print("Running Evidence Composer tests...")
    run_all_tests()
