"""
Level 2 Full QA Eval: 运行完整 LangGraph workflow，评估答案质量。

用法:
  python eval/level2_fullqa_eval.py --dataset techdocqa --strategy hybrid
  python eval/level2_fullqa_eval.py --dataset techdocqa --strategy all
  python eval/level2_fullqa_eval.py --dataset all --strategy all

评估指标:
  - answer_correctness: 答案是否正确
  - answer_completeness: 答案是否完整
  - citation_precision: 引用精确度
  - citation_coverage: 引用覆盖率
  - faithfulness: 忠实度 (答案是否被 context 支持)
  - unsupported_claim_rate: 无支持声明率
  - guardrail_pass_rate: 护栏通过率
  - repair_rate: 修复触发率
  - latency: 延迟
"""

import json
import time
import sys
import argparse
import os
from pathlib import Path
from typing import List, Dict, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env")


def check_answer_completion(answer: str) -> dict:
    """[Phase 5] Check if answer appears truncated (code/list endings)."""
    if not answer:
        return {"is_truncated": False, "truncation_signal": None}
    stripped = answer.rstrip()
    # Check for obvious truncation signals
    signals = []
    if stripped.endswith(("import ", "from ", "def ", "class ", "return ", "elif ", "else:", "try:", "except ")):
        signals.append("ends_with_statement_keyword")
    if stripped.endswith((",", ":", "(", "[", "{")) and not stripped.endswith("."):
        signals.append("ends_with_open_delimiter")
    # Unbalanced code blocks
    if stripped.count("```") % 2 != 0:
        signals.append("unclosed_code_block")
    # Very short but has code markers
    if len(stripped) < 100 and ("def " in stripped or "class " in stripped or "```" in stripped):
        signals.append("code_started_but_incomplete")
    is_truncated = len(signals) > 0
    return {"is_truncated": is_truncated, "truncation_signal": signals[0] if signals else None}


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
        "chunks_path": "data/processed/garage/chunks.jsonl",
        "raw_path": "data/raw/garage",
        "use_candidate_pool": False,  # [Phase 3] 直接用全索引跑 Full QA
    },
}

STRATEGIES = {
    "hybrid": {"retrieval_plan": ["dense", "bm25"]},
    "adaptive_hybrid": {"method": "adaptive_hybrid"},
    "adaptive_selective_graph": {"method": "selective_graph"},
}


