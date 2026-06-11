import json

with open(
    "E:/its4learning/IRIS/DocResearch/data/processed/multihop_rag/eval_dataset_v1.jsonl",
    encoding="utf-8",
) as f:
    first = json.loads(f.readline())
print("gold_doc_ids:", first.get("gold_doc_ids"))
print("gold_chunk_ids:", first.get("gold_chunk_ids"))
