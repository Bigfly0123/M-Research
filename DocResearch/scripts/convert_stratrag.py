"""
将 StratRAG 原始数据转换为 DocResearch 统一格式。

每条 StratRAG 样本包含 15 个候选文档(2 gold + 13 distractors)，
我们提取所有文档建立 corpus，gold 文档建立 eval 关联。

输出:
- corpus_docs.jsonl / chunks.jsonl / eval_dataset_v1.jsonl / id_maps.json
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "stratrag"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "stratrag"


def make_doc_id(index: int) -> str:
    return f"sr_doc_{index:06d}"


def make_q_id(index: int) -> str:
    return f"sr_q_{index:06d}"


def make_chunk_id(doc_id: str, chunk_index: int) -> str:
    return f"{doc_id}-c{chunk_index:03d}"


def write_jsonl(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"写入 {len(data)} 条 -> {path}")


def main():
    print("=" * 80)
    print("StratRAG 数据转换")

    # 加载 train + val
    all_qa = []
    for fname in ["train.jsonl", "val.jsonl"]:
        fpath = RAW_DIR / fname
        if fpath.exists():
            with fpath.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        all_qa.append(json.loads(line))
    print(f"加载 QA: {len(all_qa)} 条")

    # 全局 doc 去重 (doc_pool 中不同样本可能共享文档)
    doc_text_to_doc_id = {}
    corpus_docs = []
    chunks = []
    eval_rows = []

    for qi, qa in enumerate(all_qa):
        query = qa.get("query", "")
        answer = qa.get("reference_answer", "")
        doc_pool = qa.get("doc_pool", [])
        gold_indices = qa.get("gold_doc_indices", [])
        q_type = qa.get("metadata", {}).get("question_type", "unknown")

        # 处理 doc_pool
        sample_doc_ids = []
        for doc in doc_pool:
            doc_text = doc.get("text", "")
            doc_orig_id = doc.get("doc_id", "")

            # 去重: 用 text 前 200 字符做 key
            dedup_key = doc_text[:200]
            if dedup_key in doc_text_to_doc_id:
                sample_doc_ids.append(doc_text_to_doc_id[dedup_key])
                continue

            di = len(corpus_docs)
            doc_id = make_doc_id(di)
            doc_text_to_doc_id[dedup_key] = doc_id

            title = doc_text[:80].split("\n")[0] if doc_text else doc_orig_id

            corpus_docs.append({
                "doc_id": doc_id,
                "source_dataset": "StratRAG",
                "title": title,
                "text": doc_text,
                "metadata": {"original_doc_id": doc_orig_id},
            })

            # 截断长文本
            text_for_chunk = doc_text[:6000] if len(doc_text) > 6000 else doc_text
            chunks.append({
                "chunk_id": make_chunk_id(doc_id, 0),
                "doc_id": doc_id,
                "source_dataset": "StratRAG",
                "title": title,
                "section": "",
                "text": text_for_chunk,
                "metadata": {"chunk_index": 0},
            })

            sample_doc_ids.append(doc_id)

        # gold 文档
        gold_doc_ids = []
        gold_chunk_ids = []
        for gi in gold_indices:
            if 0 <= gi < len(sample_doc_ids):
                gd_id = sample_doc_ids[gi]
                gold_doc_ids.append(gd_id)
                gold_chunk_ids.append(make_chunk_id(gd_id, 0))

        gold_doc_ids = list(dict.fromkeys(gold_doc_ids))
        gold_chunk_ids = list(dict.fromkeys(gold_chunk_ids))

        difficulty = "easy" if len(gold_doc_ids) <= 1 else ("medium" if len(gold_doc_ids) <= 2 else "hard")

        eval_rows.append({
            "id": make_q_id(qi),
            "source_dataset": "StratRAG",
            "question": query,
            "question_type": q_type,
            "expected_answer": answer,
            "gold_doc_ids": gold_doc_ids,
            "gold_chunk_ids": gold_chunk_ids,
            "difficulty": difficulty,
            "metadata": {
                "original_id": qa.get("id", ""),
                "num_gold_docs": len(gold_doc_ids),
                "num_candidate_docs": len(doc_pool),
            },
        })

    # 输出
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(corpus_docs, PROCESSED_DIR / "corpus_docs.jsonl")
    write_jsonl(chunks, PROCESSED_DIR / "chunks.jsonl")
    write_jsonl(eval_rows, PROCESSED_DIR / "eval_dataset_v1.jsonl")

    id_maps = {"doc_text_to_doc_id": {k: v for k, v in doc_text_to_doc_id.items()}}
    with (PROCESSED_DIR / "id_maps.json").open("w", encoding="utf-8") as f:
        json.dump(id_maps, f, ensure_ascii=False, indent=2)

    print(f"\n转换完成: {len(corpus_docs)} docs, {len(chunks)} chunks, {len(eval_rows)} QA")


if __name__ == "__main__":
    main()