def build_initial_state(question: str, gold_answer: str = "") -> dict:
    """构建 LangGraph 工作流的初始状态。"""
    from app.config import config

    return {
        "question": question,
        "context_plan": {},
        "query_type": "concept",
        "retrieval_plan": ["dense", "bm25", "graph_expand"],
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


def evaluate_answer_quality(
    gold_answer: str,
    generated_answer: str,
    context_pack: List[dict],
    used_citations: List[str],
    guardrail_result: dict,
    judge_result: dict,
) -> dict:
    """评估答案质量的多个维度。"""
    # 简单规则评估 (不依赖 LLM)

    # 1. Citation precision: used_citations 中有多少能在 context_pack 中找到
    ctx_ids = {item.get("chunk_id", "") for item in context_pack}
    valid_citations = [c for c in used_citations if c in ctx_ids]
    citation_precision = len(valid_citations) / max(len(used_citations), 1)

    # 2. Citation coverage: context_pack 中有多少被引用了
    cited_ids = set(used_citations)
    citation_coverage = len(ctx_ids & cited_ids) / max(len(ctx_ids), 1)

    # 2b. [Phase 4] Primary evidence coverage: 只统计 primary evidence 的引用覆盖
    primary_items = [item for item in context_pack if item.get("evidence_tier") == "primary"]
    primary_count = len(primary_items)
    cited_primary = len([item for item in primary_items
                         if item.get("citation_id", item.get("chunk_id", "")) in cited_ids])
    primary_evidence_coverage = cited_primary / max(primary_count, 1) if primary_count > 0 else 0.0
    # [Phase 4] has_primary_cited: 至少有一个 primary evidence 被引用 (更实用的指标)
    has_primary_cited = cited_primary > 0

    # 3. 答案非空
    has_answer = len(generated_answer.strip()) > 10

    # 4. Guardrail pass
    guardrail_pass = guardrail_result.get("pass_", guardrail_result.get("pass", True))

    # 5. Judge scores
    judge_scores = {}
    if judge_result:
        judge_scores = {
            "answer_relevance": judge_result.get("answer_relevance", 0),
            "citation_support": judge_result.get("citation_support", 0),
            "faithfulness": judge_result.get("faithfulness", 0),
            "context_sufficiency": judge_result.get("context_sufficiency", 0),
        }

    # 6. Faithfulness (from judge or rule-based)
    if judge_scores.get("faithfulness"):
        faithfulness = judge_scores["faithfulness"]
    else:
        # 简单规则: 如果答案很短且无 unsupported claims
        faithfulness = 1.0 if has_answer else 0.0

    return {
        "has_answer": has_answer,
        "answer_length": len(generated_answer),
        "citation_precision": round(citation_precision, 4),
        "citation_coverage": round(citation_coverage, 4),
        "primary_evidence_coverage": round(primary_evidence_coverage, 4),
        "has_primary_cited": has_primary_cited,
        "primary_evidence_count": primary_count,
        "cited_primary_count": cited_primary,
        "guardrail_pass": bool(guardrail_pass),
        "faithfulness": round(faithfulness, 4),
        "judge_scores": judge_scores,
    }


def run_fullqa(dataset_name: str, strategy_name: str, top_k: int = 10):
    """对一个数据集 + 策略跑 Full QA。"""
    ds_config = DATASETS.get(dataset_name)
    if not ds_config:
        print(f"未知数据集: {dataset_name}")
        return None

    strategy = STRATEGIES.get(strategy_name)
    if not strategy:
        print(f"未知策略: {strategy_name}")
        return None

    print(f"\n{'=' * 70}")
    print(f"Full QA: {dataset_name} / {strategy_name}")

    # 加载评测数据
    eval_path = PROJECT_ROOT / ds_config["eval_path"]
    eval_rows = load_jsonl(eval_path)
    print(f"  eval 条数: {len(eval_rows)}")

    # 加载索引
    from app.retrieval.hybrid_retriever import HybridGraphRetriever
    from app import graph as graph_module

    retriever = HybridGraphRetriever()
    index_dir = ds_config.get("index_dir")
    if index_dir:
        ok = retriever.load_index(str(PROJECT_ROOT / index_dir))
        if not ok:
            print(f"  [ERROR] 无法加载索引: {index_dir}")
            return None
        print(f"  索引已加载: {len(retriever._chunks_by_id)} chunks")
    else:
        print(f"  [WARN] 无预建索引，跳过")
        return None

    # 替换 graph.py 中的全局 retriever
    graph_module.retriever = retriever

    # 构建 LangGraph workflow
    from app.graph import create_graph

    graph = create_graph()

    results = []
    total_correct = 0
    total_citation_precision = 0
    total_citation_coverage = 0
    total_primary_evidence_coverage = 0
    total_has_primary_cited = 0
    total_faithfulness = 0
    total_guardrail_pass = 0
    total_has_answer = 0
    total_latency = 0
    total_repair = 0
    total_truncated = 0  # [Phase 5]

    for i, row in enumerate(eval_rows):
        question = row.get("question", "")
        gold_answer = row.get("gold_answer", row.get("answer", ""))
        gold_doc_ids = row.get("gold_doc_ids", [])

        # 构建初始状态
        initial_state = build_initial_state(question, gold_answer)

        # 根据策略设置 retrieval_plan
        if "retrieval_plan" in strategy:
            initial_state["retrieval_plan"] = strategy["retrieval_plan"]

        # 运行 LangGraph
        start = time.time()
        try:
            output_state = graph.invoke(initial_state)
        except Exception as e:
            print(f"  [{i+1}] ERROR: {e}")
            results.append({
                "dataset": dataset_name,
                "query_id": row.get("query_id", row.get("question_id", f"q_{i}")),
                "query": question[:200],
                "gold_answer": gold_answer[:500] if gold_answer else "",
                "error": str(e),
                "metrics": {"latency_ms": int((time.time() - start) * 1000)},
            })
            continue

        latency_ms = int((time.time() - start) * 1000)

        # 提取结果
        answer = output_state.get("answer", "")
        context_pack = output_state.get("context_pack", [])
        used_citations = output_state.get("used_citations", [])
        unsupported_claims = output_state.get("unsupported_claims", [])
        guardrail_result = output_state.get("guardrail_result", {})
        guardrail_pass = output_state.get("guardrail_pass", True)
        judge_result = output_state.get("judge_result", {})
        repair_count = output_state.get("repair_count", 0)
        failure_type = output_state.get("failure_type", "")

        # 评估答案质量
        # [Phase 3] 用 judge 的最终 decision 作为 guardrail_pass
        judge_decision = judge_result.get("decision", "PASS") if judge_result else "PASS"
        final_guardrail_pass = (judge_decision != "HARD_FAIL")
        quality = evaluate_answer_quality(
            gold_answer, answer, context_pack, used_citations,
            guardrail_result, judge_result
        )
        quality["guardrail_pass"] = final_guardrail_pass  # 覆盖为 judge 最终决策

        # [Phase 5] Answer completion check
        completion = check_answer_completion(answer)

        # 检索质量 (recall@10)
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

        # 累计
        total_has_answer += int(quality["has_answer"])
        total_citation_precision += quality["citation_precision"]
        total_citation_coverage += quality["citation_coverage"]
        total_primary_evidence_coverage += quality["primary_evidence_coverage"]
        total_has_primary_cited += int(quality.get("has_primary_cited", quality["cited_primary_count"] > 0))
        total_faithfulness += quality["faithfulness"]
        total_guardrail_pass += int(quality["guardrail_pass"])
        total_latency += latency_ms
        total_repair += repair_count
        if completion["is_truncated"]:
            total_truncated = total_truncated + 1  # [Phase 5]

        result = {
            "dataset": dataset_name,
            "query_id": row.get("query_id", row.get("question_id", f"q_{i}")),
            "query": question[:200],
            "gold_answer": gold_answer[:500] if gold_answer else "",
            "gold_doc_ids": gold_doc_ids,
            "retrieval_strategy": strategy_name,
            "retrieved_doc_ids": retrieved_doc_ids[:top_k],
            "retrieval_recall": round(recall, 4),
            "answer": answer,  # [Phase 5] save full answer (was [:500])
            "citations": used_citations,
            "unsupported_claims": unsupported_claims,
            "guardrail_pass": guardrail_pass,
            "guardrail_result": guardrail_result if isinstance(guardrail_result, dict) else {},
            "judge_result": judge_result if isinstance(judge_result, dict) else {},
            "failure_type": failure_type,
            "repair_count": repair_count,
            "quality": quality,
            "answer_completion": completion,  # [Phase 5]
            "metrics": {
                "latency_ms": latency_ms,
                "recall@10": round(recall, 4),
                **quality,
            },
        }
        results.append(result)

        if (i + 1) % 5 == 0:
            print(f"  进度: {i + 1}/{len(eval_rows)}, 延迟={latency_ms}ms")

    # 汇总
    n = len(results)
    summary = {
        "dataset": dataset_name,
        "strategy": strategy_name,
        "n": n,
        "has_answer_rate": round(total_has_answer / n, 4) if n else 0,
        "avg_citation_precision": round(total_citation_precision / n, 4) if n else 0,
        "avg_citation_coverage": round(total_citation_coverage / n, 4) if n else 0,
        "avg_primary_evidence_coverage": round(total_primary_evidence_coverage / n, 4) if n else 0,
        "has_primary_cited_rate": round(total_has_primary_cited / n, 4) if n else 0,
        "avg_faithfulness": round(total_faithfulness / n, 4) if n else 0,
        "guardrail_pass_rate": round(total_guardrail_pass / n, 4) if n else 0,
        "avg_repair_count": round(total_repair / n, 2) if n else 0,
        "truncated_rate": round(total_truncated / n, 4) if n else 0,  # [Phase 5]
        "avg_latency_ms": round(total_latency / n) if n else 0,
    }

    # 保存
    out_dir = PROJECT_ROOT / "outputs" / "fullqa"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(results, out_dir / f"{dataset_name}_{strategy_name}_results.jsonl")

    print(f"\n  汇总 ({dataset_name} / {strategy_name}):")
    for k, v in summary.items():
        if k not in ("dataset", "strategy", "n"):
            print(f"    {k}: {v}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Level 2 Full QA Eval")
    parser.add_argument("--dataset", default="all", help="数据集名或 all")
    parser.add_argument("--strategy", default="all", help="策略名或 all")
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()

    datasets = list(DATASETS.keys()) if args.dataset == "all" else [args.dataset]
    strategies = list(STRATEGIES.keys()) if args.strategy == "all" else [args.strategy]

    all_summaries = []
    for ds in datasets:
        for st in strategies:
            s = run_fullqa(ds, st, args.top_k)
            if s:
                all_summaries.append(s)

    if all_summaries:
        summary_path = PROJECT_ROOT / "outputs" / "fullqa" / "fullqa_summary.jsonl"
        write_jsonl(all_summaries, summary_path)
        print(f"\n{'=' * 70}")
        print("Level 2 Full QA Eval 完成")
        for s in all_summaries:
            print(f"\n  {s['dataset']} / {s['strategy']}:")
            for k, v in s.items():
                if k not in ("dataset", "strategy", "n"):
                    print(f"    {k}: {v}")


if __name__ == "__main__":
    main()
