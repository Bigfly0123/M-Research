"""
通用 Level 1 Eval Runner: 支持 4 个数据集 + 多策略检索对比。

用法:
  python eval/level1_eval.py --dataset stratrag --strategy dense_only
  python eval/level1_eval.py --dataset stratrag --strategy all
  python eval/level1_eval.py --dataset all --strategy all
"""

import json
import time
import sys
import argparse
import os
import random
from pathlib import Path
from typing import List, Dict, Set, Optional
from collections import defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from eval.metrics import (
    gold_doc_recall_at_k,
    all_gold_docs_hit_at_k,
    gold_chunk_recall_at_k,
    selected_evidence_recall,
)

import platform as _p

_c = _p.platform()
_p.platform = lambda *a, **kw: _c


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
    "multihop_rag": {
        "eval_path": "data/processed/multihop_rag/eval_dataset_v1.jsonl",
        "chunks_path": "data/processed/multihop_rag/chunks.jsonl",
        "index_dir": "data/indexes/multihop_rag",
        "sample_path": "data/processed/multihop_rag/eval_dataset_sample_100.jsonl",
        "use_sample": True,
    },
    "techdocqa": {
        "eval_path": "data/processed/techdocqa/eval_dataset_sample_42.jsonl",
        "chunks_path": "data/processed/techdocqa/chunks.jsonl",
        "index_dir": "data/indexes/techdocqa",
    },
    "stratrag": {
        "eval_path": "data/processed/stratrag/eval_dataset_sample_100.jsonl",
        "chunks_path": "data/processed/stratrag/chunks.jsonl",
        "raw_path": "data/raw/stratrag",
        "use_candidate_pool": True,
    },
    "garage": {
        "eval_path": "data/processed/garage/eval_dataset_sample_50.jsonl",
        "chunks_path": "data/processed/garage/chunks.jsonl",
        "raw_path": "data/raw/garage",
        "use_candidate_pool": True,
    },
}

STRATEGIES = {
    "dense_only": {"use_dense": True, "use_bm25": False, "use_graph": False},
    "bm25_only": {"use_dense": False, "use_bm25": True, "use_graph": False},
    "hybrid": {"use_dense": True, "use_bm25": True, "use_graph": False},
    "hybrid_graph": {"use_dense": True, "use_bm25": True, "use_graph": True},
    "adaptive_hybrid": {"method": "adaptive_hybrid"},
    "selective_graph": {"method": "selective_graph"},
}


def get_retrieval_plan(strategy: dict) -> List[str]:
    plan = []
    if strategy.get("use_dense"):
        plan.append("dense")
    if strategy.get("use_bm25"):
        plan.append("bm25")
    if strategy.get("use_graph"):
        plan.append("graph_expand")
    return plan if plan else ["dense"]


