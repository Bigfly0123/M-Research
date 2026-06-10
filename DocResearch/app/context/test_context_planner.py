"""
Context Planner 单元测试: 规划器 schema + 规则版 + trace + run_from_state。
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

from app.context.context_planner import (
    ContextPlan, ContextPlanOutput, rule_based_plan, plan_context, run_from_state,
)


def test_context_plan_schema():
    plan = ContextPlan(query_type="fact", intent="test", rewritten_query="what is RAG")
    assert plan.query_type == "fact"
    assert plan.risk_level == "citation_sensitive"
    assert plan.context_budget > 0
    d = plan.model_dump()
    assert "retrieval_plan" in d
    assert "judge_focus" in d


def test_rule_based_comparison():
    plan = rule_based_plan("对比 dense 和 BM25 的区别")
    assert plan.query_type == "comparison"
    assert "graph_expand" in plan.retrieval_plan
    assert plan.context_budget == 4500


def test_rule_based_multi_hop():
    plan = rule_based_plan("为什么 retrieval miss 会触发 repair?")
    assert plan.query_type == "multi_hop"
    assert "graph_expand" in plan.retrieval_plan


def test_rule_based_code():
    plan = rule_based_plan("DenseRetriever 函数的参数有哪些?")
    assert plan.query_type == "code_understanding"
    assert plan.need_code_blocks is True


def test_rule_based_fact():
    plan = rule_based_plan("什么是 ContextPlanner?")
    assert plan.query_type == "fact"


def test_rule_based_default():
    plan = rule_based_plan("介绍下系统的整体架构")
    assert plan.query_type == "concept"
    assert "graph_expand" in plan.retrieval_plan


def test_rule_based_troubleshooting():
    plan = rule_based_plan("BM25 报错 debug 修复")
    assert plan.query_type == "troubleshooting"


def test_plan_context_ok():
    result = plan_context("如何使用 HybridRetriever?", use_llm=False)
    assert result.status == "ok"
    assert result.plan is not None
    assert result.plan.query_type in ["multi_hop", "concept", "fact", "comparison", "code_understanding", "troubleshooting"]
    assert "fallback_used" in result.trace
    assert "latency_ms" in result.trace


def test_plan_context_empty():
    result = plan_context("", use_llm=False)
    assert result.status == "fail"
    assert result.next_action == "check_input"


def test_plan_context_trace_fields():
    result = plan_context("对比 BM25 和 dense", use_llm=False)
    t = result.trace
    assert t["module"] == "ContextPlanner"
    assert t["query_type"] is not None
    assert t["retrieval_plan"] is not None
    assert t["context_budget"] > 0
    assert t["risk_level"] == "citation_sensitive"
    assert "fallback_used" in t


def test_run_from_state():
    state = {"question": "如何使用 RAG?", "use_llm": False}
    update = run_from_state(state)
    assert "context_plan" in update
    assert "query_type" in update
    assert "retrieval_plan" in update
    assert "context_budget" in update
    assert "rewrite_query" in update


def test_context_plan_output_serialization():
    result = plan_context("什么是 BM25?", use_llm=False)
    d = result.model_dump()
    assert isinstance(d, dict)
    assert d["status"] == "ok"
    assert isinstance(d["plan"], dict)


def test_judge_focus():
    plan = rule_based_plan("对比两种检索方式的区别")
    assert "context_sufficiency" in plan.judge_focus
    plan2 = rule_based_plan("为什么 repair 会被触发?")
    assert "answer_relevance" in plan2.judge_focus


def run_all_tests():
    tests = [
        test_context_plan_schema,
        test_rule_based_comparison,
        test_rule_based_multi_hop,
        test_rule_based_code,
        test_rule_based_fact,
        test_rule_based_default,
        test_rule_based_troubleshooting,
        test_plan_context_ok,
        test_plan_context_empty,
        test_plan_context_trace_fields,
        test_run_from_state,
        test_context_plan_output_serialization,
        test_judge_focus,
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
    print("Running Context Planner tests...")
    run_all_tests()
