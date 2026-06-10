"""
Step4: 生成 QA 草稿 — 读取 chunks.jsonl，用规则模板生成 QA 草稿。
目标: 50-80 条，question_type 分布: fact~8, concept~15, comparison~6,
multi_hop~10, implementation~10, troubleshooting~5
"""
import json
import re
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "techdocqa"
CHUNKS_PATH = PROCESSED_DIR / "chunks.jsonl"
QA_DRAFT_PATH = PROCESSED_DIR / "qa_draft_for_review.jsonl"

TARGET_TOTAL = 65
TYPE_TARGETS = {
    "fact": 8,
    "concept": 15,
    "comparison": 6,
    "multi_hop": 10,
    "implementation": 10,
    "troubleshooting": 5,
}

TECH_TERMS = {
    "langgraph", "stategraph", "state", "node", "edge", "checkpoint",
    "subgraph", "rag", "agentic", "retrieval", "embedding", "vector",
    "llm", "tool", "agent", "guardrail", "mcp", "context",
    "chunking", "faithfulness", "relevancy", "precision", "recall",
    "metric", "evaluation", "hallucination", "compaction", "streaming",
    "prompt", "token", "schema", "json-rpc", "reducer", "graph",
    "knowledge", "indexing", "query", "reranker", "knowledge graph",
    "entity", "relationship", "community", "dual-level",
}

TROUBLESHOOTING_PHRASES = [
    "常见问题", "troubleshoot", "error", "debug", "failure", "limitation",
    "issue", "problem", "workaround", "pitfall",
]

COMPARISON_KEYWORDS = [
    "compare", "difference", "vs", "versus", "alternative", "contrast",
]


def has_code(text: str) -> bool:
    return bool(re.search(r"```\w*", text) or re.search(r"`\S+`", text))


def has_comparison(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in COMPARISON_KEYWORDS)


def has_troubleshooting(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in TROUBLESHOOTING_PHRASES)


def extract_keywords(section: str, text: str) -> list:
    lower = (section + " " + text[:500]).lower()
    found = [t for t in TECH_TERMS if t in lower]
    words = re.findall(r"[A-Za-z_][A-Za-z0-9_]{2,}", text[:500])
    for w in words:
        wl = w.lower()
        if wl not in found and wl not in {"the", "and", "for", "with", "from", "that", "this"}:
            if any(c.isupper() for c in w) or "_" in w:
                found.append(wl)
    seen = set()
    unique = []
    for k in found:
        if k not in seen:
            seen.add(k)
            unique.append(k)
    return unique[:5]


def infer_difficulty(text: str, section: str) -> str:
    tokens = len(text) // 4
    if tokens < 100:
        return "easy"
    elif tokens < 300:
        return "medium"
    else:
        return "hard"


def select_high_quality_chunks(chunks: list) -> list:
    scored = []
    for c in chunks:
        text = c["text"]
        score = 0
        if len(text) > 200:
            score += 2
        if len(text) > 500:
            score += 1
        if has_code(text):
            score += 2
        lower = text.lower()
        if any(t in lower for t in TECH_TERMS):
            score += 1
        if has_comparison(text):
            score += 1
        scored.append((score, c))
    scored.sort(key=lambda x: -x[0])
    return [c for _, c in scored]


def generate_qa_for_chunk(chunk: dict, draft_counter: list, qa_list: list, type_counts: dict):
    """为单个 chunk 生成 QA 草稿，type_counts 控制分布上限。"""
    title = chunk["title"]
    section = chunk["section"]
    text = chunk["text"]
    chunk_id = chunk["chunk_id"]
    doc_id = chunk["doc_id"]
    keywords = extract_keywords(section, text)
    difficulty = infer_difficulty(text, section)

    def make_draft(question, question_type):
        if type_counts.get(question_type, 0) >= TYPE_TARGETS.get(question_type, 0) + 3:
            return
        draft_id = f"draft_{draft_counter[0]:04d}"
        draft_counter[0] += 1
        type_counts[question_type] = type_counts.get(question_type, 0) + 1
        draft = {
            "draft_id": draft_id,
            "source_chunk_id": chunk_id,
            "source_doc_id": doc_id,
            "question": question,
            "question_type": question_type,
            "expected_answer": text[:200],
            "expected_keywords": keywords,
            "suggested_gold_chunk_ids": [chunk_id],
            "difficulty": difficulty,
            "review_status": "pending",
        }
        qa_list.append(draft)

    display_section = section if section and section != "(header)" else title

    if type_counts.get("concept", 0) < TYPE_TARGETS["concept"] + 3:
        make_draft(
            f"在{title}中，{display_section}的作用是什么？",
            "concept",
        )

    if has_code(text) and type_counts.get("implementation", 0) < TYPE_TARGETS["implementation"] + 3:
        make_draft(
            f"如何在{title}中使用{display_section}？给出代码示例。",
            "implementation",
        )

    if has_comparison(text) and type_counts.get("comparison", 0) < TYPE_TARGETS["comparison"] + 3:
        make_draft(
            f"{title}中{display_section}与其他方案的区别和对比是什么？",
            "comparison",
        )

    if has_troubleshooting(text) and type_counts.get("troubleshooting", 0) < TYPE_TARGETS["troubleshooting"] + 3:
        make_draft(
            f"在使用{title}的{display_section}时，常见问题及解决方法是什么？",
            "troubleshooting",
        )

    if type_counts.get("fact", 0) < TYPE_TARGETS["fact"] + 3:
        make_draft(
            f"{title}中{display_section}的定义是什么？",
            "fact",
        )


