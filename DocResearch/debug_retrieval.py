import sys, json

sys.path.insert(0, "E:/its4learning/IRIS/DocResearch")

import platform as _p

_c = _p.platform()
_p.platform = lambda *a, **kw: _c

from app.retrieval.hybrid_retriever import HybridGraphRetriever

with open(
    "E:/its4learning/IRIS/DocResearch/data/processed/multihop_rag/eval_dataset_sample_100.jsonl",
    encoding="utf-8",
) as f:
    first = json.loads(f.readline())

print("question:", first["question"])
print("gold_doc_ids:", first["gold_doc_ids"])
print("gold_chunk_ids:", first["gold_chunk_ids"])

r = HybridGraphRetriever()
loaded = r.load_index("E:/its4learning/IRIS/DocResearch/data/indexes/multihop_rag")
print(f"Index loaded: {loaded}")
print(f"Dense index: {r.dense.index is not None}")
print(f"BM25 docs: {len(r.bm25.docs) if hasattr(r.bm25, 'docs') else 'N/A'}")

import time

t0 = time.time()
res = r.retrieve(first["question"], retrieval_plan=["dense"], top_k=10)
lat = int((time.time() - t0) * 1000)
print(f"\nRetrieved {len(res.chunks)} chunks in {lat}ms")
for c in res.chunks[:5]:
    doc_id = c.chunk_id.rsplit("-c", 1)[0]
    print(f"  chunk_id={c.chunk_id} doc_id={doc_id} score={c.dense_score:.3f}")

retrieved_doc_ids = [c.chunk_id.rsplit("-c", 1)[0] for c in res.chunks]
gold = set(first["gold_doc_ids"])
retrieved = set(retrieved_doc_ids)
print(f"\nGold: {gold}")
print(f"Retrieved doc_ids: {retrieved}")
print(f"Intersection: {gold & retrieved}")
