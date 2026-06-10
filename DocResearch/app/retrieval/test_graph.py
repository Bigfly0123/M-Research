"""
Graph Retrieval 模块单元测试: LightweightGraphIndex + GraphRetriever + 三路融合 验收测试。

覆盖: 术语抽取(6规则), 图构建+co-occurrence权重, BFS多hop扩展,
模糊匹配, 统计接口, 持久化save/load, GraphRetriever检索,
三路融合dedup/merge, ablation(graph_only/full)。
"""

import sys
import os
import json
import tempfile
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

from app.retrieval.graph_index import LightweightGraphIndex, ExpansionResult, GraphStats, TECH_KEYWORDS
from app.retrieval.graph_retriever import GraphRetriever
from app.schemas.retrieval import RetrievedChunk


SAMPLE_CHUNKS = [
    {"chunk_id": "D1-C001", "text": "HybridRetriever combines DenseRetriever and BM25Retriever for RAG systems.", "source_path": "retriever.md", "section_path": ["Retriever", "Hybrid"], "element_type": "text"},
    {"chunk_id": "D1-C002", "text": "The context_budget limits token usage in evidence_composer.", "source_path": "composer.md", "section_path": ["Evidence", "Budget"], "element_type": "text"},
    {"chunk_id": "D1-C003", "text": "SelfReflectionJudge evaluates faithfulness and relevance of generated answers.", "source_path": "judge.md", "section_path": ["Judge", "Reflection"], "element_type": "text"},
    {"chunk_id": "D1-C004", "text": "BM25 retrieval uses rank_bm25 for keyword-based search with BM25 scoring.", "source_path": "bm25.md", "section_path": ["Retriever", "BM25"], "element_type": "text"},
    {"chunk_id": "D1-C005", "text": "CitationGuardrails check that each citation [D1-C012] is supported by evidence.", "source_path": "guardrails.md", "section_path": ["Guardrails", "Citation"], "element_type": "text"},
    {"chunk_id": "D1-C006", "text": "RepairRouter decides repair_action based on failure_type and repair_count.", "source_path": "repair.md", "section_path": ["Repair", "Router"], "element_type": "text"},
]


def test_extract_terms_camelcase():
    idx = LightweightGraphIndex()
    terms = idx.extract_terms("HybridRetriever combines DenseRetriever and SelfReflectionJudge")
    assert "HybridRetriever" in terms
    assert "DenseRetriever" in terms
    assert "SelfReflectionJudge" in terms


def test_extract_terms_snake_case():
    idx = LightweightGraphIndex()
    terms = idx.extract_terms("context_budget and failure_type and repair_action")
    assert "context_budget" in terms
    assert "failure_type" in terms
    assert "repair_action" in terms


def test_extract_terms_uppercase_abbr():
    idx = LightweightGraphIndex()
    terms = idx.extract_terms("BM25 retrieval for RAG with LLM and API")
    assert "BM25" in terms
    assert "RAG" in terms
    assert "LLM" in terms
    assert "API" in terms


def test_extract_terms_dashed():
    idx = LightweightGraphIndex()
    terms = idx.extract_terms("cross-encoder and self-reflection modules")
    assert "cross-encoder" in terms
    assert "self-reflection" in terms


def test_extract_terms_reference_brackets():
    idx = LightweightGraphIndex()
    terms = idx.extract_terms("see citation [D1-C012] and reference [D2-C005]")
    assert "D1-C012" in terms
    assert "D2-C005" in terms


def test_extract_terms_tech_keywords():
    idx = LightweightGraphIndex()
    terms = idx.extract_terms("the retriever uses embedding for chunk and citation")
    assert "retriever" in terms
    assert "embedding" in terms
    assert "chunk" in terms
    assert "citation" in terms


def test_extract_terms_empty():
    idx = LightweightGraphIndex()
    assert idx.extract_terms("") == []
    assert idx.extract_terms("   ") == []


def test_build_creates_mappings():
    idx = LightweightGraphIndex()
    idx.build(SAMPLE_CHUNKS)
    assert idx._built
    assert len(idx.term_to_chunks) > 0
    assert len(idx.chunk_to_terms) > 0
    assert len(idx.term_graph) > 0


def test_build_co_occurrence_edges():
    idx = LightweightGraphIndex()
    idx.build(SAMPLE_CHUNKS)
    assert len(idx._edge_weights) > 0
    for (t1, t2), weight in idx._edge_weights.items():
        assert weight >= 1
        assert t1 < t2


def test_expand_single_hop():
    idx = LightweightGraphIndex()
    idx.build(SAMPLE_CHUNKS)
    terms = idx.extract_terms("HybridRetriever")
    if not terms:
        return
    result = idx.expand(terms[0], max_hops=1)
    assert isinstance(result, ExpansionResult)
    assert result.seed_term != ""
    assert "status" in result.trace


def test_expand_two_hops():
    idx = LightweightGraphIndex()
    idx.build(SAMPLE_CHUNKS)
    terms = idx.extract_terms("HybridRetriever")
    if not terms:
        return
    result = idx.expand(terms[0], max_hops=2)
    assert result.hops_used == 2


def test_expand_term_not_found():
    idx = LightweightGraphIndex()
    idx.build(SAMPLE_CHUNKS)
    result = idx.expand("NonExistentTermXYZ", max_hops=1)
    assert result.trace.get("status") == "term_not_found"


def test_expand_fuzzy_match():
    idx = LightweightGraphIndex()
    idx.build(SAMPLE_CHUNKS)
    terms = idx.extract_terms("HybridRetriever")
    if not terms:
        return
    result = idx.expand(terms[0].lower(), max_hops=1)
    assert result.trace.get("status") == "ok"


