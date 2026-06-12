"""
Level 2 Full QA Ablation Eval: Vanilla RAG vs Hybrid RAG vs Full System.

用法:
  python eval/level2_ablation_eval.py --dataset techdocqa --mode vanilla_rag
  python eval/level2_ablation_eval.py --dataset techdocqa --mode all
  python eval/level2_ablation_eval.py --dataset all --mode all

三种模式:
  vanilla_rag:             dense-only retrieval, no guardrails/judge/repair
  hybrid_no_guardrails:    adaptive hybrid retrieval + evidence composer, no guardrails/judge/repair
  full_system:             complete DocResearch-Agent v1.0 pipeline

输出:
  outputs/level2_ablation/{dataset}_{mode}_results.jsonl
"""

import json
import time
import sys
import argparse
from pathlib import Path
from typing import List

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


def load_jsonl(path: Path) -> List[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(data: List[dict], path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


DATASETS = {
    "techdocqa": {
        "eval_path": "data/processed/techdocqa/eval_dataset_sample_42.jsonl",
        "index_dir": "data/indexes/techdocqa",
    },
    "garage": {
        "eval_path": "data/processed/garage/eval_dataset_sample_50.jsonl",
        "index_dir": "data/indexes/garage",
    },
}

MODES = {
    "vanilla_rag": "Dense-only retrieval + simple answer, no reliability modules",
    "hybrid_no_guardrails": "Adaptive hybrid + evidence composer, no guardrails/judge/repair",
    "full_system": "Complete DocResearch-Agent v1.0 pipeline",
}


# ---------------------------------------------------------------------------
# Graph builders
# ---------------------------------------------------------------------------

def build_initial_state(question: str, mode: str) -> dict:
    """Build initial state, varying retrieval plan by mode."""
    from app.config import config

    if mode == "vanilla_rag":
        retrieval_plan = ["dense"]  # dense-only
    else:
        retrieval_plan = ["dense", "bm25", "graph_expand"]

    return {
        "question": question,
        "context_plan": {},
        "query_type": "concept",
        "retrieval_plan": retrieval_plan,
        "context_budget": config.DEFAULT_CONTEXT_BUDGET,
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


def create_vanilla_graph():
    """Vanilla RAG: dense retriever → evidence composer → answer generator → END.

    Skips: context_planner (LLM planning), retrieval_evaluator, guardrails, judge, repair.
    """
    from langgraph.graph import StateGraph, END
    from app.state import AgentState
    from app.graph import hybrid_graph_retriever, evidence_composer, grounded_answer_generator

    workflow = StateGraph(AgentState)

    # Passthrough node: set retrieval_plan to dense-only
    def set_dense_only(state):
        return {"retrieval_plan": ["dense"]}

    workflow.add_node("set_dense_only", set_dense_only)
    workflow.add_node("hybrid_graph_retriever", hybrid_graph_retriever)
    workflow.add_node("evidence_composer", evidence_composer)
    workflow.add_node("answer_generator", grounded_answer_generator)

    workflow.set_entry_point("set_dense_only")
    workflow.add_edge("set_dense_only", "hybrid_graph_retriever")
    workflow.add_edge("hybrid_graph_retriever", "evidence_composer")
    workflow.add_edge("evidence_composer", "answer_generator")
    workflow.add_edge("answer_generator", END)

    return workflow.compile()


def create_hybrid_no_guardrails_graph():
    """Hybrid RAG w/o guardrails: full retrieval + evidence pipeline, but stops after answer generation.

    Skips: citation_guardrails, self_reflection_judge, repair_router.
    """
    from langgraph.graph import StateGraph, END
    from app.state import AgentState
    from app.graph import (
        context_planner,
        hybrid_graph_retriever,
        retrieval_evaluator,
        evidence_composer,
        grounded_answer_generator,
    )

    workflow = StateGraph(AgentState)

    workflow.add_node("context_planner", context_planner)
    workflow.add_node("hybrid_graph_retriever", hybrid_graph_retriever)
    workflow.add_node("retrieval_evaluator", retrieval_evaluator)
    workflow.add_node("evidence_composer", evidence_composer)
    workflow.add_node("answer_generator", grounded_answer_generator)

    workflow.set_entry_point("context_planner")
    workflow.add_edge("context_planner", "hybrid_graph_retriever")
    workflow.add_edge("hybrid_graph_retriever", "retrieval_evaluator")
    workflow.add_edge("retrieval_evaluator", "evidence_composer")
    workflow.add_edge("evidence_composer", "answer_generator")
    workflow.add_edge("answer_generator", END)

    return workflow.compile()


def create_full_system_graph():
    """Full System: complete DocResearch-Agent v1.0 pipeline."""
    from app.graph import create_graph
    return create_graph()


GRAPH_BUILDERS = {
    "vanilla_rag": create_vanilla_graph,
    "hybrid_no_guardrails": create_hybrid_no_guardrails_graph,
    "full_system": create_full_system_graph,
}


# ---------------------------------------------------------------------------
# Evaluation logic (reused from level2_fullqa_eval.py)
# ---------------------------------------------------------------------------

def evaluate_answer_quality(generated_answer, context_pack, used_citations,
                            guardrail_result, judge_result):
    """Evaluate answer quality metrics."""
    ctx_ids = {item.get("chunk_id", "") for item in context_pack}
    valid_citations = [c for c in used_citations if c in ctx_ids]
    citation_precision = len(valid_citations) / max(len(used_citations), 1)

    cited_ids = set(used_citations)
    citation_coverage = len(ctx_ids & cited_ids) / max(len(ctx_ids), 1)

    primary_items = [item for item in context_pack if item.get("evidence_tier") == "primary"]
    primary_count = len(primary_items)
    cited_primary = len([item for item in primary_items
                         if item.get("citation_id", item.get("chunk_id", "")) in cited_ids])
    primary_evidence_coverage = cited_primary / max(primary_count, 1) if primary_count > 0 else 0.0
    has_primary_cited = cited_primary > 0

    has_answer = len(generated_answer.strip()) > 10

    # Faithfulness from judge
    judge_scores = {}
    if judge_result:
        judge_scores = {
            "answer_relevance": judge_result.get("answer_relevance", 0),
            "citation_support": judge_result.get("citation_support", 0),
            "faithfulness": judge_result.get("faithfulness", 0),
            "context_sufficiency": judge_result.get("context_sufficiency", 0),
        }

    if judge_scores.get("faithfulness"):
        faithfulness = judge_scores["faithfulness"]
    else:
        # For vanilla/hybrid modes without judge: use rule-based approximation
        faithfulness = 1.0 if (has_answer and len(valid_citations) > 0) else (0.5 if has_answer else 0.0)

    # Unsupported claim rate approximation
    unsupported_claim_rate = 1.0 - faithfulness

    return {
        "has_answer": has_answer,
        "answer_length": len(generated_answer),
        "citation_precision": round(citation_precision, 4),
        "citation_coverage": round(citation_coverage, 4),
        "primary_evidence_coverage": round(primary_evidence_coverage, 4),
        "has_primary_cited": has_primary_cited,
        "faithfulness": round(faithfulness, 4),
        "unsupported_claim_rate": round(unsupported_claim_rate, 4),
        "judge_scores": judge_scores,
    }


def check_answer_completion(answer: str) -> dict:
    """Check if answer appears truncated."""
    if not answer:
        return {"is_truncated": False, "truncation_signal": None}
    stripped = answer.rstrip()
    signals = []
    if stripped.endswith(("import ", "from ", "def ", "class ", "return ", "elif ", "else:", "try:", "except ")):
        signals.append("ends_with_statement_keyword")
    if stripped.endswith((",", ":", "(", "[", "{")) and not stripped.endswith("."):
        signals.append("ends_with_open_delimiter")
    if stripped.count("```") % 2 != 0:
        signals.append("unclosed_code_block")
    if len(stripped) < 100 and ("def " in stripped or "class " in stripped or "```" in stripped):
        signals.append("code_started_but_incomplete")
    return {"is_truncated": len(signals) > 0, "truncation_signal": signals[0] if signals else None}


# ---------------------------------------------------------------------------
# Main run function
# ---------------------------------------------------------------------------

def run_ablation(dataset_name: str, mode: str, top_k: int = 10, limit: int = 0):
    """Run ablation eval for one dataset + mode."""
    ds_config = DATASETS.get(dataset_name)
    if not ds_config:
        print(f"Unknown dataset: {dataset_name}")
        return None

    print(f"\n{'=' * 70}")
    print(f"Ablation: {dataset_name} / {mode}")
    print(f"  Description: {MODES[mode]}")

    # Load eval data
    eval_path = PROJECT_ROOT / ds_config["eval_path"]
    eval_rows = load_jsonl(eval_path)
    if limit > 0:
        eval_rows = eval_rows[:limit]
    print(f"  eval samples: {len(eval_rows)}")

    # Load index
    from app.retrieval.hybrid_retriever import HybridGraphRetriever
    from app import graph as graph_module

    retriever = HybridGraphRetriever()
    index_dir = ds_config.get("index_dir")
    if index_dir:
        ok = retriever.load_index(str(PROJECT_ROOT / index_dir))
        if not ok:
            print(f"  [ERROR] Cannot load index: {index_dir}")
            return None
        print(f"  index loaded: {len(retriever._chunks_by_id)} chunks")
    graph_module.retriever = retriever

    # Build graph
    graph = GRAPH_BUILDERS[mode]()

    # Run
    results = []
    total_has_answer = 0
    total_citation_precision = 0
    total_citation_coverage = 0
    total_faithfulness = 0
    total_unsupported_claim_rate = 0
    total_latency = 0
    total_truncated = 0
    total_answer_length = 0

    for i, row in enumerate(eval_rows):
        question = row.get("question", "")
        gold_answer = row.get("gold_answer", row.get("answer", ""))
        gold_doc_ids = row.get("gold_doc_ids", [])

        initial_state = build_initial_state(question, mode)

        t0 = time.time()
        try:
            output_state = graph.invoke(initial_state)
        except Exception as e:
            print(f"  [{i+1}] ERROR: {e}")
            results.append({
                "dataset": dataset_name,
                "mode": mode,
                "query_id": row.get("id", row.get("query_id", f"q_{i}")),
                "query": question[:200],
                "error": str(e),
            })
            continue

        latency_ms = int((time.time() - t0) * 1000)

        answer = output_state.get("answer", "")
        context_pack = output_state.get("context_pack", [])
        used_citations = output_state.get("used_citations", [])
        guardrail_result = output_state.get("guardrail_result", {})
        judge_result = output_state.get("judge_result", {})
        repair_count = output_state.get("repair_count", 0)

        # Evaluate
        quality = evaluate_answer_quality(
            answer, context_pack, used_citations, guardrail_result, judge_result
        )
        completion = check_answer_completion(answer)

        # Retrieval recall
        retrieved_chunks = output_state.get("retrieved_chunks", [])
        retrieved_doc_ids = []
        for c in retrieved_chunks:
            did = c.get("metadata", {}).get("doc_id", "") if isinstance(c.get("metadata"), dict) else ""
            if not did:
                cid = c.get("chunk_id", "")
                if "-c" in cid:
                    did = cid.rsplit("-c", 1)[0]
            if did:
                retrieved_doc_ids.append(did)
        retrieved_doc_ids = list(dict.fromkeys(retrieved_doc_ids))[:top_k]
        recall = len(set(retrieved_doc_ids) & set(gold_doc_ids)) / max(len(gold_doc_ids), 1)

        # Accumulate
        total_has_answer += int(quality["has_answer"])
        total_citation_precision += quality["citation_precision"]
        total_citation_coverage += quality["citation_coverage"]
        total_faithfulness += quality["faithfulness"]
        total_unsupported_claim_rate += quality["unsupported_claim_rate"]
        total_latency += latency_ms
        total_answer_length += quality["answer_length"]
        if completion["is_truncated"]:
            total_truncated += 1

        result = {
            "dataset": dataset_name,
            "mode": mode,
            "query_id": row.get("id", row.get("query_id", f"q_{i}")),
            "query": question[:200],
            "gold_doc_ids": gold_doc_ids,
            "retrieved_doc_ids": retrieved_doc_ids[:top_k],
            "retrieval_recall": round(recall, 4),
            "answer": answer,
            "citations": used_citations,
            "quality": quality,
            "answer_completion": completion,
            "repair_count": repair_count,
            "guardrail_result": guardrail_result if isinstance(guardrail_result, dict) else {},
            "judge_result": judge_result if isinstance(judge_result, dict) else {},
            "latency_ms": latency_ms,
        }
        results.append(result)

        if (i + 1) % 5 == 0:
            print(f"  progress: {i + 1}/{len(eval_rows)}, latency={latency_ms}ms")

    # Summary
    n = len(results)
    summary = {
        "dataset": dataset_name,
        "mode": mode,
        "n": n,
        "has_answer_rate": round(total_has_answer / n, 4) if n else 0,
        "avg_citation_precision": round(total_citation_precision / n, 4) if n else 0,
        "avg_citation_coverage": round(total_citation_coverage / n, 4) if n else 0,
        "avg_faithfulness": round(total_faithfulness / n, 4) if n else 0,
        "avg_unsupported_claim_rate": round(total_unsupported_claim_rate / n, 4) if n else 0,
        "avg_answer_length": round(total_answer_length / n) if n else 0,
        "truncated_rate": round(total_truncated / n, 4) if n else 0,
        "avg_latency_ms": round(total_latency / n) if n else 0,
    }

    # Save results
    out_dir = PROJECT_ROOT / "outputs" / "level2_ablation"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(results, out_dir / f"{dataset_name}_{mode}_results.jsonl")

    print(f"\n  Summary ({dataset_name} / {mode}):")
    for k, v in summary.items():
        if k not in ("dataset", "mode", "n"):
            print(f"    {k}: {v}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Level 2 Full QA Ablation Eval")
    parser.add_argument("--dataset", default="all", help="Dataset name or 'all'")
    parser.add_argument("--mode", default="all", help="Mode: vanilla_rag / hybrid_no_guardrails / full_system / all")
    parser.add_argument("--top-k", type=int, default=10)
    parser.add_argument("--limit", type=int, default=0, help="Limit samples (0 = all)")
    args = parser.parse_args()

    datasets = list(DATASETS.keys()) if args.dataset == "all" else [args.dataset]
    modes = list(MODES.keys()) if args.mode == "all" else [args.mode]

    all_summaries = []
    for ds in datasets:
        for mode in modes:
            s = run_ablation(ds, mode, args.top_k, args.limit)
            if s:
                all_summaries.append(s)

    if all_summaries:
        # Save all summaries
        out_dir = PROJECT_ROOT / "outputs" / "level2_ablation"
        summary_path = out_dir / "ablation_summary.jsonl"
        write_jsonl(all_summaries, summary_path)

        print(f"\n{'=' * 70}")
        print("Phase 5.1 Full QA Ablation Complete")
        print(f"{'=' * 70}")

        # Print comparison table
        for ds in datasets:
            ds_results = [s for s in all_summaries if s["dataset"] == ds]
            if len(ds_results) > 1:
                print(f"\n  {ds.upper()} Ablation Comparison:")
                print(f"  {'Mode':<25} {'CitePrec':>10} {'Faithful':>10} {'UnsuppRt':>10} {'AnsLen':>8} {'Latency':>8}")
                print(f"  {'-'*25} {'-'*10} {'-'*10} {'-'*10} {'-'*8} {'-'*8}")
                for s in ds_results:
                    print(f"  {s['mode']:<25} {s['avg_citation_precision']:>10.4f} {s['avg_faithfulness']:>10.4f} "
                          f"{s['avg_unsupported_claim_rate']:>10.4f} {s['avg_answer_length']:>8} {s['avg_latency_ms']:>8}")


if __name__ == "__main__":
    main()
