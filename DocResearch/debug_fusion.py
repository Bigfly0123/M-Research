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
    rows = [json.loads(l.strip()) for l in f if l.strip()]

# Find a case where bm25_only hits gold but hybrid doesn't
r = HybridGraphRetriever()
r.load_index("E:/its4learning/IRIS/DocResearch/data/indexes/multihop_rag")

for i, row in enumerate(rows[:20]):
    q = row["question"]
    gold = set(row.get("gold_doc_ids", []))

    # bm25 only
    res_bm25 = r.retrieve(q, retrieval_plan=["bm25"], top_k=10)
    bm25_docs = set(
        c.metadata.get("doc_id", "") if c.metadata else c.chunk_id.rsplit("-c", 1)[0]
        for c in res_bm25.chunks
    )
    bm25_hit = len(gold & bm25_docs)

    # hybrid
    res_hyb = r.retrieve(q, retrieval_plan=["dense", "bm25"], top_k=10)
    hyb_docs = set(
        c.metadata.get("doc_id", "") if c.metadata else c.chunk_id.rsplit("-c", 1)[0]
        for c in res_hyb.chunks
    )
    hyb_hit = len(gold & hyb_docs)

    if bm25_hit > hyb_hit:
        print(f"\n[{i}] bm25_hit={bm25_hit} > hybrid_hit={hyb_hit}")
        print(f"  gold: {gold}")
        bm25_only_gold = (gold & bm25_docs) - (gold & hyb_docs)
        print(f"  gold in bm25 but NOT hybrid: {bm25_only_gold}")
        # Check if these gold docs are in hybrid results at all
        for c in res_hyb.chunks:
            did = c.metadata.get("doc_id", "") if c.metadata else ""
            if did in bm25_only_gold:
                print(
                    f"  FOUND in hybrid at rank: score={c.final_score:.4f} sources={c.retrieval_sources}"
                )
        # Check top-20
        res_hyb20 = r.retrieve(q, retrieval_plan=["dense", "bm25"], top_k=20)
        hyb20_docs = set(
            c.metadata.get("doc_id", "")
            if c.metadata
            else c.chunk_id.rsplit("-c", 1)[0]
            for c in res_hyb20.chunks
        )
        if bm25_only_gold & hyb20_docs:
            print(f"  -> Found in hybrid top-20, but cut by top-10")
        break
