"""
为 StratRAG 和 GaRAGe 构建索引并做端到端验证。
只索引 sample 涉及的 chunk，减少 embedding 调用量。
"""
import json
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.retrieval.hybrid_retriever import HybridGraphRetriever

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def build_and_eval(name: str, processed_dir: Path, index_dir: Path, sample_path: Path):
    print(f"\n{'='*80}\n{name}: 建索引 + 端到端验证")

    chunks_all = load_jsonl(processed_dir / "chunks.jsonl")
    print(f"总 chunks: {len(chunks_all)}")

    # 收集 sample 涉及的 doc_ids
    sample_rows = load_jsonl(sample_path)
    needed_doc_ids = set()
    for r in sample_rows:
        needed_doc_ids.update(r.get("gold_doc_ids", []))
    print(f"sample 涉及 {len(needed_doc_ids)} 个 gold doc")

    # 只索引需要的 chunk (+ distractors: 每个 gold doc 加一些随机干扰)
    import random
    random.seed(42)
    gold_chunks = [c for c in chunks_all if c["doc_id"] in needed_doc_ids]

    # 补充一些 distractor chunks (最多 500)
    other_chunks = [c for c in chunks_all if c["doc_id"] not in needed_doc_ids]
    random.shuffle(other_chunks)
    distractor_chunks = other_chunks[:500]

    index_chunks = gold_chunks + distractor_chunks
    print(f"索引 chunks: {len(gold_chunks)} gold + {len(distractor_chunks)} distractor = {len(index_chunks)}")

    # 确保 source_path 字段存在 (用于 retrieval metadata 中的 source)
    for c in index_chunks:
        if "source_path" not in c or not c["source_path"]:
            c["source_path"] = c.get("doc_id", "")

    # 建索引
    print("构建索引...")
    t0 = time.time()
    retriever = HybridGraphRetriever()
    retriever.build_index(index_chunks, index_dir=str(index_dir))
    print(f"索引构建完成: {time.time()-t0:.1f}s")

    # 端到端验证
    n = min(10, len(sample_rows))
    recall_sum = 0
    print(f"\n端到端验证 (前 {n} 条):")

    for i, row in enumerate(sample_rows[:n]):
        q = row["question"]
        gold_doc_ids = set(row.get("gold_doc_ids", []))
        result = retriever.retrieve(q, top_k=10)
        retrieved_doc_ids = set(c.chunk_id.rsplit("-c", 1)[0] for c in result.chunks)
        hits = len(gold_doc_ids & retrieved_doc_ids)
        recall = hits / len(gold_doc_ids) if gold_doc_ids else 0
        recall_sum += recall
        print(f"  [{i+1}] recall={recall:.2f} gold={len(gold_doc_ids)} hits={hits}")

    print(f"\n平均 recall@10: {recall_sum/n:.3f}")


def main():
    build_and_eval(
        "StratRAG",
        PROJECT_ROOT / "data" / "processed" / "stratrag",
        PROJECT_ROOT / "data" / "indexes" / "stratrag",
        PROJECT_ROOT / "data" / "processed" / "stratrag" / "eval_dataset_sample_100.jsonl",
    )
    build_and_eval(
        "GaRAGe",
        PROJECT_ROOT / "data" / "processed" / "garage",
        PROJECT_ROOT / "data" / "indexes" / "garage",
        PROJECT_ROOT / "data" / "processed" / "garage" / "eval_dataset_sample_50.jsonl",
    )


if __name__ == "__main__":
    main()
