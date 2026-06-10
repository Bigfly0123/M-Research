"""
将 GaRAGe 原始数据转换为 DocResearch 统一格式。

GaRAGe 侧重 grounding/citation，每条样本有 15 个 grounding evidence，
其中 evidence_cited=YES 的是被引用的 gold evidence。

输出:
- corpus_docs.jsonl / chunks.jsonl / eval_dataset_v1.jsonl / id_maps.json
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "garage"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "garage"


def make_doc_id(index: int) -> str:
    return f"ge_doc_{index:06d}"


def make_q_id(index: int) -> str:
    return f"ge_q_{index:06d}"


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
    print("GaRAGe 数据转换")

    fpath = RAW_DIR / "GaRAGe_benchmark.jsonl"
    all_qa = []
    with fpath.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                all_qa.append(json.loads(line))
    print(f"加载: {len(all_qa)} 条")

    # 全局 evidence 去重
    ev_text_to_doc_id = {}
    corpus_docs = []
    chunks = []
    eval_rows = []

    for qi, qa in enumerate(all_qa):
        question = qa.get("question", "")
        answer = qa.get("answer_generate", "")
        grounding = qa.get("grounding", [])
        evidence_relevant = qa.get("evidence_relevant", [])
        evidence_cited = qa.get("evidence_cited", [])
        q_type = qa.get("question_type", "")
        q_category = qa.get("question_category", "")

        # 处理 grounding evidence
        sample_doc_ids = []
        gold_doc_ids = []
        gold_chunk_ids = []

        for ei, ev in enumerate(grounding):
            cite_text = ev.get("cite_1", "").strip()
            if not cite_text:
                continue

            # 去重
            dedup_key = cite_text[:200]
            if dedup_key in ev_text_to_doc_id:
                doc_id = ev_text_to_doc_id[dedup_key]
            else:
                di = len(corpus_docs)
                doc_id = make_doc_id(di)
                ev_text_to_doc_id[dedup_key] = doc_id

                title = cite_text[:80].split(".")[0] if cite_text else f"evidence_{ei}"

                corpus_docs.append({
                    "doc_id": doc_id,
                    "source_dataset": "GaRAGe",
                    "title": title,
                    "text": cite_text,
                    "metadata": {
                        "provider": ev.get("provider", ""),
                        "age": ev.get("age", ""),
                        "date": ev.get("date", ""),
                    },
                })

                text_for_chunk = cite_text[:6000] if len(cite_text) > 6000 else cite_text
                chunks.append({
                    "chunk_id": make_chunk_id(doc_id, 0),
                    "doc_id": doc_id,
                    "source_dataset": "GaRAGe",
                    "title": title,
                    "section": "",
                    "text": text_for_chunk,
                    "metadata": {"chunk_index": 0},
                })

            sample_doc_ids.append(doc_id)

            # gold: evidence_cited=YES 或 evidence_relevant=YES + evidence_correct=ANSWER-THE-QUESTION
            is_cited = ei < len(evidence_cited) and evidence_cited[ei] == "YES"
            is_relevant_correct = (
                ei < len(evidence_relevant) and evidence_relevant[ei] == "YES"
                and ei < len(qa.get("evidence_correct", []))
                and qa["evidence_correct"][ei] == "ANSWER-THE-QUESTION"
            )
            if is_cited or is_relevant_correct:
                gold_doc_ids.append(doc_id)
                gold_chunk_ids.append(make_chunk_id(doc_id, 0))

        gold_doc_ids = list(dict.fromkeys(gold_doc_ids))
        gold_chunk_ids = list(dict.fromkeys(gold_chunk_ids))

        difficulty = "easy" if len(gold_doc_ids) <= 1 else ("medium" if len(gold_doc_ids) <= 3 else "hard")

        eval_rows.append({
            "id": make_q_id(qi),
            "source_dataset": "GaRAGe",
            "question": question,
            "question_type": q_type,
            "expected_answer": answer,
            "gold_doc_ids": gold_doc_ids,
            "gold_chunk_ids": gold_chunk_ids,
            "difficulty": difficulty,
            "metadata": {
                "original_sample_id": qa.get("sample_id", ""),
                "question_category": q_category,
                "num_grounding": len(grounding),
                "num_gold_docs": len(gold_doc_ids),
            },
        })

    # 输出
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    write_jsonl(corpus_docs, PROCESSED_DIR / "corpus_docs.jsonl")
    write_jsonl(chunks, PROCESSED_DIR / "chunks.jsonl")
    write_jsonl(eval_rows, PROCESSED_DIR / "eval_dataset_v1.jsonl")

    id_maps = {"ev_text_to_doc_id": {k: v for k, v in ev_text_to_doc_id.items()}}
    with (PROCESSED_DIR / "id_maps.json").open("w", encoding="utf-8") as f:
        json.dump(id_maps, f, ensure_ascii=False, indent=2)

    print(f"\n转换完成: {len(corpus_docs)} docs, {len(chunks)} chunks, {len(eval_rows)} QA")


if __name__ == "__main__":
    main()
