"""
Trace Schema: 全链路追踪数据结构定义。

模块11专属设计: TraceEvent 含 fallback_used 字段;
TraceRecord 覆盖完整 pipeline 各阶段输出。
"""

from typing import List, Dict, Optional
from pydantic import BaseModel


class TraceEvent(BaseModel):
    node: str
    input: str = ""
    output: str = ""
    latency_ms: int = 0
    fallback_used: bool = False
    tokens: int = 0


class TraceRecord(BaseModel):
    trace_id: str
    question: str
    nodes: List[str] = []
    context_plan: Dict = {}
    retrieval: Dict = {}
    evidence_pack: List[Dict] = []
    answer: str = ""
    judge_result: Dict = {}
    repair_history: List[Dict] = []
    final_answer: str = ""
    metrics: Dict = {}
    events: List[TraceEvent] = []
    start_time: str = ""
    end_time: str = ""
    total_latency_ms: int = 0
