"""
Context Planner: 上下文决策入口层。

判断本轮问题需要什么上下文、调用哪些检索工具、上下文预算多少、
风险级别和 Judge 应重点检查什么。

遵循指南: Rule-based Planner -> LLM Refiner -> Pydantic Validation -> Fallback。
"""

import time
from typing import List, Literal, Optional
from pydantic import BaseModel, Field
from app.config import config


class ContextPlan(BaseModel):
    """上下文规划输出 schema (指南模块01专属设计)。"""
    query_type: Literal["fact", "concept", "multi_hop", "comparison", "code_understanding", "troubleshooting"]
    intent: str = ""
    rewritten_query: str = ""
    retrieval_plan: List[Literal["dense", "bm25", "graph_expand"]] = Field(default=["dense", "bm25", "graph_expand"])
    top_k_dense: int = 12
    top_k_bm25: int = 12
    graph_hops: int = 1
    use_reranker: bool = True
    context_budget: int = 3500
    need_code_blocks: bool = False
    need_tables: bool = False
    metadata_filters: dict = Field(default_factory=dict)
    risk_level: Literal["low", "medium", "citation_sensitive"] = "citation_sensitive"
    expected_evidence: List[str] = Field(default_factory=list)
    judge_focus: List[str] = Field(default_factory=list)


class ContextPlanOutput(BaseModel):
    """Module 模式输出: status + data + trace + next_action。"""
    status: Literal["ok", "warn", "fail"] = "ok"
    plan: ContextPlan = None
    trace: dict = Field(default_factory=dict)
    next_action: Optional[str] = None


def rule_based_plan(question: str) -> ContextPlan:
    """规则版规划: 根据问题关键词匹配 query_type、retrieval_plan、context_budget。"""
    q = question.lower()

    if any(x in q for x in ["区别", "对比", "compare", "difference", "vs", "versus"]):
        query_type, plan, budget = "comparison", ["dense", "bm25", "graph_expand"], 4500
    elif any(x in q for x in ["为什么", "如何", "触发", "关系", "why", "cause", "how"]):
        query_type, plan, budget = "multi_hop", ["dense", "bm25", "graph_expand"], 3500
    elif any(x in q for x in ["troubleshoot", "debug", "修复", "fix", "报错"]):
        query_type, plan, budget = "troubleshooting", ["dense", "bm25", "graph_expand"], 3500
    elif any(x in q for x in ["函数", "class", "参数", "代码", "error", "function", "def "]):
        query_type, plan, budget = "code_understanding", ["bm25", "dense"], 3500
    elif any(x in q for x in ["什么是", "定义", "what is", "define"]):
        query_type, plan, budget = "fact", ["dense", "bm25"], 2500
    else:
        query_type, plan, budget = "concept", ["dense", "bm25", "graph_expand"], 3500

    need_code = any(x in q for x in ["代码", "code", "函数", "function", "class", "def "])
    need_tables = any(x in q for x in ["表格", "table", "参数表", "对比表"])
    judge_focus = ["citation_support", "faithfulness"]
    if query_type == "comparison":
        judge_focus.append("context_sufficiency")
    if query_type == "multi_hop":
        judge_focus.append("answer_relevance")

    return ContextPlan(
        query_type=query_type,
        intent=f"rule_based_{query_type}",
        rewritten_query=question,
        retrieval_plan=plan,
        context_budget=budget,
        need_code_blocks=need_code,
        need_tables=need_tables,
        risk_level="citation_sensitive",
        judge_focus=judge_focus,
    )


def llm_refine_plan(question: str, base_plan: ContextPlan) -> ContextPlan:
    """LLM 细化规划: 补充 intent、expected_evidence，可能调整 retrieval_plan。"""
    from app.llm import get_llm
    llm = get_llm("fast")
    prompt = f"""You are a context planner for a technical documentation Q&A system.

Question: {question}
Current plan: {base_plan.model_dump_json()}

Refine the plan. Output ONLY valid JSON with these fields:
- query_type: one of [fact, concept, multi_hop, comparison, code_understanding, troubleshooting]
- intent: brief description of what the question asks
- retrieval_plan: list of [dense, bm25, graph_expand]
- context_budget: integer, max context tokens
- rewritten_query: improved query for retrieval
- expected_evidence: list of what kind of evidence is needed
- judge_focus: list of dimensions judge should focus on"""

    try:
        raw = llm.invoke(prompt).content
        raw = raw.replace("```json", "").replace("```", "").strip()
        import json
        refined = json.loads(raw)
        return ContextPlan(
            query_type=refined.get("query_type", base_plan.query_type),
            intent=refined.get("intent", base_plan.intent),
            retrieval_plan=refined.get("retrieval_plan", base_plan.retrieval_plan),
            context_budget=refined.get("context_budget", base_plan.context_budget),
            rewritten_query=refined.get("rewritten_query", question),
            expected_evidence=refined.get("expected_evidence", []),
            judge_focus=refined.get("judge_focus", base_plan.judge_focus),
        )
    except Exception:
        return base_plan


def plan_context(question: str, use_llm: bool = True) -> ContextPlanOutput:
    """统一入口: Rule-based -> LLM Refiner -> Pydantic Validation -> Fallback。"""
    start = time.time()
    fallback_used = False

    if not question or not question.strip():
        return ContextPlanOutput(
            status="fail",
            trace={"module": "ContextPlanner", "error": "empty_question", "fallback_used": False, "latency_ms": 0},
            next_action="check_input",
        )

    base_plan = rule_based_plan(question)

    if use_llm:
        try:
            refined = llm_refine_plan(question, base_plan)
        except Exception:
            refined = base_plan
            fallback_used = True
    else:
        refined = base_plan

    latency = int((time.time() - start) * 1000)
    trace = {
        "module": "ContextPlanner",
        "query_type": refined.query_type,
        "retrieval_plan": refined.retrieval_plan,
        "context_budget": refined.context_budget,
        "risk_level": refined.risk_level,
        "fallback_used": fallback_used,
        "latency_ms": latency,
    }

    return ContextPlanOutput(
        status="ok",
        plan=refined,
        trace=trace,
    )


def run_from_state(state: dict) -> dict:
    """从 AgentState 取输入，执行规划，返回 state 更新。"""
    question = state.get("question", "")
    use_llm = state.get("use_llm", True)
    result = plan_context(question, use_llm=use_llm)
    plan = result.plan
    return {
        "context_plan": plan.model_dump() if plan else {},
        "query_type": plan.query_type if plan else "concept",
        "retrieval_plan": list(plan.retrieval_plan) if plan else ["dense", "bm25", "graph_expand"],
        "context_budget": plan.context_budget if plan else config.DEFAULT_CONTEXT_BUDGET,
        "rewrite_query": plan.rewritten_query if plan else question,
        "trace": [{"node": "context_planner", "output": f"type={plan.query_type}, plan={plan.retrieval_plan}", "latency_ms": result.trace.get("latency_ms", 0)}] if plan else [],
    }