def build_candidate_pool_index(
    dataset_name: str, ds_config: dict, eval_rows: List[dict], strategy_name: str
):
    """为 StratRAG/GaRAGe 构建 per-query candidate pool 索引 (controlled hard setting)。"""
    from app.retrieval.hybrid_retriever import HybridGraphRetriever

    chunks_path = PROJECT_ROOT / ds_config["chunks_path"]
    all_chunks = load_jsonl(chunks_path)

    # 收集所有 sample 涉及的 doc_ids
    needed_doc_ids = set()
    for row in eval_rows:
        needed_doc_ids.update(row.get("gold_doc_ids", []))
        # 对于 StratRAG, 也需要 distractor doc_ids (从 candidate_doc_ids 或从原始数据)
        needed_doc_ids.update(row.get("candidate_doc_ids", []))

    # 如果没有 candidate_doc_ids, 从原始数据补充
    if dataset_name == "stratrag" and not eval_rows[0].get("candidate_doc_ids"):
        raw_dir = PROJECT_ROOT / ds_config["raw_path"]
        qa_by_id = {}
        for fname in ["train.jsonl", "val.jsonl"]:
            fp = raw_dir / fname
            if fp.exists():
                with fp.open("r", encoding="utf-8") as f:
                    for line in f:
                        if line.strip():
                            qa = json.loads(line.strip())
                            qa_by_id[qa.get("id", "")] = qa

        # 补充 candidate_doc_ids 到 eval_rows
        eval_qa_ids = {r.get("metadata", {}).get("original_id", "") for r in eval_rows}
        doc_text_to_doc_id = {}
        for c in all_chunks:
            key = c.get("text", "")[:200]
            if key:
                doc_text_to_doc_id[key] = c["doc_id"]

        for row in eval_rows:
            orig_id = row.get("metadata", {}).get("original_id", "")
            if orig_id in qa_by_id:
                qa = qa_by_id[orig_id]
                cand_ids = []
                for doc in qa.get("doc_pool", []):
                    key = doc.get("text", "")[:200]
                    if key in doc_text_to_doc_id:
                        cand_ids.append(doc_text_to_doc_id[key])
                row["candidate_doc_ids"] = cand_ids
                needed_doc_ids.update(cand_ids)

    elif dataset_name == "garage" and not eval_rows[0].get("candidate_doc_ids"):
        # GaRAGe: 所有 grounding evidence 都是 candidate
        for row in eval_rows:
            row["candidate_doc_ids"] = row.get("gold_doc_ids", [])
        # 从原始数据补充所有 evidence doc_ids
        raw_path = PROJECT_ROOT / ds_config["raw_path"] / "GaRAGe_benchmark.jsonl"
        if raw_path.exists():
            orig_samples = {}
            with raw_path.open("r", encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        s = json.loads(line.strip())
                        orig_samples[s.get("sample_id", "")] = s

            doc_text_to_doc_id = {}
            for c in all_chunks:
                key = c.get("text", "")[:200]
                if key:
                    doc_text_to_doc_id[key] = c["doc_id"]

            for row in eval_rows:
                orig_id = row.get("metadata", {}).get("original_sample_id", "")
                if orig_id in orig_samples:
                    sample = orig_samples[orig_id]
                    cand_ids = []
                    for ev in sample.get("grounding", []):
                        key = ev.get("cite_1", "").strip()[:200]
                        if key in doc_text_to_doc_id:
                            cand_ids.append(doc_text_to_doc_id[key])
                    row["candidate_doc_ids"] = cand_ids
                    needed_doc_ids.update(cand_ids)

    # 筛选 chunks
    index_chunks = [c for c in all_chunks if c["doc_id"] in needed_doc_ids]
    # 确保 source_path
    for c in index_chunks:
        if "source_path" not in c or not c["source_path"]:
            c["source_path"] = c.get("doc_id", "")

    print(f"  candidate pool: {len(index_chunks)} chunks ({len(needed_doc_ids)} docs)")

    # 建索引
    index_dir = str(
        PROJECT_ROOT / "data" / "indexes" / dataset_name / f"hard_{strategy_name}"
    )
    retriever = HybridGraphRetriever()
    retriever.build_index(index_chunks, index_dir=index_dir)
    print(f"  索引已建: {index_dir}")

    return retriever, index_dir


def load_existing_index(dataset_name: str, strategy_name: str):
    """加载已有索引。"""
    from app.retrieval.hybrid_retriever import HybridGraphRetriever

    # 先尝试 strategy-specific 目录
    for subdir in [f"hard_{strategy_name}", strategy_name, ""]:
        index_dir = (
            str(PROJECT_ROOT / "data" / "indexes" / dataset_name / subdir)
            if subdir
            else str(PROJECT_ROOT / "data" / "indexes" / dataset_name)
        )
        if os.path.exists(index_dir):
            retriever = HybridGraphRetriever()
            loaded = retriever.load_index(index_dir)
            if loaded:
                print(f"  索引加载: {index_dir}")
                return retriever, index_dir
    return None, None


def mrr_at_k(
    retrieved_doc_ids: List[str], gold_doc_ids: List[str], k: int
) -> Optional[float]:
    gold: Set[str] = set(gold_doc_ids)
    if not gold:
        return None
    for i, doc_id in enumerate(retrieved_doc_ids[:k]):
        if doc_id in gold:
            return 1.0 / (i + 1)
    return 0.0


def run_eval(dataset_name: str, strategy_name: str, top_k: int = 10):
    """跑单个数据集 + 单策略的 retrieval-only eval。"""
    ds_config = DATASETS[dataset_name]
    strategy = STRATEGIES[strategy_name]
    retrieval_plan = get_retrieval_plan(strategy)

    print(f"\n{'=' * 70}")
    print(f"数据集: {dataset_name} | 策略: {strategy_name} | plan: {retrieval_plan}")

    # 加载 eval 数据
    if ds_config.get("use_sample") and ds_config.get("sample_path"):
        eval_path = PROJECT_ROOT / ds_config["sample_path"]
    else:
        eval_path = PROJECT_ROOT / ds_config["eval_path"]
    eval_rows = load_jsonl(eval_path)
    print(f"eval 条数: {len(eval_rows)}")

    # 获取检索器
    use_pool = ds_config.get("use_candidate_pool", False)
    if use_pool:
        retriever, index_dir = build_candidate_pool_index(
            dataset_name, ds_config, eval_rows, strategy_name
        )
    else:
        retriever, index_dir = load_existing_index(dataset_name, strategy_name)
        if retriever is None:
            print(f"  [错误] 找不到 {dataset_name} 的索引，跳过")
            return None

    # 跑检索评测
    results = []
    for i, row in enumerate(eval_rows):
        question = row.get("question", "")
        gold_doc_ids = row.get("gold_doc_ids", [])
        gold_chunk_ids = row.get("gold_chunk_ids", [])

        start = time.time()
        # 判断策略类型: 新方法用专属函数，旧方法用 retrieve()
        method_name = strategy.get("method")
        if method_name == "adaptive_hybrid":
            retrieval_result = retriever.retrieve_adaptive_hybrid(
                question, k=top_k, use_rerank=False
            )
        elif method_name == "selective_graph":
            retrieval_result = retriever.retrieve_selective_graph(
                question, k=top_k, use_rerank=False
            )
        else:
            retrieval_result = retriever.retrieve(
                question, retrieval_plan=retrieval_plan, top_k=top_k,
                use_rerank=False,
            )
        latency_ms = int((time.time() - start) * 1000)

        retrieved_doc_ids = []
        retrieved_chunk_ids = []
        for chunk in retrieval_result.chunks:
            retrieved_chunk_ids.append(chunk.chunk_id)
            # 优先从 metadata 取 doc_id，否则从 chunk_id 解析
            doc_id = chunk.metadata.get("doc_id", "") if chunk.metadata else ""
            if not doc_id and "-c" in chunk.chunk_id:
                doc_id = chunk.chunk_id.rsplit("-c", 1)[0]
            if doc_id:
                retrieved_doc_ids.append(doc_id)

        metrics = {
            "gold_doc_recall@5": gold_doc_recall_at_k(
                retrieved_doc_ids, gold_doc_ids, 5
            ),
            "gold_doc_recall@10": gold_doc_recall_at_k(
                retrieved_doc_ids, gold_doc_ids, top_k
            ),
            "all_gold_hit@10": all_gold_docs_hit_at_k(
                retrieved_doc_ids, gold_doc_ids, top_k
            ),
            "gold_chunk_recall@10": gold_chunk_recall_at_k(
                retrieved_chunk_ids, gold_chunk_ids, top_k
            ),
            "mrr@10": mrr_at_k(retrieved_doc_ids, gold_doc_ids, top_k),
            "latency_ms": latency_ms,
        }

        results.append(
            {
                "question_id": row.get("id", ""),
                "question": question,
                "gold_doc_ids": gold_doc_ids,
                "retrieved_doc_ids": retrieved_doc_ids[:top_k],
                "metrics": metrics,
            }
        )

        if (i + 1) % 20 == 0:
            print(f"  进度: {i + 1}/{len(eval_rows)}")

    # 汇总
    summary = summarize(results, dataset_name, strategy_name)

    # 保存
    out_dir = PROJECT_ROOT / "reports" / dataset_name
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(results, out_dir / f"{strategy_name}_results.jsonl")

    return summary


def summarize(results: List[dict], dataset_name: str, strategy_name: str) -> dict:
    """计算汇总指标。"""
    metric_keys = [
        "gold_doc_recall@5",
        "gold_doc_recall@10",
        "all_gold_hit@10",
        "gold_chunk_recall@10",
        "mrr@10",
    ]
    summary = {"dataset": dataset_name, "strategy": strategy_name, "n": len(results)}

    for mk in metric_keys:
        values = [r["metrics"][mk] for r in results if r["metrics"].get(mk) is not None]
        if values:
            summary[mk] = round(sum(values) / len(values), 4)
        else:
            summary[mk] = None

    latencies = [r["metrics"]["latency_ms"] for r in results]
    summary["avg_latency_ms"] = (
        round(sum(latencies) / len(latencies)) if latencies else 0
    )

    print(f"\n  汇总 ({dataset_name} / {strategy_name}):")
    for mk in metric_keys:
        v = summary.get(mk)
        print(f"    {mk}: {v:.4f}" if v is not None else f"    {mk}: N/A")
    print(f"    avg_latency_ms: {summary['avg_latency_ms']}")

    return summary


def main():
    parser = argparse.ArgumentParser(description="Level 1 Eval Runner")
    parser.add_argument("--dataset", default="all", help="数据集名或 all")
    parser.add_argument("--strategy", default="all", help="策略名或 all")
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args()

    datasets = list(DATASETS.keys()) if args.dataset == "all" else [args.dataset]
    strategies = list(STRATEGIES.keys()) if args.strategy == "all" else [args.strategy]

    all_summaries = []
    for ds in datasets:
        for st in strategies:
            s = run_eval(ds, st, args.top_k)
            if s:
                all_summaries.append(s)

    # 保存总汇总
    if all_summaries:
        summary_path = PROJECT_ROOT / "reports" / "level1_summary.jsonl"
        write_jsonl(all_summaries, summary_path)
        print(f"\n{'=' * 70}")
        print("Level 1 Eval 完成，汇总:")
        print(
            f"{'dataset':<15} {'strategy':<15} {'recall@5':>10} {'recall@10':>10} {'all_hit@10':>10} {'MRR@10':>10} {'latency':>8}"
        )
        print("-" * 78)
        for s in all_summaries:
            r5 = s.get("gold_doc_recall@5", 0) or 0
            r10 = s.get("gold_doc_recall@10", 0) or 0
            hit = s.get("all_gold_hit@10", 0) or 0
            mrr = s.get("mrr@10", 0) or 0
            lat = s.get("avg_latency_ms", 0)
            print(
                f"{s['dataset']:<15} {s['strategy']:<15} {r5:>10.4f} {r10:>10.4f} {hit:>10.4f} {mrr:>10.4f} {lat:>8}ms"
            )


if __name__ == "__main__":
    main()
