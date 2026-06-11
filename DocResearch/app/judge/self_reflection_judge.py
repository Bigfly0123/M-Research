"""
Self-Reflection Judge: 答案质量审查器 (Phase 3 校准版)。

三层判断: PASS / SOFT_WARN / HARD_FAIL
- PASS: 答案质量好，不需要 repair
- SOFT_WARN: 答案有小问题 (citation_coverage 低等)，记录 warning 但不 repair
- HARD_FAIL: 答案有严重问题 (无答案/无引用/幻觉)，必须 repair

4 维规则评估: answer_relevance / citation_support / faithfulness / context_sufficiency。
"""

import json
import re
import time
from typing import List, Literal, Optional
from pydantic import BaseModel
from app.config import config


CITATION_PATTERN = re.compile(r'\[.+?-s\d+-c\d+\]')


class JudgeResult(BaseModel):
    pass_: bool = True
    decision: Literal["PASS", "SOFT_WARN", "HARD_FAIL"] = "PASS"
    should_repair: bool = False
    answer_relevance: float = 0.0
    citation_support: float = 0.0
    citation_precision: float = 0.0
    faithfulness: float = 0.0
    context_sufficiency: float = 0.0
    failure_type: Literal[
        "none", "retrieval_miss", "weak_evidence",
        "citation_error", "hallucination",
        "incomplete_answer", "context_noise",
    ] = "none"
    repair_action: Optional[str] = None
    warnings: List[str] = []
    reason: str = ""


class JudgeOutput(BaseModel):
    status: Literal["ok", "warn", "fail"] = "ok"
    result: Optional[JudgeResult] = None
    trace: dict = {}
    next_action: Optional[str] = None


def _compute_answer_relevance(question: str, answer: str, has_valid_citation: bool = False) -> float:
    """计算答案相关性: 词重叠 + 长度 + 引用信号。"""
    if not answer or len(answer.strip()) < 10:
        return 0.0

    q_words = set(question.lower().split())
    a_words = set(answer.lower().split())
    overlap = q_words & a_words
    word_overlap = min(1.0, len(overlap) / max(1, len(q_words))) * 1.5

    # 答案长度信号
    length_bonus = min(0.3, len(answer) / 1000.0)

    # 引用信号: 有有效引用说明答案与证据相关
    citation_bonus = 0.15 if has_valid_citation else 0.0

    score = min(1.0, word_overlap + length_bonus + citation_bonus)
    return score


def _compute_citation_metrics(
    answer: str,
    context_pack: List[dict],
    used_citations: List[str],
) -> tuple:
    """计算引用精确度和覆盖度。

    Returns: (citation_precision, citation_coverage, has_valid_citation)
    """
    if not context_pack:
        return (0.0, 0.0, False)

    ctx_ids = {item.get("citation_id", item.get("chunk_id", "")) for item in context_pack}

    # Precision: used_citations 中有多少在 context_pack 中存在
    valid_citations = [c for c in used_citations if c in ctx_ids]
    precision = len(valid_citations) / max(len(used_citations), 1) if used_citations else 0.0

    # Coverage: context_pack 中有多少被引用了 (作为参考，不作为硬判据)
    cited_ids = set(used_citations)
    coverage = len(ctx_ids & cited_ids) / max(len(ctx_ids), 1)

    has_valid = len(valid_citations) > 0

    return (round(precision, 4), round(coverage, 4), has_valid)


