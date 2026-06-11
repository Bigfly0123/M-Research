"""
LangGraph 工作流编排: DocResearch-Agent 2026 完整图结构。

工作流: START → ContextPlanner → HybridGraphRetriever → RetrievalEvaluator
  → EvidenceComposer → GroundedAnswerGenerator → CitationGuardrails
  → SelfReflectionJudge → RepairRouter(条件边)
"""

import time
from langgraph.graph import StateGraph, END
from app.state import AgentState
from app.config import config
from app.context.context_planner import plan_context
from app.retrieval.hybrid_retriever import HybridGraphRetriever
from app.retrieval.retrieval_evaluator import evaluate_retrieval
from app.evidence.evidence_composer import compose_context_pack
from app.generation.answer_generator import generate_answer
from app.judge.self_reflection_judge import judge_answer
from app.judge.guardrails import check_citations
from app.repair.repair_router import route_repair
from app.trace.trace_store import TraceStore

retriever = HybridGraphRetriever()
trace_store = TraceStore()

GUARDRAIL_NODE_MAP = {
    "repair": "evidence_composer",
    "block": "answer_generator",
}


def context_planner(state: AgentState) -> dict:
    """节点1: 上下文规划。"""
    start = time.time()
    question = state["question"]
    output = plan_context(question, use_llm=True)
    plan = output.plan
    latency = int((time.time() - start) * 1000)
    return {
        "context_plan": plan.model_dump() if plan else {},
        "query_type": plan.query_type if plan else "concept",
        "retrieval_plan": list(plan.retrieval_plan) if plan else ["dense", "bm25", "graph_expand"],
        "context_budget": plan.context_budget if plan else config.DEFAULT_CONTEXT_BUDGET,
        "rewrite_query": plan.rewritten_query if plan else question,
        "trace": [{"node": "context_planner", "output": f"type={plan.query_type}, plan={plan.retrieval_plan}", "latency_ms": latency}] if plan else [],
    }


def hybrid_graph_retriever(state: AgentState) -> dict:
    """节点2: 多路混合检索。"""
    query = state.get("rewrite_query", state["question"])
    retrieval_plan = state.get("retrieval_plan", ["dense", "bm25", "graph_expand"])
    repair_action = state.get("repair_action", "")
    top_k = config.FINAL_TOP_K + 5 if repair_action == "graph_expand" else config.FINAL_TOP_K

    result = retriever.retrieve(query, retrieval_plan=retrieval_plan, top_k=top_k)

    chunks_dicts = [c.model_dump() for c in result.chunks]
    sources = list(result.source_stats.keys()) if result.source_stats else []

    return {
        "retrieved_chunks": chunks_dicts,
        "retrieval_sources": sources,
        "trace": [{"node": "hybrid_graph_retriever", "output": f"status={result.status}, retrieved {result.total_retrieved} chunks, stats={result.source_stats}", "latency_ms": result.trace.get("latency_ms", 0)}],
    }


def retrieval_evaluator(state: AgentState) -> dict:
    """节点3: 检索质量评估。"""
    start = time.time()
    question = state["question"]
    chunks = state.get("retrieved_chunks", [])
    output = evaluate_retrieval(question, chunks, use_llm=True)
    latency = int((time.time() - start) * 1000)
    return {
        "retrieval_eval": output.model_dump(),
        "trace": [{"node": "retrieval_evaluator", "output": f"quality={output.result.evidence_quality}, action={output.result.recommended_action}", "latency_ms": latency}],
    }


def evidence_composer(state: AgentState) -> dict:
    """节点4: 证据组合。"""
    start = time.time()
    chunks = state.get("retrieved_chunks", [])
    question = state["question"]
    budget = state.get("context_budget", config.DEFAULT_CONTEXT_BUDGET)
    pack = compose_context_pack(chunks, question, context_budget=budget)
    latency = int((time.time() - start) * 1000)
    return {
        "context_pack": [item.model_dump() for item in pack.context_pack],
        "dropped_chunks": pack.dropped_chunks,
        "total_context_tokens": pack.total_context_tokens,
        "trace": [{"node": "evidence_composer", "output": f"pack={len(pack.context_pack)} items, tokens={pack.total_context_tokens}, dropped={len(pack.dropped_chunks)}", "latency_ms": latency}],
    }


def grounded_answer_generator(state: AgentState) -> dict:
    """节点5: 带引用答案生成。"""
    start = time.time()
    question = state["question"]
    context_pack = state.get("context_pack", [])
    query_type = state.get("query_type", "concept")
    output = generate_answer(question, context_pack, query_type=query_type)
    latency = int((time.time() - start) * 1000)
    if output.result is None:
        return {
            "answer": "",
            "used_citations": [],
            "unsupported_claims": [],
            "answer_confidence": "low",
            "trace": [{"node": "answer_generator", "output": "fail", "latency_ms": latency}],
        }
    return {
        "answer": output.result.answer,
        "used_citations": output.result.used_citations,
        "unsupported_claims": output.result.unsupported_claims,
        "answer_confidence": output.result.confidence,
        "trace": [{"node": "answer_generator", "output": f"confidence={output.result.confidence}, citations={len(output.result.used_citations)}", "latency_ms": latency}],
    }


