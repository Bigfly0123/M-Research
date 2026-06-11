"""Quick test: full LangGraph workflow on TechDocQA (2 samples)."""
import sys, json, time
sys.path.insert(0, ".")
from dotenv import load_dotenv
load_dotenv(".env")

# 先加载索引到全局 retriever
from app.retrieval.hybrid_retriever import HybridGraphRetriever
from app import graph as graph_module

retriever = HybridGraphRetriever()
ok = retriever.load_index("data/indexes/techdocqa")
print(f"TechDocQA index loaded: {ok}, chunks={len(retriever._chunks_by_id)}")

# 替换 graph.py 中的全局 retriever
graph_module.retriever = retriever

from app.graph import create_graph
graph = create_graph()

# 读 2 条 TechDocQA 样本
with open("data/processed/techdocqa/eval_dataset_sample_42.jsonl", "r", encoding="utf-8") as f:
    samples = [json.loads(l) for l in f][:2]

for i, row in enumerate(samples):
    question = row.get("question", "")
    gold_answer = row.get("gold_answer", row.get("answer", ""))
    gold_doc_ids = row.get("gold_doc_ids", [])
    print(f"\n--- Sample {i+1}: {question[:80]}...")
    print(f"Gold docs: {gold_doc_ids}")

    state = {
        "question": question,
        "context_plan": {},
        "query_type": "concept",
        "retrieval_plan": ["dense", "bm25", "graph_expand"],
        "context_budget": 8000,
        "rewrite_query": question,
        "retrieved_chunks": [],
        "retrieval_sources": [],
        "retrieval_eval": {},
        "context_pack": [],
        "dropped_chunks": [],
        "total_context_tokens": 0,
        "answer": "",
        "used_citations": [],
        "unsupported_claims": [],
        "answer_confidence": "",
        "guardrail_result": {},
        "guardrail_pass": True,
        "judge_result": {},
        "failure_type": "",
        "repair_action": "",
        "repair_count": 0,
        "max_repair_count": 2,
        "repair_history": [],
        "trace": [],
        "latency_ms": 0,
        "context_tokens": 0,
        "total_tokens": 0,
    }

    start = time.time()
    try:
        result = graph.invoke(state)
        latency = int((time.time() - start) * 1000)
        answer = result.get("answer", "")
        citations = result.get("used_citations", [])
        judge = result.get("judge_result", {})
        failure = result.get("failure_type", "")
        repair = result.get("repair_count", 0)
        guardrail_pass = result.get("guardrail_pass", True)

        # 检索 recall
        chunks = result.get("retrieved_chunks", [])
        ret_docs = []
        for c in chunks:
            did = ""
            if isinstance(c.get("metadata"), dict):
                did = c["metadata"].get("doc_id", "")
            if not did:
                cid = c.get("chunk_id", "")
                if "-c" in cid:
                    did = cid.rsplit("-c", 1)[0]
            if did:
                ret_docs.append(did)
        ret_docs = list(dict.fromkeys(ret_docs))[:10]
        recall = len(set(ret_docs) & set(gold_doc_ids)) / max(len(gold_doc_ids), 1)

        print(f"  Recall@10: {recall:.2f}, docs: {ret_docs[:5]}")
        print(f"  Answer ({len(answer)} chars): {answer[:200]}...")
        print(f"  Citations: {citations[:5]}")
        print(f"  Guardrail pass: {guardrail_pass}")
        print(f"  Judge: {json.dumps(judge, ensure_ascii=False)[:200]}")
        print(f"  Failure: {failure}, Repair: {repair}")
        print(f"  Latency: {latency}ms")
    except Exception as e:
        print(f"  ERROR: {e}")
        import traceback
        traceback.print_exc()
