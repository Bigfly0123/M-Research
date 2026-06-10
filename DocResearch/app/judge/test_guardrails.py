"""
Citation Guardrails 单元测试: mock 重依赖，验证三层检查、action 决策、schema、run_from_state。"""

import sys
import os
import unittest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

for mod in [
    "langchain_community", "langchain_huggingface", "langchain_openai",
    "langgraph.graph", "rank_bm25", "sentence_transformers",
]:
    if mod in sys.modules:
        del sys.modules[mod]
    sys.modules[mod] = MagicMock()

from app.judge.guardrails import (
    CitationGuardResult,
    GuardrailOutput,
    check_existence,
    check_alignment,
    check_support,
    check_citations,
    run_from_state,
)


class TestCheckExistence(unittest.TestCase):
    def test_find_citations(self):
        found = check_existence("a [D1-C001] b [D2-C003] c")
        self.assertEqual(found, ["[D1-C001]", "[D2-C003]"])

    def test_no_citations(self):
        found = check_existence("no citations here")
        self.assertEqual(found, [])

    def test_malformed_citation(self):
        found = check_existence("a [D1-001] b [D1-C001]")
        self.assertEqual(found, ["[D1-C001]"])


class TestCheckAlignment(unittest.TestCase):
    def test_all_aligned(self):
        invalid = check_alignment(["[D1-C001]", "[D2-C003]"], {"D1-C001", "D2-C003"})
        self.assertEqual(invalid, [])

    def test_has_misaligned(self):
        invalid = check_alignment(["[D1-C001]", "[D9-C999]"], {"D1-C001"})
        self.assertEqual(invalid, ["[D9-C999]"])


class TestCheckSupport(unittest.TestCase):
    def test_long_sentence_with_citation(self):
        result = check_support("这是一条超过二十个字符的长句子并且有引用 [D1-C001]")
        self.assertEqual(result, [])

    def test_long_sentence_without_citation(self):
        result = check_support("这是一条超过二十个字符的长句子但是没有任何引用支撑")
        self.assertEqual(len(result), 1)

    def test_short_sentence_no_check(self):
        result = check_support("短句子")
        self.assertEqual(result, [])


class TestCheckCitations(unittest.TestCase):
    def setUp(self):
        self.context_pack = [
            {"citation_id": "D1-C001"},
            {"citation_id": "D2-C003"},
        ]

    def test_all_pass(self):
        output = check_citations("答案 [D1-C001] 和 [D2-C003] 都有引用", self.context_pack)
        self.assertTrue(output.result.pass_)
        self.assertEqual(output.result.action, "pass")

    def test_no_citations_block(self):
        output = check_citations("完全没有引用的答案内容", self.context_pack)
        self.assertFalse(output.result.pass_)
        self.assertEqual(output.result.action, "block")

    def test_invalid_citations_repair(self):
        output = check_citations("有效 [D1-C001] 和无效引用 [D9-C999]", self.context_pack)
        self.assertFalse(output.result.pass_)
        self.assertEqual(output.result.action, "repair")
        self.assertIn("[D9-C999]", output.result.invalid_citations)

    def test_all_invalid_block(self):
        output = check_citations("[D9-C998] [D9-C999]", self.context_pack)
        self.assertFalse(output.result.pass_)
        self.assertEqual(output.result.action, "block")

    def test_empty_answer(self):
        output = check_citations("", self.context_pack)
        self.assertEqual(output.status, "fail")
        self.assertEqual(output.result.action, "block")

    def test_uncited_claim_repair(self):
        output = check_citations("这是一条超过二十个字符的声明但没有引用支撑. 有效 [D1-C001]", self.context_pack)
        self.assertFalse(output.result.pass_)
        self.assertEqual(output.result.action, "repair")


class TestRunFromState(unittest.TestCase):
    def test_pass(self):
        state = {
            "answer": "答案 [D1-C001] 有引用",
            "context_pack": [{"citation_id": "D1-C001"}],
        }
        result = run_from_state(state)
        self.assertTrue(result["guardrail_pass"])

    def test_block(self):
        state = {
            "answer": "没有引用的答案",
            "context_pack": [{"citation_id": "D1-C001"}],
        }
        result = run_from_state(state)
        self.assertFalse(result["guardrail_pass"])


class TestSchemas(unittest.TestCase):
    def test_guard_result_schema(self):
        gr = CitationGuardResult(pass_=True, action="pass")
        self.assertTrue(gr.pass_)
        self.assertEqual(gr.action, "pass")

    def test_output_schema(self):
        go = GuardrailOutput(status="ok", result=CitationGuardResult(pass_=True))
        self.assertEqual(go.status, "ok")


def run_all_tests():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    run_all_tests()
