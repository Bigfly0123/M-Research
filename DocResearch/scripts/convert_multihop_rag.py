"""
将 MultiHop-RAG 原始数据转换为 DocResearch 统一格式。

输出:
- corpus_docs.jsonl: 每篇文档一行
- chunks.jsonl: 每个 chunk 一行 (第一版: 一个 document 一个 chunk)
- eval_dataset_v1.jsonl: 每条 QA 一行
- id_maps.json: title→doc_id 映射
"""
import json
from pathlib import Path
from collections import Counter

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "multihop_rag"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "multihop_rag"

# question_type 映射表
QUESTION_TYPE_MAP = {
    "inference_query": "multi_hop",
    "comparison_query": "comparison",
    "temporal_query": "multi_hop",
    "null_query": "fact",
}

# difficulty 映射: 基于 evidence_list 长度
def infer_difficulty(num_gold_docs: int) -> str:
    if num_gold_docs == 0:
        return "easy"
    elif num_gold_docs <= 2:
        return "medium"
    else:
        return "hard"


def make_doc_id(index: int) -> str:
    return f"mh_doc_{index:06d}"


def make_q_id(index: int) -> str:
    return f"mh_q_{index:06d}"


def make_chunk_id(doc_id: str, chunk_index: int) -> str:
    return f"{doc_id}-c{chunk_index:03d}"


def load_json_any(path: Path):
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows


def write_jsonl(data, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    print(f"写入 {len(data)} 条 -> {path}")


def convert_corpus(corpus_data):
    """转换 corpus → corpus_docs.jsonl + chunks.jsonl + title→doc_id 映射。"""
    corpus_docs = []
    chunks = []
    title_to_doc_id = {}

    for i, doc in enumerate(corpus_data):
        doc_id = make_doc_id(i)
        title = doc.get("title", "")
        body = doc.get("body", "")

        # corpus_docs.jsonl
        corpus_doc = {
            "doc_id": doc_id,
            "source_dataset": "MultiHop-RAG",
            "title": title,
            "text": body,
            "metadata": {
                "original_index": i,
                "source": doc.get("source", ""),
                "category": doc.get("category", ""),
                "url": doc.get("url", ""),
            },
        }
        corpus_docs.append(corpus_doc)

        # chunks.jsonl: 第一版一个 document 一个 chunk
        chunk = {
            "chunk_id": make_chunk_id(doc_id, 0),
            "doc_id": doc_id,
            "source_dataset": "MultiHop-RAG",
            "title": title,
            "section": "",
            "text": body,
            "metadata": {
                "chunk_index": 0,
                "original_index": i,
            },
        }
        chunks.append(chunk)

        # title → doc_id 映射
        if title:
            title_to_doc_id[title] = doc_id

    return corpus_docs, chunks, title_to_doc_id


def convert_qa(qa_data, title_to_doc_id):
    """转换 QA → eval_dataset_v1.jsonl。"""
    eval_rows = []
    gold_match_stats = Counter()

    for i, qa in enumerate(qa_data):
        query = qa.get("query", "")
        answer = qa.get("answer", "")
        question_type_raw = qa.get("question_type", "")
        question_type = QUESTION_TYPE_MAP.get(question_type_raw, "unknown")
        evidence_list = qa.get("evidence_list", [])

        # 通过 evidence_list 中的 title 与 corpus 中的 title 匹配来建立 gold_doc_ids
        gold_doc_ids = []
        gold_chunk_ids = []
        gold_evidence_texts = []

        for ev in evidence_list:
            ev_title = ev.get("title", "")
            ev_fact = ev.get("fact", "")

            if ev_title and ev_title in title_to_doc_id:
                doc_id = title_to_doc_id[ev_title]
                gold_doc_ids.append(doc_id)
                gold_chunk_ids.append(make_chunk_id(doc_id, 0))

            if ev_fact:
                gold_evidence_texts.append(ev_fact)

        # 去重
        gold_doc_ids = list(dict.fromkeys(gold_doc_ids))
        gold_chunk_ids = list(dict.fromkeys(gold_chunk_ids))

        num_gold_docs = len(gold_doc_ids)
        matched = len(gold_doc_ids) > 0
        gold_match_stats["matched" if matched else "unmatched"] += 1

        eval_row = {
            "id": make_q_id(i),
            "source_dataset": "MultiHop-RAG",
            "question": query,
            "question_type": question_type,
            "expected_answer": answer,
            "gold_doc_ids": gold_doc_ids,
            "gold_chunk_ids": gold_chunk_ids,
            "gold_evidence_texts": gold_evidence_texts,
            "difficulty": infer_difficulty(num_gold_docs),
            "metadata": {
                "original_index": i,
                "num_gold_docs": num_gold_docs,
                "original_question_type": question_type_raw,
            },
        }
        eval_rows.append(eval_row)

    print(f"\ngold_doc_ids 匹配统计: {dict(gold_match_stats)}")
    return eval_rows


def main():
    print("=" * 80)
    print("MultiHop-RAG 数据转换")
    print(f"原始数据目录: {RAW_DIR}")
    print(f"输出目录: {PROCESSED_DIR}")

    # 加载原始数据
    qa_data = load_json_any(RAW_DIR / "MultiHopRAG.json")
    corpus_data = load_json_any(RAW_DIR / "corpus.json")
    print(f"加载 QA: {len(qa_data)} 条, Corpus: {len(corpus_data)} 篇")

    # 转换 corpus
    corpus_docs, chunks, title_to_doc_id = convert_corpus(corpus_data)
    print(f"Corpus docs: {len(corpus_docs)}, Chunks: {len(chunks)}, Title 映射: {len(title_to_doc_id)}")

    # 转换 QA
    eval_rows = convert_qa(qa_data, title_to_doc_id)

    # 输出文件
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    write_jsonl(corpus_docs, PROCESSED_DIR / "corpus_docs.jsonl")
    write_jsonl(chunks, PROCESSED_DIR / "chunks.jsonl")
    write_jsonl(eval_rows, PROCESSED_DIR / "eval_dataset_v1.jsonl")

    # id_maps.json
    id_maps = {"title_to_doc_id": title_to_doc_id}
    id_maps_path = PROCESSED_DIR / "id_maps.json"
    with id_maps_path.open("w", encoding="utf-8") as f:
        json.dump(id_maps, f, ensure_ascii=False, indent=2)
    print(f"写入 id_maps.json -> {id_maps_path}")

    print("\n转换完成。")


if __name__ == "__main__":
    main()
