"""
Context Budget 控制器。

确保送入 LLM 的证据 token 不超过预算，超长时按优先级截断。
"""

from app.ingestion.chunker import Chunk


def enforce_budget(chunks: list[dict], budget: int) -> tuple[list[dict], list[dict]]:
    """按 final_score 排序，依次累加 token 直到预算用尽。
    返回 (kept_chunks, dropped_chunks)。"""
    sorted_chunks = sorted(chunks, key=lambda c: c.get("final_score", 0), reverse=True)

    kept = []
    dropped = []
    used_tokens = 0

    for chunk in sorted_chunks:
        tokens = chunk.get("token_count", len(chunk.get("text", "")) // 3)
        if used_tokens + tokens <= budget:
            kept.append(chunk)
            used_tokens += tokens
        else:
            dropped.append({**chunk, "drop_reason": "over_budget"})

    return kept, dropped
