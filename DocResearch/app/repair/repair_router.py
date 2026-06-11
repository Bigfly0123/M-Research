"""
Repair Router: 根据 failure_type 路由到对应修复动作和下一节点。

模块10专属设计: REPAIR_POLICY + REPAIR_NODE_MAP 双字典驱动，
输出 RepairOutput 统一 schema (status/trace/fallback_used/next_action)。
"""

import time
from typing import Optional, Literal, Dict, Any
from pydantic import BaseModel


REPAIR_POLICY: Dict[str, str] = {
    "retrieval_miss": "rewrite_query",
    "weak_evidence": "graph_expand",
    "citation_error": "evidence_recompose",
    "hallucination": "regenerate_with_evidence_only",
    "incomplete_answer": "decompose_question",
    "context_noise": "reduce_context",
}

REPAIR_NODE_MAP: Dict[str, str] = {
    "rewrite_query": "context_planner",
    "graph_expand": "hybrid_graph_retriever",
    "evidence_recompose": "evidence_composer",
    "regenerate_with_evidence_only": "answer_generator",
    "decompose_question": "context_planner",
    "reduce_context": "evidence_composer",
}


class RepairDecision(BaseModel):
    repair_action: str
    repair_reason: str
    next_node: str
    updated_state_patch: dict = {}
    failure_type: str = ""


class RepairOutput(BaseModel):
    status: Literal["ok", "warn", "fail"]
    decision: RepairDecision
    trace: dict = {}
    next_action: Optional[str] = None


def route_repair(
    failure_type: Optional[str],
    repair_count: int,
    max_repair_count: int,
    judge_result: Optional[dict] = None,
) -> RepairOutput:
    t0 = time.perf_counter()
    fallback_used = False

    # [Phase 3] 检查 judge decision: 只有 HARD_FAIL 才 repair
    judge_decision = "HARD_FAIL"
    if judge_result:
        judge_decision = judge_result.get("decision", "HARD_FAIL")

    if judge_decision == "SOFT_WARN" or judge_decision == "PASS":
        # SOFT_WARN 或 PASS → 不 repair，直接结束
        decision = RepairDecision(
            repair_action="none",
            repair_reason=f"Judge decision={judge_decision}, 不触发 repair",
            next_node="end",
            failure_type=failure_type or "none",
        )
        elapsed = int((time.perf_counter() - t0) * 1000)
        trace = _build_trace(failure_type or "none", "none", "end", repair_count, fallback_used, elapsed)
        return RepairOutput(status="ok", decision=decision, trace=trace, next_action="end")

    if failure_type is None or failure_type == "none":
        decision = RepairDecision(
            repair_action="none",
            repair_reason="无需修复",
            next_node="end",
            failure_type=failure_type or "none",
        )
        elapsed = int((time.perf_counter() - t0) * 1000)
        trace = _build_trace("none", decision.repair_action, decision.next_node, repair_count, fallback_used, elapsed)
        return RepairOutput(status="ok", decision=decision, trace=trace, next_action="end")

    if repair_count >= max_repair_count:
        fallback_used = True
        decision = RepairDecision(
            repair_action="stop",
            repair_reason=f"修复次数已达上限({max_repair_count})，保守降级",
            next_node="end",
            failure_type=failure_type,
        )
        elapsed = int((time.perf_counter() - t0) * 1000)
        trace = _build_trace(failure_type, "stop", "end", repair_count, fallback_used, elapsed)
        return RepairOutput(status="warn", decision=decision, trace=trace, next_action="end")

    repair_action = REPAIR_POLICY.get(failure_type, "regenerate_with_evidence_only")
    next_node = REPAIR_NODE_MAP.get(repair_action, "answer_generator")
    reason = f"failure_type={failure_type} → repair_action={repair_action}"
    if judge_result:
        reason += f", judge_reason={judge_result.get('reason', '')}"

    decision = RepairDecision(
        repair_action=repair_action,
        repair_reason=reason,
        next_node=next_node,
        failure_type=failure_type,
    )
    elapsed = int((time.perf_counter() - t0) * 1000)
    trace = _build_trace(failure_type, repair_action, next_node, repair_count, fallback_used, elapsed)
    return RepairOutput(status="ok", decision=decision, trace=trace, next_action=next_node)


def _build_trace(
    failure_type: str,
    repair_action: str,
    next_node: str,
    repair_count: int,
    fallback_used: bool,
    latency_ms: int,
) -> dict:
    return {
        "module": "repair_router",
        "failure_type": failure_type,
        "repair_action": repair_action,
        "next_node": next_node,
        "repair_count": repair_count,
        "fallback_used": fallback_used,
        "latency_ms": latency_ms,
    }


def run_from_state(state: dict) -> dict:
    failure_type = state.get("failure_type")
    repair_count = state.get("repair_count", 0)
    max_repair_count = state.get("max_repair_count", 3)
    judge_result = state.get("judge_result")
    output = route_repair(failure_type, repair_count, max_repair_count, judge_result)
    patch = output.decision.updated_state_patch
    state["repair_action"] = output.decision.repair_action
    state["repair_count"] = repair_count + (1 if output.decision.repair_action not in ("none", "stop") else 0)
    if patch:
        state.update(patch)
    return {"status": output.status, "decision": output.decision.model_dump(), "trace": output.trace, "next_action": output.next_action}
