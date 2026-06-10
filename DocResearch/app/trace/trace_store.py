"""
Trace Store: 全链路追踪存储，记录每次问答完整执行路径。

模块11专属设计: start/add/end trace 完整生命周期,
自动计算 total_latency, 写入 JSON + JSONL, 记录 fallback_used。
"""

import os
import json
import time
from typing import Optional, Dict, Any
from datetime import datetime

from app.trace.trace_schema import TraceRecord, TraceEvent


class TraceStore:
    def __init__(self, trace_dir: str = "traces"):
        self.trace_dir = trace_dir
        self._record: Optional[TraceRecord] = None
        self._start_dt: Optional[datetime] = None
        os.makedirs(trace_dir, exist_ok=True)

    def start_trace(self, question: str, trace_id: Optional[str] = None) -> TraceRecord:
        if trace_id is None:
            trace_id = f"run_{int(time.time() * 1000)}"
        self._start_dt = datetime.now()
        self._record = TraceRecord(
            trace_id=trace_id,
            question=question,
            start_time=self._start_dt.isoformat(),
        )
        return self._record

    def add_event(
        self,
        node_name: str,
        input_summary: str = "",
        output_summary: str = "",
        latency_ms: int = 0,
        fallback_used: bool = False,
        tokens: int = 0,
    ) -> None:
        if self._record is None:
            raise RuntimeError("尚未调用 start_trace")
        event = TraceEvent(
            node=node_name,
            input=input_summary,
            output=output_summary,
            latency_ms=latency_ms,
            fallback_used=fallback_used,
            tokens=tokens,
        )
        self._record.events.append(event)
        if node_name not in self._record.nodes:
            self._record.nodes.append(node_name)

    def add_metrics(self, metrics: Dict) -> None:
        if self._record is None:
            raise RuntimeError("尚未调用 start_trace")
        self._record.metrics.update(metrics)

    def update_trace(self, **kwargs: Any) -> None:
        if self._record is None:
            raise RuntimeError("尚未调用 start_trace")
        for k, v in kwargs.items():
            if hasattr(self._record, k):
                setattr(self._record, k, v)

    def end_trace(self, final_status: str = "pass") -> TraceRecord:
        if self._record is None:
            raise RuntimeError("尚未调用 start_trace")
        end_dt = datetime.now()
        self._record.end_time = end_dt.isoformat()
        if self._start_dt:
            self._record.total_latency_ms = int((end_dt - self._start_dt).total_seconds() * 1000)
        if final_status != "pass" and "final_status" not in self._record.metrics:
            self._record.metrics["final_status"] = final_status

        trace_id = self._record.trace_id
        json_path = os.path.join(self.trace_dir, f"{trace_id}.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self._record.model_dump(), f, ensure_ascii=False, indent=2)

        jsonl_path = os.path.join(self.trace_dir, "all_traces.jsonl")
        with open(jsonl_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(self._record.model_dump(), ensure_ascii=False) + "\n")

        return self._record

    def get_trace(self) -> TraceRecord:
        if self._record is None:
            raise RuntimeError("尚未调用 start_trace")
        return self._record

    def get_summary(self) -> Dict:
        if self._record is None:
            raise RuntimeError("尚未调用 start_trace")
        fallback_count = sum(1 for e in self._record.events if e.fallback_used)
        return {
            "node_count": len(self._record.nodes),
            "total_latency_ms": self._record.total_latency_ms,
            "fallback_count": fallback_count,
            "metrics": self._record.metrics,
        }
