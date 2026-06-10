"""
AgentState: LangGraph 工作流共享状态定义。

整个 DocResearch-Agent 12 模块的数据都通过这个 TypedDict 在节点间流转。
相比 IRIS 的 9 字段状态，新版扩展为 20+ 字段，覆盖上下文规划、
图增强检索、证据组合、引用校验、修复路由和全链路追踪。
"""

from typing import TypedDict, List, Optional


class AgentState(TypedDict):
    question: str

    # --- Context Planner 输出 ---
    context_plan: dict
    query_type: str
    retrieval_plan: List[str]
    context_budget: int
    rewrite_query: str

    # --- 检索结果 ---
    retrieved_chunks: List[dict]
    retrieval_sources: List[str]

    # --- Retrieval Evaluator 输出 ---
    retrieval_eval: dict

    # --- Evidence Composer 输出 ---
    context_pack: List[dict]
    dropped_chunks: List[dict]
    total_context_tokens: int

    # --- Answer Generator 输出 ---
    answer: str
    used_citations: List[str]
    unsupported_claims: List[str]
    answer_confidence: str

    # --- Citation Guardrails 输出 ---
    guardrail_result: dict
    guardrail_pass: bool

    # --- Self-Reflection Judge 输出 ---
    judge_result: dict
    failure_type: str
    repair_action: str

    # --- Repair Router ---
    repair_count: int
    max_repair_count: int
    repair_history: List[dict]

    # --- Trace ---
    trace: List[dict]
    latency_ms: float
    context_tokens: float
    total_tokens: float
