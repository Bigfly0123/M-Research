"""
Trace Store 单元测试: 覆盖 schema、start/add/end trace、
summary、persistence (JSON/JSONL)。
"""

import sys
import os
import json
import shutil
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from app.trace.trace_schema import TraceEvent, TraceRecord
from app.trace.trace_store import TraceStore


class TestTraceSchema(unittest.TestCase):
    def test_trace_event_defaults(self):
        ev = TraceEvent(node="test_node")
        self.assertEqual(ev.node, "test_node")
        self.assertEqual(ev.input, "")
        self.assertEqual(ev.output, "")
        self.assertEqual(ev.latency_ms, 0)
        self.assertFalse(ev.fallback_used)
        self.assertEqual(ev.tokens, 0)

    def test_trace_event_with_fallback(self):
        ev = TraceEvent(node="retriever", fallback_used=True, latency_ms=120)
        self.assertTrue(ev.fallback_used)
        self.assertEqual(ev.latency_ms, 120)

    def test_trace_record_defaults(self):
        rec = TraceRecord(trace_id="t1", question="q1")
        self.assertEqual(rec.nodes, [])
        self.assertEqual(rec.events, [])
        self.assertEqual(rec.total_latency_ms, 0)
        self.assertEqual(rec.metrics, {})

    def test_trace_record_full_fields(self):
        rec = TraceRecord(
            trace_id="t2",
            question="q2",
            nodes=["a", "b"],
            events=[TraceEvent(node="a")],
            total_latency_ms=500,
        )
        self.assertEqual(len(rec.nodes), 2)
        self.assertEqual(len(rec.events), 1)


class TestStartAddEndTrace(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.store = TraceStore(trace_dir=self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_start_trace(self):
        rec = self.store.start_trace("测试问题", trace_id="test_001")
        self.assertEqual(rec.trace_id, "test_001")
        self.assertEqual(rec.question, "测试问题")
        self.assertNotEqual(rec.start_time, "")

    def test_add_event(self):
        self.store.start_trace("q")
        self.store.add_event("retriever", "in", "out", latency_ms=50, fallback_used=True, tokens=100)
        rec = self.store.get_trace()
        self.assertEqual(len(rec.events), 1)
        self.assertEqual(rec.events[0].node, "retriever")
        self.assertTrue(rec.events[0].fallback_used)
        self.assertIn("retriever", rec.nodes)

    def test_add_event_without_start_raises(self):
        with self.assertRaises(RuntimeError):
            self.store.add_event("x")

    def test_add_metrics(self):
        self.store.start_trace("q")
        self.store.add_metrics({"precision": 0.9, "recall": 0.8})
        rec = self.store.get_trace()
        self.assertAlmostEqual(rec.metrics["precision"], 0.9)
        self.assertAlmostEqual(rec.metrics["recall"], 0.8)

    def test_update_trace(self):
        self.store.start_trace("q")
        self.store.update_trace(answer="测试答案", judge_result={"verdict": "pass"})
        rec = self.store.get_trace()
        self.assertEqual(rec.answer, "测试答案")
        self.assertEqual(rec.judge_result["verdict"], "pass")

    def test_end_trace_writes_files(self):
        self.store.start_trace("q", trace_id="end_test")
        self.store.add_event("node_a", "i", "o", 10)
        rec = self.store.end_trace()
        self.assertGreater(rec.total_latency_ms, -1)
        json_path = os.path.join(self.tmp_dir, "end_test.json")
        self.assertTrue(os.path.exists(json_path))
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["trace_id"], "end_test")
        jsonl_path = os.path.join(self.tmp_dir, "all_traces.jsonl")
        self.assertTrue(os.path.exists(jsonl_path))


class TestGetSummary(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.store = TraceStore(trace_dir=self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_summary_counts(self):
        self.store.start_trace("q")
        self.store.add_event("a", "", "", 10, fallback_used=False)
        self.store.add_event("b", "", "", 20, fallback_used=True)
        self.store.add_event("c", "", "", 30, fallback_used=True)
        self.store.add_metrics({"f1": 0.85})
        self.store.end_trace()
        summary = self.store.get_summary()
        self.assertEqual(summary["node_count"], 3)
        self.assertEqual(summary["fallback_count"], 2)
        self.assertAlmostEqual(summary["metrics"]["f1"], 0.85)

    def test_summary_without_start_raises(self):
        with self.assertRaises(RuntimeError):
            self.store.get_summary()


class TestPersistence(unittest.TestCase):
    def setUp(self):
        self.tmp_dir = tempfile.mkdtemp()
        self.store = TraceStore(trace_dir=self.tmp_dir)

    def tearDown(self):
        shutil.rmtree(self.tmp_dir, ignore_errors=True)

    def test_json_and_jsonl_content(self):
        self.store.start_trace("持久化测试", trace_id="persist_001")
        self.store.add_event("planner", "ctx_in", "ctx_out", 5, fallback_used=True, tokens=50)
        self.store.update_trace(final_answer="最终答案")
        self.store.end_trace(final_status="pass")

        json_path = os.path.join(self.tmp_dir, "persist_001.json")
        with open(json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.assertEqual(data["question"], "持久化测试")
        self.assertEqual(data["final_answer"], "最终答案")
        self.assertEqual(len(data["events"]), 1)
        self.assertTrue(data["events"][0]["fallback_used"])

        jsonl_path = os.path.join(self.tmp_dir, "all_traces.jsonl")
        with open(jsonl_path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        self.assertEqual(len(lines), 1)
        jsonl_data = json.loads(lines[0])
        self.assertEqual(jsonl_data["trace_id"], "persist_001")


def run_all_tests():
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2)
    return runner.run(suite)


if __name__ == "__main__":
    run_all_tests()
