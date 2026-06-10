"""
检查 MultiHop-RAG 转换后的数据质量。

输出: docs数量、chunks数量、eval rows数量、question非空数量、answer非空数量、
gold_doc_ids非空数量、gold_chunk_ids非空数量、gold docs数量分布、前3条样本预览。
"""
import json
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "multihop_rag"


def load_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def check():
    print("=" * 80)
    print("MultiHop-RAG 转换质量检查")

    # 加载数据
    docs = load_jsonl(PROCESSED_DIR / "corpus_docs.jsonl")
    chunks = load_jsonl(PROCESSED_DIR / "chunks.jsonl")
    eval_rows = load_jsonl(PROCESSED_DIR / "eval_dataset_v1.jsonl")

    print(f"\ndocs 数量: {len(docs)}")
    print(f"chunks 数量: {len(chunks)}")
    print(f"eval rows 数量: {len(eval_rows)}")

    # eval 数据质量统计
    q_nonempty = sum(1 for r in eval_rows if r.get("question"))
    a_nonempty = sum(1 for r in eval_rows if r.get("expected_answer"))
    gold_doc_nonempty = sum(1 for r in eval_rows if r.get("gold_doc_ids"))
    gold_chunk_nonempty = sum(1 for r in eval_rows if r.get("gold_chunk_ids"))

    total = len(eval_rows)
    print(f"\nquestion 非空数量: {q_nonempty}/{total} ({q_nonempty/total*100:.1f}%)")
    print(f"expected_answer 非空数量: {a_nonempty}/{total} ({a_nonempty/total*100:.1f}%)")
    print(f"gold_doc_ids 非空数量: {gold_doc_nonempty}/{total} ({gold_doc_nonempty/total*100:.1f}%)")
    print(f"gold_chunk_ids 非空数量: {gold_chunk_nonempty}/{total} ({gold_chunk_nonempty/total*100:.1f}%)")

    # gold docs 数量分布
    gold_doc_count_dist = Counter(len(r.get("gold_doc_ids", [])) for r in eval_rows)
    print("\ngold_doc_ids 数量分布:")
    for cnt, num in sorted(gold_doc_count_dist.items()):
        print(f"  {cnt} 个 gold docs: {num} 条 ({num/total*100:.1f}%)")

    # question_type 分布
    qt_dist = Counter(r.get("question_type") for r in eval_rows)
    print("\nquestion_type 分布:")
    for qt, num in qt_dist.most_common():
        print(f"  {qt}: {num}")

    # difficulty 分布
    diff_dist = Counter(r.get("difficulty") for r in eval_rows)
    print("\ndifficulty 分布:")
    for d, num in diff_dist.most_common():
        print(f"  {d}: {num}")

    # 前 3 条样本预览
    print("\n前 3 条 eval 样本预览:")
    for i, row in enumerate(eval_rows[:3]):
        print(f"\n--- 样本 {i} ---")
        preview = {
            "id": row["id"],
            "question": row["question"][:100],
            "question_type": row["question_type"],
            "expected_answer": row["expected_answer"][:80],
            "gold_doc_ids": row["gold_doc_ids"],
            "gold_chunk_ids": row["gold_chunk_ids"],
            "difficulty": row["difficulty"],
        }
        print(json.dumps(preview, ensure_ascii=False, indent=2))

    # 验收判断
    print("\n" + "=" * 80)
    print("验收判断:")
    checks = [
        ("question 基本全部非空", q_nonempty / total > 0.95),
        ("expected_answer 基本全部非空", a_nonempty / total > 0.95),
        ("gold_doc_ids 不能大量为空", gold_doc_nonempty / total > 0.7),
        ("gold_chunk_ids 不能大量为空", gold_chunk_nonempty / total > 0.7),
    ]
    all_pass = True
    for desc, passed in checks:
        status = "通过" if passed else "失败"
        print(f"  [{status}] {desc}")
        if not passed:
            all_pass = False

    if all_pass:
        print("\n全部验收通过！")
    else:
        print("\n存在验收失败项，请检查转换逻辑。")


if __name__ == "__main__":
    check()
