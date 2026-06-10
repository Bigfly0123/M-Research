"""
Self-Reflection Judge: 答案质量审查器 (指南模块08)。

4 维规则评估: answer_relevance / citation_support / faithfulness / context_sufficiency。
审查失败时输出 failure_type 和 repair_action。LLM 为可选增强，核心逻辑不依赖 LLM。
"""

import json
import time
from typing import List, Literal, Optional
from pydantic import BaseModel
from app.config import config


class JudgeResult(BaseModel):
    pass_: bool = True
    answer_relevance: float = 0.0
    citation_support: float = 0.0
    faithfulness: float = 0.0
    context_sufficiency: float = 0.0
    failure_type: Literal[
        "none", "retrieval_miss", "weak_evidence",
        "citation_error", "hallucination",
        "incomplete_answer", "context_noise",
    ] = "none"
    repair_action: Optional[str] = None
    reason: str = ""


class JudgeOutput(BaseModel):
    status: Literal["ok", "warn", "fail"] = "ok"
    result: Optional[JudgeResult] = None
    trace: dict = {}
    next_action: Optional[str] = None


def rule_based_judge(
    question: str,
    answer: str,
    context_pack: List[dict],
    used_citations: List[str] = None,
    unsupported_claims: List[str] = None,
) -> JudgeResult:
    """基于引用数量和证据质量的规则版评估。"""
    used_citations = used_citations or []
    unsupported_claims = unsupported_claims or []

    q_words = set(question.lower().split())
    a_words = set(answer.lower().split())
    overlap = q_words & a_words
    answer_relevance = min(1.0, len(overlap) / max(1, len(q_words))) * 1.5

    pack_size = max(1, len(context_pack))
    citation_support = len(used_citations) / pack_size

    faithfulness = max(0.0, 1.0 - len(unsupported_claims) * 0.25)

    context_sufficiency = min(1.0, len(context_pack) / 5.0)

    answer_relevance = min(1.0, answer_relevance)
    citation_support = min(1.0, citation_support)
    faithfulness = min(1.0, faithfulness)
    context_sufficiency = min(1.0, context_sufficiency)

    failure_type = "none"
    repair_action = None
    pass_ = True

    ar_thresh = config.ANSWER_RELEVANCE_THRESHOLD
    cs_thresh = config.CITATION_SUPPORT_THRESHOLD
    f_thresh = config.FAITHFULNESS_THRESHOLD
    ctx_thresh = config.CONTEXT_SUFFICIENCY_THRESHOLD

    if answer_relevance < ar_thresh:
        pass_ = False
        failure_type = "incomplete_answer"
        repair_action = "decompose_query"
    elif citation_support < cs_thresh:
        pass_ = False
        failure_type = "citation_error"
        repair_action = "recompose_evidence"
    elif faithfulness < f_thresh:
        pass_ = False
        failure_type = "hallucination"
        repair_action = "regenerate_with_evidence_only"
    elif context_sufficiency < ctx_thresh:
        pass_ = False
        failure_type = "weak_evidence"
        repair_action = "graph_expand"

    if len(used_citations) == 0 and len(context_pack) > 0:
        pass_ = False
        failure_type = "citation_error"
        repair_action = "recompose_evidence"

    reason = f"ar={answer_relevance:.2f} cs={citation_support:.2f} f={faithfulness:.2f} ctx={context_sufficiency:.2f}"

    return JudgeResult(
        pass_=pass_,
        answer_relevance=round(answer_relevance, 3),
        citation_support=round(citation_support, 3),
        faithfulness=round(faithfulness, 3),
        context_sufficiency=round(context_sufficiency, 3),
        failure_type=failure_type,
        repair_action=repair_action,
        reason=reason,
    )


