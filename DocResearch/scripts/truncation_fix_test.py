"""Quick test to verify answer truncation fix (Phase 5)."""
import json, sys, time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")

def main():
    # Load truncation test samples
    rows = []
    with open(PROJECT_ROOT / "data" / "eval" / "truncation_test.jsonl", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    
    rows = rows[:5]  # limit to 5
    print(f"Testing {len(rows)} truncation-prone questions...\n")
    
    # Load techdocqa index
    from app.retrieval.hybrid_retriever import HybridGraphRetriever
    from app import graph as graph_module
    
    retriever = HybridGraphRetriever()
    ok = retriever.load_index(str(PROJECT_ROOT / "data" / "indexes" / "techdocqa"))
    if not ok:
        print("ERROR: Failed to load techdocqa index")
        return
    graph_module.retriever = retriever
    
    from app.graph import create_graph
    graph = create_graph()
    
    from eval.level2_fullqa_eval import check_answer_completion
    
    results = []
    for i, row in enumerate(rows):
        q = row["question"]
        print(f"[{i+1}/{len(rows)}] {q[:80]}...")
        
        initial_state = {
            "question": q,
            "gold_answer": row.get("expected_answer", ""),
            "query_type": "concept",
            "retrieved_chunks": [],
            "context_pack": [],
            "answer": "",
            "used_citations": [],
            "unsupported_claims": [],
            "answer_confidence": "medium",
            "guardrail_result": {},
            "guardrail_pass": True,
            "judge_result": {},
            "repair_count": 0,
            "max_repair_count": 2,
            "repair_history": [],
            "trace": [],
            "failure_type": "",
        }
        
        t0 = time.time()
        try:
            output_state = graph.invoke(initial_state)
            answer = output_state.get("answer", "")
        except Exception as e:
            answer = f"ERROR: {e}"
        
        latency = int((time.time() - t0) * 1000)
        completion = check_answer_completion(answer)
        
        print(f"  Answer length: {len(answer)} chars")
        print(f"  Last 80 chars: ...{answer[-80:]}")
        print(f"  Truncated: {completion['is_truncated']} (signal: {completion['truncation_signal']})")
        print(f"  Latency: {latency}ms\n")
        
        results.append({
            "question": q,
            "answer_length": len(answer),
            "answer_tail": answer[-100:],
            "answer_full": answer,
            "is_truncated": completion["is_truncated"],
            "truncation_signal": completion["truncation_signal"],
            "latency_ms": latency,
        })
    
    # Save results
    out_path = PROJECT_ROOT / "outputs" / "fullqa" / "truncation_test_results.jsonl"
    with open(out_path, "w", encoding="utf-8") as f:
        for r in results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    
    # Summary
    trunc_count = sum(1 for r in results if r["is_truncated"])
    avg_len = sum(r["answer_length"] for r in results) / len(results)
    print(f"\n=== Truncation Test Summary ===")
    print(f"Total: {len(results)}")
    print(f"Avg answer length: {avg_len:.0f} chars")
    print(f"Truncated: {trunc_count}/{len(results)}")
    print(f"Results saved to: {out_path}")

if __name__ == "__main__":
    main()
