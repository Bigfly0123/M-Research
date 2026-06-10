"""
Eval Run Tool: 封装评估运行，读取 trace 目录并计算指标。
"""
import os
import json
from typing import List
from app.tools.registry import BaseTool, ToolSpec
from app.config import config


class EvalRunTool(BaseTool):
    spec = ToolSpec(
        name="eval_run",
        description="Run evaluation on trace files, computing quality metrics.",
        input_schema={"trace_dir": "str", "metrics": "list[str]"},
        output_schema={"eval_results": "dict", "status": "str"},
    )

    def run(self, trace_dir: str, metrics: List[str], **kwargs) -> dict:
        try:
            results = {}
            if not os.path.isdir(trace_dir):
                return {"eval_results": {}, "status": "fail"}

            trace_files = [f for f in os.listdir(trace_dir) if f.endswith(".json")]
            total = len(trace_files)
            results["trace_count"] = total

            for metric in metrics:
                if metric == "avg_latency":
                    latencies = []
                    for fname in trace_files:
                        try:
                            with open(os.path.join(trace_dir, fname), "r", encoding="utf-8") as f:
                                data = json.load(f)
                            if "latency_ms" in data:
                                latencies.append(data["latency_ms"])
                        except Exception:
                            pass
                    results["avg_latency"] = sum(latencies) / len(latencies) if latencies else 0.0
                elif metric == "pass_rate":
                    passed = 0
                    for fname in trace_files:
                        try:
                            with open(os.path.join(trace_dir, fname), "r", encoding="utf-8") as f:
                                data = json.load(f)
                            if data.get("status") in ("ok", "pass"):
                                passed += 1
                        except Exception:
                            pass
                    results["pass_rate"] = passed / total if total > 0 else 0.0

            return {"eval_results": results, "status": "ok"}
        except Exception as e:
            return {"eval_results": {"error": str(e)}, "status": "fail"}