def judge_answer(
    question: str,
    answer: str,
    context_pack: List[dict],
    used_citations: List[str] = None,
    unsupported_claims: List[str] = None,
    use_llm: bool = False,
) -> JudgeOutput:
    """先 rule_based 评估，再可选 LLM 增强。"""
    start = time.time()
    fallback_used = False

    rule_result = rule_based_judge(
        question, answer, context_pack, used_citations, unsupported_claims,
    )

    result = rule_result

    if use_llm:
        try:
            from app.llm import get_llm
            llm = get_llm("smart")
            evidence = "\n".join([
                f"[{item.get('citation_id')}] {item.get('compressed_text', item.get('evidence_text', ''))[:300]}"
                for item in context_pack
            ])
            prompt = f"""You are a strict answer quality judge. Evaluate the answer on 4 dimensions (0.0-1.0).

Question: {question}
Answer: {answer}
Evidence:
{evidence}

Output ONLY valid JSON:
{{
    "answer_relevance": 0.0-1.0,
    "citation_support": 0.0-1.0,
    "faithfulness": 0.0-1.0,
    "context_sufficiency": 0.0-1.0,
    "failure_type": "none" or one of [retrieval_miss, weak_evidence, citation_error, hallucination, incomplete_answer, context_noise],
    "reason": "brief explanation",
    "repair_action": null or one of [rewrite_query, graph_expand, recompose_evidence, regenerate_with_evidence_only, decompose_query, reduce_context_noise]
}}"""
            raw = llm.invoke(prompt).content
            raw = raw.replace("```json", "").replace("```", "").strip()
            parsed = json.loads(raw)
            ft = parsed.get("failure_type", "none")
            if ft not in ("none", "retrieval_miss", "weak_evidence", "citation_error", "hallucination", "incomplete_answer", "context_noise"):
                ft = "none"
            result = JudgeResult(
                pass_=(ft == "none"),
                answer_relevance=float(parsed.get("answer_relevance", rule_result.answer_relevance)),
                citation_support=float(parsed.get("citation_support", rule_result.citation_support)),
                faithfulness=float(parsed.get("faithfulness", rule_result.faithfulness)),
                context_sufficiency=float(parsed.get("context_sufficiency", rule_result.context_sufficiency)),
                failure_type=ft,
                repair_action=parsed.get("repair_action"),
                reason=parsed.get("reason", ""),
            )
        except Exception:
            fallback_used = True
            result = rule_result

    latency = int((time.time() - start) * 1000)

    trace = {
        "module": "SelfReflectionJudge",
        "scores": {
            "answer_relevance": result.answer_relevance,
            "citation_support": result.citation_support,
            "faithfulness": result.faithfulness,
            "context_sufficiency": result.context_sufficiency,
        },
        "failure_type": result.failure_type,
        "fallback_used": fallback_used,
        "latency_ms": latency,
    }

    next_action = None
    if not result.pass_:
        next_action = "repair"

    return JudgeOutput(
        status="ok",
        result=result,
        trace=trace,
        next_action=next_action,
    )


def run_from_state(state: dict) -> dict:
    """从 AgentState 取输入，执行审判，返回 state 更新。"""
    question = state.get("question", "")
    answer = state.get("answer", "")
    context_pack = state.get("context_pack", [])
    used_citations = state.get("used_citations", [])
    unsupported_claims = state.get("unsupported_claims", [])

    output = judge_answer(question, answer, context_pack, used_citations, unsupported_claims)

    if output.result is None:
        return {
            "judge_result": {},
            "failure_type": "none",
            "repair_action": None,
            "trace": [{"node": "self_reflection_judge", "output": "fail", "latency_ms": output.trace.get("latency_ms", 0)}],
        }

    return {
        "judge_result": output.result.model_dump(),
        "failure_type": output.result.failure_type,
        "repair_action": output.result.repair_action,
        "trace": [{"node": "self_reflection_judge", "output": f"pass={output.result.pass_}, failure={output.result.failure_type}", "latency_ms": output.trace.get("latency_ms", 0)}],
    }
