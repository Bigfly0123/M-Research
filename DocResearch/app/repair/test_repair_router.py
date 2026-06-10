"""
Repair Router 单元测试: 覆盖 policy 映射、max repair、
no failure、每种 failure_type、run_from_state。
"""

import sys
import os
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.repair.repair_router import (
    route_repair,
    run_from_state,
    REPAIR_POLICY,
    REPAIR_NODE_MAP,
    RepairDecision,
    RepairOutput,
)


class TestRepairPolicyMapping(unittest.TestCase):
    def test_policy_matches_spec(self):
        expected = {
            "retrieval_miss": "rewrite_query",
            "weak_evidence": "graph_expand",
            "citation_error": "evidence_recompose",
            "hallucination": "regenerate_with_evidence_only",
            "incomplete_answer": "decompose_question",
            "context_noise": "reduce_context",
        }
        self.assertEqual(REPAIR_POLICY, expected)

    def test_node_map_matches_spec(self):
        expected = {
            "rewrite_query": "context_planner",
            "graph_expand": "hybrid_graph_retriever",
            "evidence_recompose": "evidence_composer",
            "regenerate_with_evidence_only": "answer_generator",
            "decompose_question": "context_planner",
            "reduce_context": "evidence_composer",
        }
        self.assertEqual(REPAIR_NODE_MAP, expected)


class TestNoFailure(unittest.TestCase):
    def test_failure_type_none(self):
        out = route_repair(None, 0, 3)
        self.assertEqual(out.status, "ok")
        self.assertEqual(out.decision.next_node, "end")
        self.assertEqual(out.decision.repair_action, "none")
        self.assertEqual(out.next_action, "end")

    def test_failure_type_none_str(self):
        out = route_repair("none", 0, 3)
        self.assertEqual(out.status, "ok")
        self.assertEqual(out.decision.next_node, "end")


class TestMaxRepair(unittest.TestCase):
    def test_max_repair_reached(self):
        out = route_repair("hallucination", 3, 3)
        self.assertEqual(out.status, "warn")
        self.assertEqual(out.decision.repair_action, "stop")
        self.assertEqual(out.decision.next_node, "end")
        self.assertTrue(out.trace["fallback_used"])


class TestEachFailureType(unittest.TestCase):
    def _check(self, failure_type, expected_action, expected_node):
        out = route_repair(failure_type, 0, 3)
        self.assertEqual(out.status, "ok")
        self.assertEqual(out.decision.repair_action, expected_action)
        self.assertEqual(out.decision.next_node, expected_node)
        self.assertEqual(out.next_action, expected_node)
        self.assertFalse(out.trace["fallback_used"])

    def test_retrieval_miss(self):
        self._check("retrieval_miss", "rewrite_query", "context_planner")

    def test_weak_evidence(self):
        self._check("weak_evidence", "graph_expand", "hybrid_graph_retriever")

    def test_citation_error(self):
        self._check("citation_error", "evidence_recompose", "evidence_composer")

    def test_hallucination(self):
        self._check("hallucination", "regenerate_with_evidence_only", "answer_generator")

    def test_incomplete_answer(self):
        self._check("incomplete_answer", "decompose_question", "context_planner")

    def test_context_noise(self):
        self._check("context_noise", "reduce_context", "evidence_composer")


class TestUnknownFailureType(unittest.TestCase):
    def test_unknown_defaults_to_regenerate(self):
        out = route_repair("unknown_type", 0, 3)
        self.assertEqual(out.decision.repair_action, "regenerate_with_evidence_only")
        self.assertEqual(out.decision.next_node, "answer_generator")


class TestJudgeResultInReason(unittest.TestCase):
    def test_judge_result_appended(self):
        out = route_repair("hallucination", 0, 3, judge_result={"reason": "检测到幻觉"})
        self.assertIn("judge_reason=检测到幻觉", out.decision.repair_reason)


class TestTraceFields(unittest.TestCase):
    def test_trace_contains_required_keys(self):
        out = route_repair("retrieval_miss", 1, 3)
        for key in ("module", "failure_type", "repair_action", "next_node", "repair_count", "fallback_used", "latency_ms"):
            self.assertIn(key, out.trace)
        self.assertEqual(out.trace["module"], "repair_router")
        self.assertEqual(out.trace["repair_count"], 1)


class TestRunFromState(unittest.TestCase):
    def test_run_from_state_basic(self):
        state = {"failure_type": "hallucination", "repair_count": 0, "max_repair_count": 3}
        result = run_from_state(state)
        self.assertEqual(result["status"], "ok")
        self.assertEqual(result["decision"]["repair_action"], "regenerate_with_evidence_only")
        self.assertEqual(result["next_action"], "answer_generator")
        self.assertEqual(state["repair_count"], 1)

    def test_run_from_state_no_failure(self):
        state = {"failure_type": None, "repair_count": 0, "max_repair_count": 3}
        result = run_from_state(state)
        self.assertEqual(result["next_action"], "end")
        self.assertEqual(state["repair_count"], 0)

    def test_run_from_state_max_repair(self):
        state = {"failure_type": "hallucination", "repair_count": 3, "max_repair_count": 3}
        result = run_from_state(state)
        self.assertEqual(result["status"], "warn")
        self.assertEqual(state["repair_count"], 3)


def run_all_tests():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    run_all_tests()