def citation_guardrails(state: AgentState) -> dict:
    """节点6: 引用护栏。"""
    start = time.time()
    answer = state.get("answer", "")
    context_pack = state.get("context_pack", [])
    output = check_citations(answer, context_pack)
    latency = int((time.time() - start) * 1000)
    if output.result is None:
        return {
            "guardrail_result": {},
            "guardrail_pass": False,
            "trace": [{"node": "citation_guardrails", "output": "fail", "latency_ms": latency}],
        }
    return {
        "guardrail_result": output.result.model_dump(),
        "guardrail_pass": output.result.pass_,
        "trace": [{"node": "citation_guardrails", "output": f"pass={output.result.pass_}, invalid={output.result.invalid_citations}", "latency_ms": latency}],
    }


def self_reflection_judge(state: AgentState) -> dict:
    """节点7: 自省审查 (Phase 3 校准版)。"""
    start = time.time()
    question = state["question"]
    answer = state.get("answer", "")
    context_pack = state.get("context_pack", [])
    used_citations = state.get("used_citations", [])
    unsupported_claims = state.get("unsupported_claims", [])
    output = judge_answer(
        question, answer, context_pack,
        used_citations=used_citations,
        unsupported_claims=unsupported_claims,
    )
    latency = int((time.time() - start) * 1000)

    if output.result is None:
        return {
            "judge_result": {},
            "failure_type": "none",
            "repair_action": "",
            "trace": [{"node": "self_reflection_judge", "output": "fail", "latency_ms": latency}],
        }

    # [Phase 3] 只在 HARD_FAIL 时设置 failure_type，让 repair_router 处理
    repair_count = state.get("repair_count", 0)
    # 用 judge decision 更新 guardrail_pass (反映最终质量判断)
    judge_pass = not output.result.should_repair
    if output.result.should_repair:
        # HARD_FAIL → 递增 repair_count 并设置 failure_type
        repair_count += 1
        return {
            "judge_result": output.result.model_dump(),
            "failure_type": output.result.failure_type,
            "repair_action": output.result.repair_action or "",
            "repair_count": repair_count,
            "guardrail_pass": False,
            "trace": [{"node": "self_reflection_judge", "output": f"decision={output.result.decision}, failure={output.result.failure_type}", "latency_ms": latency}],
        }
    else:
        # PASS 或 SOFT_WARN → 不触发 repair
        return {
            "judge_result": output.result.model_dump(),
            "failure_type": "none",
            "repair_action": "",
            "repair_count": repair_count,
            "guardrail_pass": True,
            "trace": [{"node": "self_reflection_judge", "output": f"decision={output.result.decision}, warnings={output.result.warnings}", "latency_ms": latency}],
        }


def repair_router(state: AgentState) -> str:
    """条件边: 根据 judge decision 和 failure_type 决定下一节点 (Phase 3 校准版)。"""
    failure_type = state.get("failure_type", "")
    repair_count = state.get("repair_count", 0)
    max_repair = state.get("max_repair_count", config.MAX_REPAIR_COUNT)
    judge_result = state.get("judge_result", {})

    # 无 failure 或 PASS/SOFT_WARN → 结束
    if not failure_type or failure_type == "none" or failure_type == "pass":
        return END

    # 检查 judge decision
    judge_decision = judge_result.get("decision", "HARD_FAIL")
    if judge_decision in ("PASS", "SOFT_WARN"):
        return END

    # HARD_FAIL 且未超过最大修复次数 → repair
    if repair_count >= max_repair:
        return END

    # 检查 guardrail 是否有 block
    if not state.get("guardrail_pass", True):
        guardrail_result = state.get("guardrail_result", {})
        guardrail_action = guardrail_result.get("action", "")
        guardrail_decision = guardrail_result.get("decision", "")
        # 只有 HARD_FAIL 类型的 guardrail 才触发 repair
        if guardrail_decision == "HARD_FAIL" and guardrail_action and guardrail_action != "pass":
            return GUARDRAIL_NODE_MAP.get(guardrail_action, "evidence_composer")

    decision = route_repair(failure_type, repair_count, max_repair, judge_result)
    return decision.next_node if decision.next_node != "end" else END


def create_graph():
    """构建 LangGraph 工作流。"""
    workflow = StateGraph(AgentState)

    workflow.add_node("context_planner", context_planner)
    workflow.add_node("hybrid_graph_retriever", hybrid_graph_retriever)
    workflow.add_node("retrieval_evaluator", retrieval_evaluator)
    workflow.add_node("evidence_composer", evidence_composer)
    workflow.add_node("answer_generator", grounded_answer_generator)
    workflow.add_node("citation_guardrails", citation_guardrails)
    workflow.add_node("self_reflection_judge", self_reflection_judge)

    workflow.set_entry_point("context_planner")
    workflow.add_edge("context_planner", "hybrid_graph_retriever")
    workflow.add_edge("hybrid_graph_retriever", "retrieval_evaluator")
    workflow.add_edge("retrieval_evaluator", "evidence_composer")
    workflow.add_edge("evidence_composer", "answer_generator")
    workflow.add_edge("answer_generator", "citation_guardrails")
    workflow.add_edge("citation_guardrails", "self_reflection_judge")

    workflow.add_conditional_edges(
        "self_reflection_judge",
        repair_router,
        {
            "context_planner": "context_planner",
            "hybrid_graph_retriever": "hybrid_graph_retriever",
            "evidence_composer": "evidence_composer",
            "answer_generator": "answer_generator",
            END: END,
        },
    )

    return workflow.compile()
