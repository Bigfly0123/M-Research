import sys, json

sys.path.insert(0, "E:/its4learning/IRIS/DocResearch")
import platform as _p

_c = _p.platform()
_p.platform = lambda *a, **kw: _c

from app.retrieval.hybrid_retriever import HybridGraphRetriever

with open(
    "E:/its4learning/IRIS/DocResearch/data/processed/techdocqa/eval_dataset_sample_42.jsonl",
    encoding="utf-8",
) as f:
    first = json.loads(f.readline())

print("question:", first["question"][:100])
print("gold_doc_ids:", first.get("gold_doc_ids"))
print("gold_chunk_ids:", first.get("gold_chunk_ids"))

r = HybridGraphRetriever()
loaded = r.load_index("E:/its4learning/IRIS/DocResearch/data/indexes/techdocqa")
print(f"Index loaded: {loaded}")
print(f"Dense index: {r.dense.index is not None}")

res = r.retrieve(first["question"], retrieval_plan=["dense"], top_k=5)
print(f"Retrieved {len(res.chunks)} chunks")
for c in res.chunks[:3]:
    doc_id = c.chunk_id.rsplit("-c", 1)[0]
    print(f"  chunk_id={c.chunk_id} doc_id={doc_id}")

retrieved = set(c.chunk_id.rsplit("-c", 1)[0] for c in res.chunks)
gold = set(first.get("gold_doc_ids", []))
print(f"\nGold: {gold}")
print(f"Retrieved: {retrieved}")
print(f"Intersection: {gold & retrieved}")
