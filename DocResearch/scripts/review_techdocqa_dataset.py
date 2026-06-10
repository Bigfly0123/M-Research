"""
TechDocQA 数据集质量审核脚本。

检查项:
- 总问题数
- question_type 分布
- difficulty 分布
- expected_answer 非空率
- expected_keywords 非空率
- gold_doc_ids 非空率
- gold_chunk_ids 非空率
- gold_chunk_ids 是否存在于 chunks.jsonl
- 重复问题
- 前3条预览

验收标准:
- 问题数量: 30-50
- expected_answer 非空率: 100%
- gold_chunk_ids 非空率: 100%
- gold_chunk_ids 存在率: 100%
- 重复问题: 0
- question_type 至少覆盖 5 类
- multi_hop 至少 5 条
- troubleshooting 至少 3 条
"""
import json
from collections import Counter
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "techdocqa"


def load_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def non_empty_rate(rows, field):
    ok = sum(1 for r in rows if r.get(field))
    return ok, len(rows), ok / len(rows) if len(rows) else 0


def review(eval_path: Path, chunks_path: Path):
    rows = load_jsonl(eval_path)
    chunks = load_jsonl(chunks_path)
    chunk_ids = {c["chunk_id"] for c in chunks}

    print("=" * 60)
    print(f"TechDocQA Dataset Review: {eval_path.name}")
    print("=" * 60)

    print(f"\n1. 总问题数: {len(rows)}")

    type_dist = Counter(r.get("question_type") for r in rows)
    print(f"\n2. question_type 分布:")
    for qt, cnt in sorted(type_dist.items(), key=lambda x: -x[1]):
        print(f"   {qt}: {cnt}")

    diff_dist = Counter(r.get("difficulty") for r in rows)
    print(f"\n3. difficulty 分布:")
    for d, cnt in sorted(diff_dist.items(), key=lambda x: -x[1]):
        print(f"   {d}: {cnt}")

    for field in ["expected_answer", "expected_keywords", "gold_doc_ids", "gold_chunk_ids"]:
        ok, total, rate = non_empty_rate(rows, field)
        print(f"\n4. {field} 非空率: {ok}/{total} = {rate*100:.1f}%")

    missing_chunks = []
    for r in rows:
        for cid in r.get("gold_chunk_ids", []):
            if cid not in chunk_ids:
                missing_chunks.append((r["id"], cid))
    exist_rate = 1 - len(missing_chunks) / sum(len(r.get("gold_chunk_ids", [])) for r in rows) if sum(len(r.get("gold_chunk_ids", [])) for r in rows) else 0
    print(f"\n5. gold_chunk_ids 存在率: {exist_rate*100:.1f}%")
    if missing_chunks:
        print(f"   缺失的 chunk_ids:")
        for qid, cid in missing_chunks[:10]:
            print(f"     {qid} -> {cid}")

    questions = [r.get("question", "") for r in rows]
    seen = {}
    duplicates = []
    for i, q in enumerate(questions):
        if q in seen:
            duplicates.append((seen[q], i, q[:60]))
        else:
            seen[q] = i
    print(f"\n6. 重复问题: {len(duplicates)}")
    for a, b, preview in duplicates[:5]:
        print(f"   row {a} vs row {b}: {preview}...")

    print(f"\n7. 前3条预览:")
    for r in rows[:3]:
        print(f"   [{r['id']}] type={r.get('question_type')} difficulty={r.get('difficulty')}")
        print(f"   Q: {r['question'][:80]}...")
        print(f"   A: {r.get('expected_answer','')[:80]}...")
        print(f"   chunks: {r.get('gold_chunk_ids', [])}")
        print()

    # === 验收 ===
    print("=" * 60)
    print("验收结果")
    print("=" * 60)
    checks = []

    c = ("问题数量 30-50", 30 <= len(rows) <= 50)
    checks.append(c)

    ea_ok, _, ea_rate = non_empty_rate(rows, "expected_answer")
    c = (f"expected_answer 非空率 100% (实际 {ea_rate*100:.1f}%)", ea_rate == 1.0)
    checks.append(c)

    gc_ok, _, gc_rate = non_empty_rate(rows, "gold_chunk_ids")
    c = (f"gold_chunk_ids 非空率 100% (实际 {gc_rate*100:.1f}%)", gc_rate == 1.0)
    checks.append(c)

    c = (f"gold_chunk_ids 存在率 100% (实际 {exist_rate*100:.1f}%)", exist_rate == 1.0)
    checks.append(c)

    c = (f"重复问题 0 (实际 {len(duplicates)})", len(duplicates) == 0)
    checks.append(c)

    type_count = len(type_dist)
    c = (f"question_type 覆盖 >=5 类 (实际 {type_count})", type_count >= 5)
    checks.append(c)

    mh_count = type_dist.get("multi_hop", 0)
    c = (f"multi_hop >=5 条 (实际 {mh_count})", mh_count >= 5)
    checks.append(c)

    ts_count = type_dist.get("troubleshooting", 0)
    c = (f"troubleshooting >=3 条 (实际 {ts_count})", ts_count >= 3)
    checks.append(c)

    all_pass = True
    for desc, ok in checks:
        status = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        print(f"  [{status}] {desc}")

    print()
    if all_pass:
        print(">>> 全部验收通过! <<<")
    else:
        print(">>> 存在验收不通过项! <<<")
    return all_pass


if __name__ == "__main__":
    eval_path = PROCESSED_DIR / "eval_dataset_v1.jsonl"
    chunks_path = PROCESSED_DIR / "chunks.jsonl"
    review(eval_path, chunks_path)
