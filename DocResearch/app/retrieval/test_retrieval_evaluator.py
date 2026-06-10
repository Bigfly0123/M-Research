"""
Retrieval Evaluator 单元测试: 验证 heuristic、evaluate_retrieval、schema、run_from_state。不依赖 LLM。
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

for mod in [
    "langchain_community", "langchain_huggingface", "langchain_openai",
    "langgraph.graph", "rank_bm25", "sentence_transformers",
]:
    if mod not in sys.modules:
        from unittest.mock import MagicMock
        sys.modules[mod] = MagicMock()

from app.retrieval.retrieval_evaluator import (
    RetrievalEvalResult,
    RetrievalEvalOutput,
    heuristic_evidence_score,
    evaluate_retrieval,
    run_from_state,
)


class TestHeuristicEvidenceScore(unittest.TestCase):
    def test_no_chunks_returns_irrelevant(self):
        result = heuristic_evidence_score("what is RAG", [])
        self.assertEqual(result.evidence_quality, "irrelevant")
        self.assertEqual(result.confidence, 0.0)
        self.assertEqual(result.recommended_action, "rewrite_query")

    def test_high_overlap_returns_strong(self):
        chunks = [
            {"text": "RAG retrieval augmented generation combines retrieval and generation", "final_score": 0.9, "metadata": {"doc_id": "d1"}},
            {"text": "RAG is a technique for retrieval augmented generation", "final_score": 0.85, "metadata": {"doc_id": "d2"}},
            {"text": "retrieval augmented generation RAG architecture", "final_score": 0.8, "metadata": {"doc_id": "d3"}},
        ]
        result = heuristic_evidence_score("RAG retrieval augmented generation", chunks)
        self.assertEqual(result.evidence_quality, "strong")
        self.assertEqual(result.recommended_action, "continue")
        self.assertGreater(result.confidence, 0.5)

    def test_medium_overlap_returns_weak(self):
        chunks = [
            {"text": "some unrelated content here", "final_score": 0.5, "metadata": {"doc_id": "d1"}},
            {"text": "another unrelated passage", "final_score": 0.45, "metadata": {"doc_id": "d1"}},
        ]
        result = heuristic_evidence_score("RAG retrieval augmented generation", chunks)
        self.assertIn(result.evidence_quality, ["weak", "irrelevant"])

    def test_missing_evidence_populated(self):
        chunks = [
            {"text": "unrelated", "final_score": 0.3, "metadata": {"doc_id": "d1"}},
        ]
        result = heuristic_evidence_score("RAG retrieval", chunks)
        self.assertIsInstance(result.missing_evidence, list)


class TestEvaluateRetrieval(unittest.TestCase):
    def test_strong_evidence_ok_status(self):
        chunks = [
            {"text": "RAG retrieval augmented generation combines retrieval and generation", "final_score": 0.9, "metadata": {"doc_id": "d1"}},
            {"text": "RAG is a technique for retrieval augmented generation", "final_score": 0.85, "metadata": {"doc_id": "d2"}},
            {"text": "retrieval augmented generation RAG architecture", "final_score": 0.8, "metadata": {"doc_id": "d3"}},
        ]
        output = evaluate_retrieval("RAG retrieval augmented generation", chunks, use_llm=False)
        self.assertEqual(output.status, "ok")
        self.assertIsNone(output.next_action)

    def test_no_chunks_fail_status(self):
        output = evaluate_retrieval("what is RAG", [], use_llm=False)
        self.assertEqual(output.status, "fail")
        self.assertIsNotNone(output.next_action)

    def test_trace_contains_required_keys(self):
        chunks = [{"text": "test", "final_score": 0.5, "metadata": {"doc_id": "d1"}}]
        output = evaluate_retrieval("query", chunks, use_llm=False)
        for key in ("module", "evidence_quality", "confidence", "recommended_action", "fallback_used", "latency_ms"):
            self.assertIn(key, output.trace)


class TestRunFromState(unittest.TestCase):
    def test_run_from_state_with_chunks(self):
        state = {
            "question": "RAG retrieval augmented generation",
            "retrieved_chunks": [
                {"text": "RAG retrieval augmented generation", "final_score": 0.9, "metadata": {"doc_id": "d1"}},
                {"text": "RAG architecture details", "final_score": 0.8, "metadata": {"doc_id": "d2"}},
                {"text": "retrieval augmented generation overview", "final_score": 0.75, "metadata": {"doc_id": "d3"}},
            ],
        }
        result = run_from_state(state)
        self.assertIn("retrieval_eval", result)
        self.assertIn("trace", result)

    def test_run_from_state_empty_chunks(self):
        state = {"question": "what is RAG", "retrieved_chunks": []}
        result = run_from_state(state)
        self.assertEqual(result["retrieval_eval"]["status"], "fail")


class TestSchemas(unittest.TestCase):
    def test_eval_result_schema(self):
        r = RetrievalEvalResult(evidence_quality="strong", confidence=0.9, reason="test", recommended_action="continue")
        self.assertEqual(r.evidence_quality, "strong")

    def test_eval_output_schema(self):
        o = RetrievalEvalOutput(
            status="ok",
            result=RetrievalEvalResult(evidence_quality="strong"),
            trace={"module": "test"},
        )
        self.assertEqual(o.status, "ok")
        self.assertIsNone(o.next_action)

    def test_warn_status(self):
        o = RetrievalEvalOutput(
            status="warn",
            result=RetrievalEvalResult(evidence_quality="weak", recommended_action="graph_expand"),
            trace={"module": "test"},
            next_action="graph_expand",
        )
        self.assertEqual(o.status, "warn")
        self.assertEqual(o.next_action, "graph_expand")


def run_all_tests():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    run_all_tests()