def generate_multi_hop_qa(chunks_by_doc: dict, draft_counter: list, qa_list: list, type_counts: dict):
    """跨文档 multi_hop 问题。"""
    doc_ids = list(chunks_by_doc.keys())
    random.shuffle(doc_ids)

    count = 0
    for i in range(len(doc_ids) - 1):
        if count >= TYPE_TARGETS["multi_hop"]:
            break
        d1, d2 = doc_ids[i], doc_ids[i + 1]
        c1 = chunks_by_doc[d1][0]
        c2 = chunks_by_doc[d2][0]

        t1 = c1["title"]
        s1 = c1["section"] if c1["section"] != "(header)" else t1
        t2 = c2["title"]
        s2 = c2["section"] if c2["section"] != "(header)" else t2

        if type_counts.get("multi_hop", 0) >= TYPE_TARGETS["multi_hop"] + 2:
            break

        draft_id = f"draft_{draft_counter[0]:04d}"
        draft_counter[0] += 1
        type_counts["multi_hop"] = type_counts.get("multi_hop", 0) + 1
        count += 1

        combined_text = (c1["text"][:100] + " " + c2["text"][:100])
        kw = extract_keywords(s1 + " " + s2, combined_text)

        draft = {
            "draft_id": draft_id,
            "source_chunk_id": c1["chunk_id"],
            "source_doc_id": d1,
            "question": f"{t1}的{s1}与{t2}的{s2}在RAG系统中分别扮演什么角色？它们如何协同工作？",
            "question_type": "multi_hop",
            "expected_answer": c1["text"][:100] + " " + c2["text"][:100],
            "expected_keywords": kw,
            "suggested_gold_chunk_ids": [c1["chunk_id"], c2["chunk_id"]],
            "difficulty": "hard",
            "review_status": "pending",
        }
        qa_list.append(draft)


def fill_to_target(qa_list: list, draft_counter: list, type_counts: dict, chunks: list):
    """补充不足的 type 到目标数量。"""
    for qtype, target in TYPE_TARGETS.items():
        current = type_counts.get(qtype, 0)
        needed = target - current
        if needed <= 0:
            continue
        random.shuffle(chunks)
        for c in chunks:
            if needed <= 0:
                break
            title = c["title"]
            section = c["section"]
            display = section if section and section != "(header)" else title
            text = c["text"]
            keywords = extract_keywords(section, text)
            difficulty = infer_difficulty(text, section)

            draft_id = f"draft_{draft_counter[0]:04d}"
            draft_counter[0] += 1
            type_counts[qtype] = type_counts.get(qtype, 0) + 1
            needed -= 1

            if qtype == "fact":
                q = f"{title}中{display}的核心概念是什么？"
            elif qtype == "concept":
                q = f"在{title}中，{display}的设计原理是什么？"
            elif qtype == "comparison":
                q = f"{title}的{display}与其他类似功能相比有什么优势？"
            elif qtype == "implementation":
                q = f"如何实现{title}中的{display}？请说明关键步骤。"
            elif qtype == "troubleshooting":
                q = f"在{title}中使用{display}时可能遇到什么问题？如何排查？"
            elif qtype == "multi_hop":
                q = f"{title}的{display}如何与RAG整体流程结合？"
            else:
                q = f"关于{title}的{display}，请说明其作用。"

            draft = {
                "draft_id": draft_id,
                "source_chunk_id": c["chunk_id"],
                "source_doc_id": c["doc_id"],
                "question": q,
                "question_type": qtype,
                "expected_answer": text[:200],
                "expected_keywords": keywords,
                "suggested_gold_chunk_ids": [c["chunk_id"]],
                "difficulty": difficulty,
                "review_status": "pending",
            }
            qa_list.append(draft)


def main():
    random.seed(42)
    print("=" * 80)
    print("Step4: 生成 QA 草稿")

    chunks = []
    with CHUNKS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                chunks.append(json.loads(line))
    print(f"加载 {len(chunks)} 个 chunks")

    hq_chunks = select_high_quality_chunks(chunks)
    print(f"高质量 chunks: {len(hq_chunks)}")

    chunks_by_doc = {}
    for c in chunks:
        chunks_by_doc.setdefault(c["doc_id"], []).append(c)

    qa_list = []
    draft_counter = [1]
    type_counts = {}

    for c in hq_chunks:
        generate_qa_for_chunk(c, draft_counter, qa_list, type_counts)

    generate_multi_hop_qa(chunks_by_doc, draft_counter, qa_list, type_counts)

    fill_to_target(qa_list, draft_counter, type_counts, chunks)

    for qtype, target in TYPE_TARGETS.items():
        current = type_counts.get(qtype, 0)
        if current > target:
            excess = current - target
            to_remove = [i for i, d in enumerate(qa_list) if d["question_type"] == qtype]
            to_remove = to_remove[-excess:]
            for idx in sorted(to_remove, reverse=True):
                qa_list.pop(idx)
                type_counts[qtype] -= 1

    if len(qa_list) < 50:
        print(f"  警告: QA 草稿数量 {len(qa_list)} < 50")

    with QA_DRAFT_PATH.open("w", encoding="utf-8") as f:
        for draft in qa_list:
            f.write(json.dumps(draft, ensure_ascii=False) + "\n")

    from collections import Counter
    type_dist = Counter(d["question_type"] for d in qa_list)
    print(f"\n写入 {len(qa_list)} 条 -> {QA_DRAFT_PATH}")
    print(f"question_type 分布: {dict(type_dist)}")
    print("Step4 完成。")


if __name__ == "__main__":
    main()
