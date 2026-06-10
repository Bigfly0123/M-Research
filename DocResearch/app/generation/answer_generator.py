"""
Grounded Answer Generator: 带引用的答案生成器 (指南模块07)。

基于 context_pack 生成答案，规则自检引用合法性，LLM 失败有 fallback。
输出遵循 Module 设计模式: status / trace / fallback_used / next_action。
"""

import json
import re
import time
from typing import List, Literal, Optional
from pydantic import BaseModel
from app.config import config


class GroundedAnswer(BaseModel):
    answer: str
    used_citations: List[str] = []
    unsupported_claims: List[str] = []
    confidence: Literal["high", "medium", "low"] = "medium"


class AnswerGeneratorOutput(BaseModel):
    status: Literal["ok", "warn", "fail"] = "ok"
    result: Optional[GroundedAnswer] = None
    trace: dict = {}
    next_action: Optional[str] = None


def rule_check_citations(answer: str, valid_ids: set) -> dict:
    """规则自检: 答案中 citation_id 是否在 context_pack 中。"""
    found = re.findall(r'\[D\d+-C\d+\]', answer)
    found_bare = [cid.strip("[]") for cid in found]
    invalid = [cid for cid, bare in zip(found, found_bare) if bare not in valid_ids]
    return {
        "found_citations": found,
        "invalid_citations": invalid,
        "valid_count": len(found) - len(invalid),
        "all_valid": len(invalid) == 0,
    }


def generate_answer(
    question: str,
    context_pack: list,
    query_type: str = "concept",
) -> AnswerGeneratorOutput:
    """基于 context_pack 生成答案，规则自检引用合法性。"""
    start = time.time()
    fallback_used = False

    if not context_pack:
        return AnswerGeneratorOutput(
            status="fail",
            result=GroundedAnswer(answer="", confidence="low"),
            trace={
                "module": "AnswerGenerator",
                "citations_used": 0,
                "confidence": "low",
                "fallback_used": False,
                "latency_ms": int((time.time() - start) * 1000),
            },
            next_action="check_retrieval",
        )

    valid_ids = {item.get("citation_id", "") for item in context_pack}

    evidence_text = "\n\n".join([
        f"[{item['citation_id']}] (source: {item.get('source', '')}, section: {item.get('section', '')}, role: {item.get('supporting_role', '')})\n{item.get('compressed_text', item.get('evidence_text', ''))}"
        for item in context_pack
    ])

    prompt = f"""You are a technical documentation Q&A assistant. Answer grounded in evidence only.

Question: {question}
Question type: {query_type}

Evidence pack:
{evidence_text}

Rules:
1. Use ONLY the evidence above. Do NOT use any outside knowledge.
2. Every key claim MUST include its citation_id in brackets like [D1-C012].
3. If evidence is insufficient to answer fully, clearly state what cannot be determined.
4. For multi-hop questions, explain the evidence chain step by step.
5. For comparison questions, organize by source.

Output ONLY valid JSON:
{{
    "answer": "your answer with citations",
    "used_citations": ["D1-C012"],
    "unsupported_claims": [],
    "confidence": "high/medium/low"
}}"""

    try:
        from app.llm import get_llm
        llm = get_llm("fast")
        raw = llm.invoke(prompt).content
        raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)

        confidence = parsed.get("confidence", "medium")
        if confidence not in ("high", "medium", "low"):
            confidence = "medium"

        grounded = GroundedAnswer(
            answer=parsed.get("answer", ""),
            used_citations=parsed.get("used_citations", []),
            unsupported_claims=parsed.get("unsupported_claims", []),
            confidence=confidence,
        )
    except Exception:
        fallback_used = True
        grounded = GroundedAnswer(
            answer=_fallback_answer(question, context_pack),
            used_citations=list(valid_ids)[:3],
            unsupported_claims=[],
            confidence="low",
        )

    check = rule_check_citations(grounded.answer, valid_ids)
    if not check["all_valid"]:
        grounded.used_citations = [cid for cid in grounded.used_citations if cid in valid_ids]
        if grounded.confidence != "low":
            grounded.confidence = "medium"

    latency = int((time.time() - start) * 1000)

    trace = {
        "module": "AnswerGenerator",
        "citations_used": len(grounded.used_citations),
        "confidence": grounded.confidence,
        "fallback_used": fallback_used,
        "latency_ms": latency,
    }

    return AnswerGeneratorOutput(
        status="ok",
        result=grounded,
        trace=trace,
        next_action=None,
    )


def _fallback_answer(question: str, context_pack: list) -> str:
    """LLM 失败时的规则版 fallback 答案。"""
    if not context_pack:
        return "无法获取足够证据来回答该问题。"
    parts = []
    for item in context_pack[:5]:
        cid = item.get("citation_id", "")
        text = item.get("compressed_text", item.get("evidence_text", ""))[:200]
        parts.append(f"[{cid}] {text}")
    return "基于现有证据的简要回答:\n" + "\n".join(parts)


def run_from_state(state: dict) -> dict:
    """从 AgentState 取输入，执行答案生成，返回 state 更新。"""
    question = state.get("question", "")
    context_pack = state.get("context_pack", [])
    query_type = state.get("query_type", "concept")

    output = generate_answer(question, context_pack, query_type=query_type)

    if output.result is None:
        return {
            "answer": "",
            "used_citations": [],
            "unsupported_claims": [],
            "answer_confidence": "low",
            "trace": [{"node": "answer_generator", "output": "fail", "latency_ms": output.trace.get("latency_ms", 0)}],
        }

    return {
        "answer": output.result.answer,
        "used_citations": output.result.used_citations,
        "unsupported_claims": output.result.unsupported_claims,
        "answer_confidence": output.result.confidence,
        "trace": [{"node": "answer_generator", "output": f"citations={len(output.result.used_citations)}, confidence={output.result.confidence}", "latency_ms": output.trace.get("latency_ms", 0)}],
    }
