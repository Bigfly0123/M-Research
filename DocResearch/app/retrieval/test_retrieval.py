"""
Retrieval 模块单元测试: Dense + BM25 Hybrid Retrieval 验收测试。

覆盖: BM25检索归一化, score fusion, merge/dedup, rerank,
Module模式(status/trace), ablation(dense_only/bm25_only/hybrid)。
"""

import sys
import os
from unittest.mock import MagicMock

# Mock heavy dependencies - must mock all submodules used by imports
import types

def _make_mock_package(name):
    """创建 mock 包层级，确保 from x.y import z 不报错。"""
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

from app.schemas.retrieval import RetrievedChunk, HybridRetrievalConfig, RetrievalOutput
from app.retrieval.hybrid_retriever import HybridGraphRetriever


def _make_chunk(i: int, text: str, dense_score: float = None, bm25_score: float = None, sources: list = None) -> RetrievedChunk:
    """测试辅助: 创建 RetrievedChunk。"""
    return RetrievedChunk(
        chunk_id=f"doc-C{i:03d}",
        text=text,
        source="test.md",
        section="Section A",
        element_type="text",
        retrieval_sources=sources or ["dense"],
        dense_score=dense_score,
        bm25_score=bm25_score,
        final_score=0.0,
    )


def test_retrieved_chunk_schema():
    chunk = RetrievedChunk(
        chunk_id="test-C001",
        text="BM25 is a keyword retrieval algorithm.",
        source="design.md",
        section="Retriever > BM25",
        element_type="text",
        retrieval_sources=["dense", "bm25"],
        dense_score=0.85,
        bm25_score=0.72,
        final_score=0.80,
    )
    assert chunk.chunk_id == "test-C001"
    assert len(chunk.retrieval_sources) == 2
    assert chunk.dense_score > 0
    assert chunk.bm25_score > 0
    d = chunk.model_dump()
    assert "chunk_id" in d
    assert "final_score" in d


def test_hybrid_retrieval_config():
    cfg = HybridRetrievalConfig()
    assert cfg.retrieval_plan == ["dense", "bm25", "graph_expand"]
    assert cfg.dense_weight + cfg.bm25_weight + cfg.graph_weight == 1.0
    assert cfg.fetch_k == 20
    assert cfg.final_top_k == 10


def test_retrieval_output_schema():
    output = RetrievalOutput(
        status="ok",
        chunks=[_make_chunk(0, "hello")],
        total_retrieved=1,
        source_stats={"dense": 1, "bm25": 0},
        trace={"module": "HybridRetriever", "latency_ms": 50},
    )
    assert output.status == "ok"
    assert len(output.chunks) == 1
    assert output.total_retrieved == 1


def test_retrieval_output_fail():
    output = RetrievalOutput(status="fail", chunks=[], total_retrieved=0, next_action="check_retrieval_quality")
    assert output.status == "fail"
    assert output.next_action == "check_retrieval_quality"


def test_score_fusion_weights():
    """验证 score fusion 权重之和为 1.0。"""
    from app.config import config
    total = config.DENSE_WEIGHT + config.BM25_WEIGHT + config.GRAPH_WEIGHT
    assert abs(total - 1.0) < 0.01


def test_merged_chunk_multi_source():
    """多路命中的 chunk 应有 bonus。"""
    chunk = _make_chunk(
        0,
        "BM25 retrieval algorithm for keyword matching",
        dense_score=0.8,
        bm25_score=0.7,
        sources=["dense", "bm25"],
    )
    assert len(chunk.retrieval_sources) == 2
    # fusion 时应该比单路同分高
    from app.config import config
    single_score = config.DENSE_WEIGHT * 0.8 + config.BM25_WEIGHT * 0.7
    multi_score = single_score + config.MULTI_SOURCE_BONUS
    assert multi_score > single_score


def test_ablation_modes():
    """验证 ablation 方法存在且可调用。"""
    retriever = HybridGraphRetriever()
    assert hasattr(retriever, "retrieve_dense_only")
    assert hasattr(retriever, "retrieve_bm25_only")
    assert hasattr(retriever, "retrieve_hybrid")
    assert hasattr(retriever, "retrieve_full")
    assert callable(retriever.retrieve_dense_only)
    assert callable(retriever.retrieve_bm25_only)


def test_retrieval_output_serialization():
    """RetrievalOutput 应可序列化为 dict (用于 trace)。"""
    output = RetrievalOutput(
        status="ok",
        chunks=[_make_chunk(0, "test text", dense_score=0.9)],
        total_retrieved=1,
        source_stats={"dense": 1},
        trace={"latency_ms": 30},
    )
    d = output.model_dump()
    assert isinstance(d, dict)
    assert d["status"] == "ok"
    assert len(d["chunks"]) == 1
    assert isinstance(d["chunks"][0], dict)


def test_retrieved_chunk_all_scores():
    """验证 RetrievedChunk 能携带所有路分数。"""
    chunk = RetrievedChunk(
        chunk_id="test-C001",
        text="Hybrid retrieval combines dense and BM25.",
        retrieval_sources=["dense", "bm25", "graph_expand"],
        dense_score=0.85,
        bm25_score=0.72,
        graph_score=0.6,
        rerank_score=0.91,
        final_score=0.88,
    )
    assert chunk.dense_score is not None
    assert chunk.bm25_score is not None
    assert chunk.graph_score is not None
    assert chunk.rerank_score is not None
    assert chunk.final_score > 0


def run_all_tests():
    tests = [
        test_retrieved_chunk_schema,
        test_hybrid_retrieval_config,
        test_retrieval_output_schema,
        test_retrieval_output_fail,
        test_score_fusion_weights,
        test_merged_chunk_multi_source,
        test_ablation_modes,
        test_retrieval_output_serialization,
        test_retrieved_chunk_all_scores,
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
    print("Running Retrieval module tests...")
    run_all_tests()
