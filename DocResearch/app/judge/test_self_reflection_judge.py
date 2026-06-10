"""
Self-Reflection Judge 单元测试: mock 重依赖，验证规则评估、阈值、failure_type、run_from_state。"""

import sys
import os
import unittest
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

for mod in [
    "langchain_community", "langchain_huggingface", "langchain_openai",
    "langgraph.graph", "rank_bm25", "sentence_transformers",
]:
    if mod in sys.modules:
        del sys.modules[mod]
    sys.modules[mod] = MagicMock()

from app.judge.self_reflection_judge import (
    JudgeResult,
    JudgeOutput,
    rule_based_judge,
    judge_answer,
    run_from_state,
)


class TestRuleBasedJudge(unittest.TestCase):
    def test_high_quality_pass(self):
        context_pack = [{"citation_id": f"D1-C{i:03d}"} for i in range(5)]
        result = rule_based_judge(
            question="RAG retrieval augmented generation",
            answer="RAG retrieval augmented generation combines retrieval and generation RAG retrieval augmented generation [D1-C000] [D1-C001] [D1-C002] [D1-C003] [D1-C004]",
            context_pack=context_pack,
            used_citations=["D1-C000", "D1-C001", "D1-C002", "D1-C003", "D1-C004"],
            unsupported_claims=[],
        )
        self.assertTrue(result.pass_)
        self.assertEqual(result.failure_type, "none")

    def test_no_citations_fails(self):
        context_pack = [{"citation_id": "D1-C000"}]
        result = rule_based_judge(
            question="什么是 RAG",
            answer="RAG 是一种技术",
            context_pack=context_pack,
            used_citations=[],
        )
        self.assertFalse(result.pass_)
        self.assertEqual(result.failure_type, "citation_error")

    def test_unsupported_claims_reduce_faithfulness(self):
        context_pack = [{"citation_id": f"D1-C{i:03d}"} for i in range(5)]
        result = rule_based_judge(
            question="什么是 RAG",
            answer="RAG 是检索增强生成 [D1-C000]",
            context_pack=context_pack,
            used_citations=["D1-C000"],
            unsupported_claims=["claim1", "claim2", "claim3", "claim4"],
        )
        self.assertLess(result.faithfulness, 0.5)

    def test_small_context_pack_low_sufficiency(self):
        context_pack = [{"citation_id": "D1-C000"}]
        result = rule_based_judge(
            question="详细解释 RAG",
            answer="RAG 是检索增强生成 [D1-C000]",
            context_pack=context_pack,
            used_citations=["D1-C000"],
        )
        self.assertLess(result.context_sufficiency, 0.5)


class TestJudgeAnswer(unittest.TestCase):
    def test_rule_based_by_default(self):
        context_pack = [{"citation_id": f"D1-C{i:03d}"} for i in range(5)]
        output = judge_answer(
            question="什么是 RAG 检索增强生成",
            answer="RAG 是检索增强生成 [D1-C000] [D1-C001] [D1-C002]",
            context_pack=context_pack,
            used_citations=["D1-C000", "D1-C001", "D1-C002"],
        )
        self.assertEqual(output.status, "ok")
        self.assertFalse(output.trace["fallback_used"])

    @patch("app.llm.get_llm")
    def test_llm_failure_fallback_to_rule(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM error")
        mock_get_llm.return_value = mock_llm
        context_pack = [{"citation_id": f"D1-C{i:03d}"} for i in range(5)]
        output = judge_answer(
            question="什么是 RAG",
            answer="RAG 是检索增强生成 [D1-C000] [D1-C001]",
            context_pack=context_pack,
            used_citations=["D1-C000", "D1-C001"],
            use_llm=True,
        )
        self.assertEqual(output.status, "ok")
        self.assertTrue(output.trace["fallback_used"])


class TestRunFromState(unittest.TestCase):
    def test_run_from_state_pass(self):
        context_pack = [{"citation_id": f"D1-C{i:03d}"} for i in range(5)]
        state = {
            "question": "RAG retrieval augmented generation",
            "answer": "RAG retrieval augmented generation combines retrieval and generation RAG retrieval augmented generation [D1-C000] [D1-C001] [D1-C002] [D1-C003] [D1-C004]",
            "context_pack": context_pack,
            "used_citations": ["D1-C000", "D1-C001", "D1-C002", "D1-C003", "D1-C004"],
            "unsupported_claims": [],
        }
        result = run_from_state(state)
        self.assertIn("judge_result", result)
        self.assertEqual(result["failure_type"], "none")

    def test_run_from_state_fail(self):
        state = {
            "question": "什么是 RAG",
            "answer": "RAG 是一种技术",
            "context_pack": [{"citation_id": "D1-C000"}],
            "used_citations": [],
            "unsupported_claims": [],
        }
        result = run_from_state(state)
        self.assertEqual(result["failure_type"], "citation_error")


class TestSchemas(unittest.TestCase):
    def test_judge_result_schema(self):
        jr = JudgeResult(pass_=True, answer_relevance=0.9, failure_type="none")
        self.assertTrue(jr.pass_)
        self.assertEqual(jr.failure_type, "none")

    def test_judge_output_schema(self):
        jo = JudgeOutput(status="ok", result=JudgeResult(pass_=True))
        self.assertEqual(jo.status, "ok")


def run_all_tests():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    run_all_tests()
