"""
Retrieval Evaluator: 检索质量评估器 (模块05)。

Corrective RAG 思想：检索可能错，先评估，再决定继续/改写/扩展。
输出遵循 Module 设计模式: status / trace / next_action。
"""

import json
import time
from typing import List, Literal, Optional
from pydantic import BaseModel
from app.config import config


class RetrievalEvalResult(BaseModel):
    evidence_quality: Literal["strong", "weak", "irrelevant", "conflicting"] = "irrelevant"
    confidence: float = 0.0
    reason: str = ""
    missing_evidence: List[str] = []
    recommended_action: Literal["continue", "rewrite_query", "graph_expand", "fallback_bm25"] = "rewrite_query"


class RetrievalEvalOutput(BaseModel):
    status: Literal["ok", "warn", "fail"] = "ok"
    result: RetrievalEvalResult
    trace: dict = {}
    next_action: Optional[str] = None


def heuristic_evidence_score(question: str, chunks: List[dict]) -> RetrievalEvalResult:
    """规则版评估。"""
    if not chunks:
        return RetrievalEvalResult(
            evidence_quality="irrelevant",
            confidence=0.0,
            reason="No chunks retrieved",
            missing_evidence=["no chunks returned from retrieval"],
            recommended_action="rewrite_query",
        )

    q_terms = set(question.lower().split())
    top_score = chunks[0].get("final_score", 0)

    overlap_counts = []
    for c in chunks[:5]:
        c_terms = set(c.get("text", "").lower().split())
        overlap = len(q_terms & c_terms) / max(len(q_terms), 1)
        overlap_counts.append(overlap)
    avg_overlap = sum(overlap_counts) / len(overlap_counts) if overlap_counts else 0

    sources = set(c.get("metadata", {}).get("doc_id", "") for c in chunks[:10])
    confidence = (top_score * 0.4 + avg_overlap * 0.4 + min(len(sources) / 3, 1) * 0.2)

    missing = []
    if avg_overlap < 0.2:
        missing.append("low query-chunk term overlap")
    if len(sources) < 2:
        missing.append("insufficient source diversity")

    if confidence >= 0.6:
        quality = "strong"
        action = "continue"
    elif confidence >= 0.35:
        quality = "weak"
        action = "graph_expand"
    else:
        quality = "irrelevant"
        action = "rewrite_query"

    return RetrievalEvalResult(
        evidence_quality=quality,
        confidence=round(confidence, 3),
        reason=f"top_score={top_score:.3f}, overlap={avg_overlap:.3f}, sources={len(sources)}",
        missing_evidence=missing,
        recommended_action=action,
    )


def llm_evaluate(question: str, chunks: List[dict]) -> RetrievalEvalResult:
    """LLM 评估。"""
    from app.llm import get_llm
    llm = get_llm("smart")
    context = "\n".join([f"[{c.get('chunk_id')}] {c.get('text', '')[:200]}" for c in chunks[:10]])

    prompt = f"""Evaluate the retrieval quality for this question.

Question: {question}

Retrieved chunks:
{context}

Output ONLY valid JSON:
{{
    "evidence_quality": "strong/weak/irrelevant/conflicting",
    "confidence": 0.0-1.0,
    "reason": "brief explanation",
    "missing_evidence": ["what is missing"],
    "recommended_action": "continue/rewrite_query/graph_expand/fallback_bm25"
}}"""

    try:
        raw = llm.invoke(prompt).content
        raw = raw.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(raw)
        return RetrievalEvalResult(
            evidence_quality=parsed.get("evidence_quality", "weak"),
            confidence=float(parsed.get("confidence", 0.0)),
            reason=parsed.get("reason", ""),
            missing_evidence=parsed.get("missing_evidence", []),
            recommended_action=parsed.get("recommended_action", "graph_expand"),
        )
    except Exception:
        return heuristic_evidence_score(question, chunks)


def evaluate_retrieval(question: str, chunks: List[dict], use_llm: bool = True) -> RetrievalEvalOutput:
    """统一入口: 先 heuristic，再可选 LLM。"""
    start = time.time()
    fallback_used = False

    result = heuristic_evidence_score(question, chunks)

    if use_llm and result.evidence_quality != "strong":
        try:
            llm_result = llm_evaluate(question, chunks)
            result = llm_result
        except Exception:
            fallback_used = True

    latency = int((time.time() - start) * 1000)

    if result.evidence_quality == "strong":
        status: Literal["ok", "warn", "fail"] = "ok"
    elif result.evidence_quality == "weak":
        status = "warn"
    else:
        status = "fail"

    trace = {
        "module": "RetrievalEvaluator",
        "evidence_quality": result.evidence_quality,
        "confidence": result.confidence,
        "recommended_action": result.recommended_action,
        "fallback_used": fallback_used,
        "latency_ms": latency,
    }

    next_action = None
    if status != "ok":
        next_action = result.recommended_action

    return RetrievalEvalOutput(
        status=status,
        result=result,
        trace=trace,
        next_action=next_action,
    )


def run_from_state(state: dict) -> dict:
    """从 AgentState 取输入，执行检索评估，返回 state 更新字典。"""
    question = state.get("rewrite_query", state.get("question", ""))
    chunks = state.get("retrieved_chunks", [])
    use_llm = state.get("use_llm_eval", False)

    output = evaluate_retrieval(question, chunks, use_llm=use_llm)

    return {
        "retrieval_eval": output.model_dump(),
        "trace": [{
            "node": "retrieval_evaluator",
            "output": f"status={output.status}, quality={output.result.evidence_quality}",
            "latency_ms": output.trace.get("latency_ms", 0),
        }],
    }
