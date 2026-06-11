"""
Evidence Composer: 证据组织与上下文压缩层。

去重 → 按 source/section 聚合 → 分配 citation_id → 标注 evidence role →
超 budget 时保留 definition/procedure/code → 超长压缩 → 控制 context budget。

指南模块06: EvidenceItem(citation_id, chunk_id, source, section_path, evidence_text,
compressed_text, role, support_score)。
"""

import re
import time
from typing import List, Optional, Literal
from pydantic import BaseModel, Field
from app.config import config


class EvidenceItem(BaseModel):
    """证据项 schema (Phase 3 增强版)。"""
    citation_id: str
    chunk_id: str
    source: str = ""
    section_path: List[str] = Field(default_factory=list)
    evidence_text: str = ""
    compressed_text: Optional[str] = None
    role: Literal["definition", "procedure", "comparison", "example", "code", "limitation"] = "definition"
    evidence_tier: Literal["primary", "supporting", "context_only"] = "primary"
    support_score: float = 0.0


class ContextPack(BaseModel):
    """Evidence Composer 输出。"""
    status: Literal["ok", "warn", "fail"] = "ok"
    context_pack: List[EvidenceItem] = Field(default_factory=list)
    dropped_chunks: List[dict] = Field(default_factory=list)
    total_context_tokens: int = 0
    trace: dict = Field(default_factory=dict)
    next_action: Optional[str] = None


def classify_evidence_tier(chunk: dict, question: str, rank: int, total: int) -> str:
    """[Phase 3] 证据分层: primary / supporting / context_only。

    - primary: top-ranked chunks 或直接回答问题的高分 chunks
    - supporting: 中等分数，提供背景或补充信息
    - context_only: 低分 chunks，仅供 LLM 理解上下文
    """
    score = chunk.get("final_score", 0.0)

    # Top 30% 且分数较高 → primary
    if rank <= max(2, total // 3) and score > 0.3:
        return "primary"
    # 中间 40% → supporting
    elif rank <= max(4, total * 7 // 10) and score > 0.1:
        return "supporting"
    # 剩余 → context_only
    else:
        return "context_only"


def deduplicate(chunks: List[dict]) -> tuple:
    """按 chunk_id 去重，返回 (kept, dropped)。"""
    seen = set()
    kept = []
    dropped = []
    for c in chunks:
        cid = c.get("chunk_id", "")
        if cid in seen:
            dropped.append({"chunk_id": cid, "reason": "duplicate"})
        else:
            seen.add(cid)
            kept.append(c)
    return kept, dropped


def classify_role(chunk: dict, question: str) -> str:
    """规则版证据角色分类。"""
    text = chunk.get("text", "").lower()
    if any(w in text for w in ["limitation", "cannot", "does not support", "限制", "不支持"]):
        return "limitation"
    if any(w in text for w in ["```", "def ", "class ", "import ", "function "]):
        return "code"
    if any(w in text for w in ["define", "definition", "是指", "定义为"]):
        return "definition"
    if " is a " in text or " refers to " in text:
        return "definition"
    if any(w in text for w in ["how to", "step", "process", "algorithm", "步骤", "流程"]):
        return "procedure"
    if any(w in text for w in ["compare", "versus", "vs", "difference", "对比", "区别"]):
        return "comparison"
    if any(w in text for w in ["example", "for instance", "e.g.", "例如", "示例"]):
        return "example"
    return "definition"


def compress_chunk(text: str, question: str, max_tokens: int = 500) -> str:
    """超长 chunk 做截断压缩 (第一版不用 LLM，避免依赖)。"""
    token_count = len(text) // 3
    if token_count <= max_tokens:
        return text
    return text[: max_tokens * 3]


def compose_context_pack(
    chunks: List[dict],
    question: str,
    context_budget: int = 3500,
) -> ContextPack:
    """组合 evidence pack 统一入口: 去重 → 排序 → 角色标注 → citation_id → budget 截断。"""
    start = time.time()

    if not chunks:
        return ContextPack(
            status="fail",
            trace={"module": "EvidenceComposer", "error": "no_chunks", "fallback_used": False, "latency_ms": 0},
            next_action="check_retrieval",
        )

    kept, dup_dropped = deduplicate(chunks)
    kept.sort(key=lambda c: c.get("final_score", 0), reverse=True)

    pack = []
    used_tokens = 0
    all_dropped = list(dup_dropped)
    total_kept = len(kept)

    for rank, chunk in enumerate(kept, 1):
        cid = chunk.get("chunk_id", "")
        compressed = compress_chunk(chunk.get("text", ""), question, max_tokens=500)
        tokens = len(compressed) // 3

        if used_tokens + tokens > context_budget:
            role = classify_role(chunk, question)
            if role in ("definition", "procedure", "code"):
                all_dropped.append({"chunk_id": cid, "reason": "over_budget_high_priority"})
            else:
                all_dropped.append({"chunk_id": cid, "reason": "over_budget"})
            continue

        source = chunk.get("source", chunk.get("metadata", {}).get("source", ""))
        section = chunk.get("section", chunk.get("metadata", {}).get("section", ""))
        section_path = section.split(" > ") if section else []

        tier = classify_evidence_tier(chunk, question, rank, total_kept)

        item = EvidenceItem(
            citation_id=cid,
            chunk_id=cid,
            source=source,
            section_path=section_path,
            evidence_text=chunk.get("text", ""),
            compressed_text=compressed,
            role=classify_role(chunk, question),
            evidence_tier=tier,
            support_score=chunk.get("final_score", 0.0),
        )
        pack.append(item)
        used_tokens += tokens

    status = "ok" if len(pack) >= 3 else ("warn" if pack else "fail")
    latency = int((time.time() - start) * 1000)

    # 统计 evidence tier 分布
    tier_counts = {"primary": 0, "supporting": 0, "context_only": 0}
    for item in pack:
        tier_counts[item.evidence_tier] += 1

    trace = {
        "module": "EvidenceComposer",
        "pack_size": len(pack),
        "dropped_count": len(all_dropped),
        "total_tokens": used_tokens,
        "budget": context_budget,
        "tier_distribution": tier_counts,
        "fallback_used": False,
        "latency_ms": latency,
    }

    return ContextPack(
        status=status,
        context_pack=pack,
        dropped_chunks=all_dropped,
        total_context_tokens=used_tokens,
        trace=trace,
        next_action=None if status == "ok" else "check_retrieval_quality",
    )


def run_from_state(state: dict) -> dict:
    """从 AgentState 取输入，执行证据组合，返回 state 更新。"""
    chunks = state.get("retrieved_chunks", [])
    question = state.get("question", "")
    budget = state.get("context_budget", config.DEFAULT_CONTEXT_BUDGET)
    pack = compose_context_pack(chunks, question, context_budget=budget)
    return {
        "context_pack": [item.model_dump() for item in pack.context_pack],
        "dropped_chunks": pack.dropped_chunks,
        "total_context_tokens": pack.total_context_tokens,
        "trace": [{"node": "evidence_composer", "output": f"pack={len(pack.context_pack)}, tokens={pack.total_context_tokens}", "latency_ms": pack.trace.get("latency_ms", 0)}],
    }
