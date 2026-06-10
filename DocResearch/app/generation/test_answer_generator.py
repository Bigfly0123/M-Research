"""
Answer Generator 单元测试: mock 重依赖，验证规则自检、fallback、schema、run_from_state。"""

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

from app.generation.answer_generator import (
    GroundedAnswer,
    AnswerGeneratorOutput,
    rule_check_citations,
    generate_answer,
    run_from_state,
)


class TestRuleCheckCitations(unittest.TestCase):
    def test_all_valid(self):
        result = rule_check_citations("a [D1-C001] b [D2-C003]", {"D1-C001", "D2-C003"})
        self.assertTrue(result["all_valid"])
        self.assertEqual(result["valid_count"], 2)

    def test_has_invalid(self):
        result = rule_check_citations("a [D1-C001] b [D9-C999]", {"D1-C001"})
        self.assertFalse(result["all_valid"])
        self.assertEqual(result["invalid_citations"], ["[D9-C999]"])

    def test_no_citations(self):
        result = rule_check_citations("no citations here", {"D1-C001"})
        self.assertTrue(result["all_valid"])
        self.assertEqual(result["found_citations"], [])


class TestGenerateAnswer(unittest.TestCase):
    def setUp(self):
        self.context_pack = [
            {"citation_id": "D1-C001", "source": "doc1", "section": "s1", "compressed_text": "内容1", "evidence_text": "内容1"},
            {"citation_id": "D2-C003", "source": "doc2", "section": "s2", "compressed_text": "内容2", "evidence_text": "内容2"},
        ]

    @patch("app.generation.answer_generator.generate_answer")
    def test_run_from_state(self, mock_gen):
        mock_gen.return_value = AnswerGeneratorOutput(
            status="ok",
            result=GroundedAnswer(answer="test", used_citations=["D1-C001"], confidence="high"),
            trace={"module": "AnswerGenerator", "citations_used": 1, "confidence": "high", "fallback_used": False, "latency_ms": 10},
        )
        state = {"question": "q", "context_pack": self.context_pack, "query_type": "concept"}
        result = run_from_state(state)
        self.assertEqual(result["answer"], "test")
        self.assertEqual(result["answer_confidence"], "high")

    def test_empty_context_pack(self):
        output = generate_answer("question", [])
        self.assertEqual(output.status, "fail")
        self.assertIsNotNone(output.result)
        self.assertEqual(output.result.confidence, "low")
        self.assertEqual(output.next_action, "check_retrieval")

    @patch("app.llm.get_llm")
    def test_llm_success(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.return_value = MagicMock(content='{"answer": "ans [D1-C001]", "used_citations": ["D1-C001"], "unsupported_claims": [], "confidence": "high"}')
        mock_get_llm.return_value = mock_llm
        output = generate_answer("question", self.context_pack)
        self.assertEqual(output.status, "ok")
        self.assertEqual(output.result.confidence, "high")
        self.assertFalse(output.trace["fallback_used"])

    @patch("app.llm.get_llm")
    def test_llm_failure_fallback(self, mock_get_llm):
        mock_llm = MagicMock()
        mock_llm.invoke.side_effect = Exception("LLM error")
        mock_get_llm.return_value = mock_llm
        output = generate_answer("question", self.context_pack)
        self.assertEqual(output.status, "ok")
        self.assertEqual(output.result.confidence, "low")
        self.assertTrue(output.trace["fallback_used"])


class TestSchemas(unittest.TestCase):
    def test_grounded_answer_schema(self):
        ga = GroundedAnswer(answer="test", used_citations=["D1-C001"], confidence="high")
        self.assertEqual(ga.confidence, "high")

    def test_output_schema(self):
        out = AnswerGeneratorOutput(status="ok", result=GroundedAnswer(answer="a", confidence="medium"))
        self.assertEqual(out.status, "ok")
        self.assertIsNotNone(out.result)


def run_all_tests():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    run_all_tests()