def rule_based_judge(
    question: str,
    answer: str,
    context_pack: List[dict],
    used_citations: List[str] = None,
    unsupported_claims: List[str] = None,
) -> JudgeResult:
    """三层规则版评估: PASS / SOFT_WARN / HARD_FAIL。"""
    used_citations = used_citations or []
    unsupported_claims = unsupported_claims or []

    # 计算 4 维指标
    citation_precision, citation_coverage, has_valid_citation = _compute_citation_metrics(
        answer, context_pack, used_citations
    )
    answer_relevance = _compute_answer_relevance(question, answer, has_valid_citation)
    faithfulness = max(0.0, 1.0 - len(unsupported_claims) * 0.25)
    context_sufficiency = min(1.0, len(context_pack) / 5.0)

    answer_relevance = min(1.0, answer_relevance)
    citation_precision = min(1.0, citation_precision)
    faithfulness = min(1.0, faithfulness)
    context_sufficiency = min(1.0, context_sufficiency)

    # --- 三层判断逻辑 ---
    warnings = []
    failure_type = "none"
    repair_action = None
    decision = "PASS"

    # 检查 HARD_FAIL 条件
    hard_failures = []

    # 1. 答案为空
    if not answer or len(answer.strip()) < 10:
        hard_failures.append("no_answer")
        failure_type = "incomplete_answer"
        repair_action = "decompose_query"

    # 2. 完全没有有效引用 (有 context 但答案中无任何正确引用)
    if context_pack and not has_valid_citation and len(used_citations) > 0:
        # 有引用但全部无效
        hard_failures.append("all_citations_invalid")
        failure_type = "citation_error"
        repair_action = "recompose_evidence"
    elif context_pack and len(used_citations) == 0:
        # 完全没有引用
        hard_failures.append("no_citations")
        failure_type = "citation_error"
        repair_action = "recompose_evidence"

    # 3. faithfulness 极低 (有大量 unsupported claims)
    if faithfulness < config.FAITHFULNESS_HARD_THRESHOLD:
        hard_failures.append("low_faithfulness")
        failure_type = "hallucination"
        repair_action = "regenerate_with_evidence_only"

    # 4. citation_precision 极低 (大量引用指向不存在的 chunk)
    if used_citations and citation_precision < 0.3:
        hard_failures.append("low_citation_precision")
        if failure_type == "none":
            failure_type = "citation_error"
            repair_action = "recompose_evidence"

    # 5. answer_relevance 极低
    if answer_relevance < config.ANSWER_RELEVANCE_HARD_THRESHOLD and answer and len(answer.strip()) >= 10:
        hard_failures.append("low_relevance")
        if failure_type == "none":
            failure_type = "incomplete_answer"
            repair_action = "decompose_query"

    # 检查 SOFT_WARN 条件 (只在没有 HARD_FAIL 时生效)
    if not hard_failures:
        soft_warnings = []

        if answer_relevance < config.ANSWER_RELEVANCE_SOFT_THRESHOLD:
            soft_warnings.append(f"low_answer_relevance ({answer_relevance:.2f})")

        if citation_coverage < config.CITATION_SUPPORT_SOFT_THRESHOLD:
            soft_warnings.append(f"low_citation_coverage ({citation_coverage:.2f})")

        if faithfulness < config.FAITHFULNESS_SOFT_THRESHOLD:
            soft_warnings.append(f"moderate_faithfulness ({faithfulness:.2f})")

        if context_sufficiency < config.CONTEXT_SUFFICIENCY_SOFT_THRESHOLD:
            soft_warnings.append(f"low_context_sufficiency ({context_sufficiency:.2f})")

        if soft_warnings:
            decision = "SOFT_WARN"
            warnings = soft_warnings

    if hard_failures:
        decision = "HARD_FAIL"

    should_repair = (decision == "HARD_FAIL")
    pass_ = (decision != "HARD_FAIL")

    reason_parts = [
        f"decision={decision}",
        f"ar={answer_relevance:.2f}",
        f"precision={citation_precision:.2f}",
        f"coverage={citation_coverage:.2f}",
        f"faith={faithfulness:.2f}",
        f"ctx={context_sufficiency:.2f}",
    ]
    if warnings:
        reason_parts.append(f"warnings=[{', '.join(warnings)}]")
    if hard_failures:
        reason_parts.append(f"hard_failures=[{', '.join(hard_failures)}]")
    reason = " | ".join(reason_parts)

    return JudgeResult(
        pass_=pass_,
        decision=decision,
        should_repair=should_repair,
        answer_relevance=round(answer_relevance, 3),
        citation_support=round(citation_coverage, 3),  # backward compat
        citation_precision=round(citation_precision, 3),
        faithfulness=round(faithfulness, 3),
        context_sufficiency=round(context_sufficiency, 3),
        failure_type=failure_type,
        repair_action=repair_action,
        warnings=warnings,
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
                decision="HARD_FAIL" if ft != "none" else "PASS",
                should_repair=(ft != "none"),
                answer_relevance=float(parsed.get("answer_relevance", rule_result.answer_relevance)),
                citation_support=float(parsed.get("citation_support", rule_result.citation_support)),
                citation_precision=rule_result.citation_precision,
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
        "decision": result.decision,
        "scores": {
            "answer_relevance": result.answer_relevance,
            "citation_support": result.citation_support,
            "citation_precision": result.citation_precision,
            "faithfulness": result.faithfulness,
            "context_sufficiency": result.context_sufficiency,
        },
        "warnings": result.warnings,
        "failure_type": result.failure_type,
        "should_repair": result.should_repair,
        "fallback_used": fallback_used,
        "latency_ms": latency,
    }

    next_action = None
    if result.should_repair:
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
        "failure_type": output.result.failure_type if output.result.should_repair else "none",
        "repair_action": output.result.repair_action if output.result.should_repair else "",
        "trace": [{"node": "self_reflection_judge", "output": f"decision={output.result.decision}, failure={output.result.failure_type}", "latency_ms": output.trace.get("latency_ms", 0)}],
    }
