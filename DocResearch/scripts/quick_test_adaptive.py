"""Quick test: adaptive_hybrid + selective_graph on 3 MultiHop-RAG samples."""
import json, time, sys
sys.path.insert(0, ".")
from app.retrieval.hybrid_retriever import HybridGraphRetriever

r = HybridGraphRetriever()
ok = r.load_index("data/indexes/multihop_rag")
print(f"Index loaded: {ok}, chunks_by_id={len(r._chunks_by_id)}")

with open("data/processed/multihop_rag/eval_dataset_sample_100.jsonl", "r", encoding="utf-8") as f:
    samples = [json.loads(l) for l in f][:5]

for s in samples:
    q = s["question"]
    gold = s["gold_doc_ids"]
    print(f"\n--- Q: {q[:80]}...")
    print(f"Gold ({len(gold)}): {gold}")

    # BM25 only
    bm25_r = r.retrieve(q, retrieval_plan=["bm25"], top_k=10, use_rerank=False)
    bm25_docs = list(dict.fromkeys([c.chunk_id.rsplit("-c", 1)[0] for c in bm25_r.chunks]))
    bm25_hit = len(set(bm25_docs) & set(gold)) / len(gold)

    # Adaptive hybrid
    t1 = time.time()
    adp_r = r.retrieve_adaptive_hybrid(q, k=10, use_rerank=False)
    adp_lat = int((time.time() - t1) * 1000)
    adp_docs = []
    for c in adp_r.chunks:
        did = c.metadata.get("doc_id", "") if c.metadata else ""
        if not did and "-c" in c.chunk_id:
            did = c.chunk_id.rsplit("-c", 1)[0]
        adp_docs.append(did)
    adp_docs = list(dict.fromkeys(adp_docs))
    adp_hit = len(set(adp_docs) & set(gold)) / len(gold)
    label = adp_r.trace.get("adaptive_label", "?")
    weights = adp_r.trace.get("adaptive_weights", {})

    # Selective graph
    t2 = time.time()
    sg_r = r.retrieve_selective_graph(q, k=10, use_rerank=False)
    sg_lat = int((time.time() - t2) * 1000)
    sg_docs = []
    for c in sg_r.chunks:
        did = c.metadata.get("doc_id", "") if c.metadata else ""
        if not did and "-c" in c.chunk_id:
            did = c.chunk_id.rsplit("-c", 1)[0]
        sg_docs.append(did)
    sg_docs = list(dict.fromkeys(sg_docs))
    sg_hit = len(set(sg_docs) & set(gold)) / len(gold)
    sg_info = sg_r.trace.get("selective_graph", {})

    print(f"  BM25:    recall={bm25_hit:.2f} [{bm25_docs[:3]}]")
    print(f"  Adaptive({label}, {adp_lat}ms): recall={adp_hit:.2f}, w={weights}")
    print(f"           [{adp_docs[:3]}]")
    print(f"  SelGraph({sg_lat}ms): recall={sg_hit:.2f}, trigger={sg_info.get('triggered', '?')}, reason={sg_info.get('reason', '?')}")
    print(f"           [{sg_docs[:3]}]")