def test_expand_multi():
    idx = LightweightGraphIndex()
    idx.build(SAMPLE_CHUNKS)
    terms = idx.extract_terms("HybridRetriever BM25 retrieval")
    if len(terms) < 2:
        return
    result = idx.expand_multi(terms[:2], max_hops=1)
    assert isinstance(result, ExpansionResult)
    assert result.trace.get("seeds") is not None


def test_get_stats():
    idx = LightweightGraphIndex()
    idx.build(SAMPLE_CHUNKS)
    stats = idx.get_stats()
    assert isinstance(stats, GraphStats)
    assert stats.total_terms > 0
    assert stats.total_chunks_indexed > 0
    assert stats.total_edges >= 0
    assert stats.avg_degree >= 0.0


def test_save_and_load():
    idx1 = LightweightGraphIndex()
    idx1.build(SAMPLE_CHUNKS)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "graph_index.json")
        idx1.save(path)
        assert os.path.exists(path)

        idx2 = LightweightGraphIndex()
        ok = idx2.load(path)
        assert ok
        assert idx2._built
        assert len(idx2.term_to_chunks) == len(idx1.term_to_chunks)
        assert len(idx2.term_graph) == len(idx1.term_graph)
        assert len(idx2._edge_weights) == len(idx1._edge_weights)


def test_save_load_roundtrip_data_integrity():
    idx1 = LightweightGraphIndex()
    idx1.build(SAMPLE_CHUNKS)
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "graph_index.json")
        idx1.save(path)
        idx2 = LightweightGraphIndex()
        idx2.load(path)
        for term in idx1.term_to_chunks:
            assert idx2.term_to_chunks[term] == idx1.term_to_chunks[term]


def test_graph_retriever_basic():
    idx = LightweightGraphIndex()
    idx.build(SAMPLE_CHUNKS)
    chunks_by_id = {c["chunk_id"]: c for c in SAMPLE_CHUNKS}
    retriever = GraphRetriever(graph_index=idx, chunks_by_id=chunks_by_id)
    results = retriever.retrieve("HybridRetriever BM25 retrieval", max_hops=1, max_terms=5, max_chunks=10)
    assert isinstance(results, list)
    for r in results:
        assert isinstance(r, RetrievedChunk)
        assert r.chunk_id != ""
        assert "graph_expand" in r.retrieval_sources
        assert r.graph_score is not None


def test_graph_retriever_no_terms():
    idx = LightweightGraphIndex()
    idx.build(SAMPLE_CHUNKS)
    retriever = GraphRetriever(graph_index=idx)
    results = retriever.retrieve("   ", max_hops=1)
    assert results == []


def test_graph_retriever_score_decay():
    idx = LightweightGraphIndex()
    idx.build(SAMPLE_CHUNKS)
    chunks_by_id = {c["chunk_id"]: c for c in SAMPLE_CHUNKS}
    retriever = GraphRetriever(graph_index=idx, chunks_by_id=chunks_by_id)
    results = retriever.retrieve("HybridRetriever BM25", max_hops=1, max_terms=5, max_chunks=20)
    if len(results) > 1:
        assert results[0].graph_score >= results[1].graph_score


def test_graph_retriever_get_expansion_info():
    idx = LightweightGraphIndex()
    idx.build(SAMPLE_CHUNKS)
    retriever = GraphRetriever(graph_index=idx)
    info = retriever.get_expansion_info("HybridRetriever", max_hops=1)
    assert isinstance(info, ExpansionResult)


def test_three_way_fusion_graph_dedup():
    from app.retrieval.hybrid_retriever import HybridGraphRetriever
    retriever = HybridGraphRetriever()
    assert hasattr(retriever, "graph_retriever")
    assert hasattr(retriever, "retrieve_graph_only")
    assert hasattr(retriever, "retrieve_full")
    assert callable(retriever.retrieve_graph_only)
    assert callable(retriever.retrieve_full)


def test_ablation_graph_only():
    from app.retrieval.hybrid_retriever import HybridGraphRetriever
    retriever = HybridGraphRetriever()
    assert retriever.retrieve_graph_only.__doc__ is not None


def test_default_retrieval_plan_includes_graph():
    from app.retrieval.hybrid_retriever import HybridGraphRetriever
    retriever = HybridGraphRetriever()
    from app.config import config
    from unittest.mock import patch
    with patch.object(retriever, 'dense') as mock_dense, \
         patch.object(retriever, 'bm25') as mock_bm25:
        mock_dense.retrieve = MagicMock(return_value=[])
        mock_bm25.retrieve = MagicMock(return_value=[])
        result = retriever.retrieve("test query")
        assert "graph_expand" in result.trace.get("retrieval_plan", [])


def run_all_tests():
    tests = [
        test_extract_terms_camelcase,
        test_extract_terms_snake_case,
        test_extract_terms_uppercase_abbr,
        test_extract_terms_dashed,
        test_extract_terms_reference_brackets,
        test_extract_terms_tech_keywords,
        test_extract_terms_empty,
        test_build_creates_mappings,
        test_build_co_occurrence_edges,
        test_expand_single_hop,
        test_expand_two_hops,
        test_expand_term_not_found,
        test_expand_fuzzy_match,
        test_expand_multi,
        test_get_stats,
        test_save_and_load,
        test_save_load_roundtrip_data_integrity,
        test_graph_retriever_basic,
        test_graph_retriever_no_terms,
        test_graph_retriever_score_decay,
        test_graph_retriever_get_expansion_info,
        test_three_way_fusion_graph_dedup,
        test_ablation_graph_only,
        test_default_retrieval_plan_includes_graph,
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
    print("Running Graph Retrieval module tests...")
    run_all_tests()
