"""
生成 MultiHop-RAG 评测报告。

读取多个 results.jsonl，生成 eval_report.md。
"""
import json
import argparse
from pathlib import Path
from collections import defaultdict
from typing import List, Dict

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_jsonl(path: Path) -> List[dict]:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def compute_summary(results: List[dict]) -> Dict:
    """计算单组结果的汇总指标。"""
    if not results:
        return {}

    metric_keys = [
        "gold_doc_recall@10",
        "all_gold_docs_hit@10",
        "gold_chunk_recall@10",
        "selected_evidence_recall",
        "answer_keyword_coverage",
    ]

    summary = {}
    for mk in metric_keys:
        values = [r["metrics"][mk] for r in results if r["metrics"].get(mk) is not None]
        if values:
            summary[mk] = sum(values) / len(values)
        else:
            summary[mk] = None

    latencies = [r["metrics"]["latency_ms"] for r in results if r["metrics"].get("latency_ms") is not None]
    summary["avg_latency_ms"] = sum(latencies) / len(latencies) if latencies else None
    summary["count"] = len(results)

    return summary


def find_failure_cases(results: List[dict], max_cases: int = 5) -> List[dict]:
    """找出检索完全失败 (gold_doc_recall@10=0) 的案例。"""
    failures = []
    for r in results:
        recall = r["metrics"].get("gold_doc_recall@10")
        if recall is not None and recall == 0.0 and r.get("gold_doc_ids"):
            failures.append({
                "question_id": r.get("question_id", ""),
                "question": r.get("question", "")[:100],
                "gold_doc_ids": r.get("gold_doc_ids", []),
            })
            if len(failures) >= max_cases:
                break
    return failures


def generate_report(input_paths: List[Path], output_path: Path):
    """生成评测报告。"""
    # 收集各组结果
    configs_data = {}
    for path in input_paths:
        config_name = path.stem.replace("_results", "")
        results = load_jsonl(path)
        summary = compute_summary(results)
        failures = find_failure_cases(results)
        configs_data[config_name] = {
            "results": results,
            "summary": summary,
            "failures": failures,
        }

    # 生成报告
    lines = []
    lines.append("# MultiHop-RAG Evaluation Report\n")

    # 1. Dataset
    total_count = 0
    for cd in configs_data.values():
        total_count = max(total_count, cd["summary"].get("count", 0))
    lines.append("## 1. Dataset\n")
    lines.append("- Dataset: MultiHop-RAG")
    lines.append(f"- Sample size: {total_count}")
    lines.append("- Task: multi-hop retrieval and QA")
    lines.append("- Corpus: MultiHop-RAG corpus")
    lines.append("")

    # 2. Compared Configs
    lines.append("## 2. Compared Configs\n")
    lines.append("| Config | Dense | BM25 | Graph | Repair |")
    lines.append("|---|---|---|---|---|")

    config_features = {
        "baseline_vector": (True, False, False, False),
        "hybrid": (True, True, False, False),
        "hybrid_graph": (True, True, True, False),
        "agentic_graph_repair": (True, True, True, True),
    }

    for config_name in configs_data:
        features = config_features.get(config_name, (True, False, False, False))
        d, b, g, r = features
        lines.append(f"| {config_name} | {'yes' if d else 'no'} | {'yes' if b else 'no'} | {'yes' if g else 'no'} | {'yes' if r else 'no'} |")
    lines.append("")

    # 3. Metrics
    lines.append("## 3. Metrics\n")
    lines.append("- Gold Doc Recall@10")
    lines.append("- All Gold Docs Hit@10")
    lines.append("- Gold Chunk Recall@10")
    lines.append("- Selected Evidence Recall")
    lines.append("- Avg Latency")
    lines.append("")

    # 4. Results
    lines.append("## 4. Results\n")
    lines.append("| Config | Gold Doc Recall@10 | All Gold Docs Hit@10 | Gold Chunk Recall@10 | Selected Evidence Recall | Avg Latency |")
    lines.append("|---|---:|---:|---:|---:|---:|")

    for config_name, cd in configs_data.items():
        s = cd["summary"]
        doc_recall = f"{s['gold_doc_recall@10']:.4f}" if s.get("gold_doc_recall@10") is not None else "N/A"
        all_hit = f"{s['all_gold_docs_hit@10']:.4f}" if s.get("all_gold_docs_hit@10") is not None else "N/A"
        chunk_recall = f"{s['gold_chunk_recall@10']:.4f}" if s.get("gold_chunk_recall@10") is not None else "N/A"
        ev_recall = f"{s['selected_evidence_recall']:.4f}" if s.get("selected_evidence_recall") is not None else "N/A"
        latency = f"{s['avg_latency_ms']:.0f}" if s.get("avg_latency_ms") is not None else "N/A"
        lines.append(f"| {config_name} | {doc_recall} | {all_hit} | {chunk_recall} | {ev_recall} | {latency} |")
    lines.append("")

    # 5. Findings
    lines.append("## 5. Findings\n")
    if len(configs_data) >= 2:
        names = list(configs_data.keys())
        s1 = configs_data[names[0]]["summary"]
        s2 = configs_data[names[-1]]["summary"]
        r1 = s1.get("gold_doc_recall@10", 0) or 0
        r2 = s2.get("gold_doc_recall@10", 0) or 0
        if r2 > r1:
            lines.append(f"1. {names[-1]} 的 Gold Doc Recall@10 ({r2:.4f}) 优于 {names[0]} ({r1:.4f})")
        else:
            lines.append(f"1. {names[0]} 的 Gold Doc Recall@10 ({r1:.4f}) 优于或等于 {names[-1]} ({r2:.4f})")
    else:
        lines.append("1. (需多组配置结果才能对比)")
    lines.append("")

    # 6. Failure Cases
    lines.append("## 6. Failure Cases\n")
    total_failures = 0
    for config_name, cd in configs_data.items():
        if cd["failures"]:
            lines.append(f"### {config_name}\n")
            for f in cd["failures"]:
                lines.append(f"- [{f['question_id']}] {f['question']}... (gold: {len(f['gold_doc_ids'])} docs)")
                total_failures += 1
            lines.append("")
    if total_failures == 0:
        lines.append("(无完全失败案例)")
        lines.append("")

    # 7. Conclusion
    lines.append("## 7. Conclusion\n")
    lines.append("- 第一版先跑 retrieval_only，验证检索质量。")
    lines.append("- 后续接入 full_qa 模式，评估完整 pipeline。")
    lines.append("")

    # 写入报告
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report_text = "\n".join(lines)
    output_path.write_text(report_text, encoding="utf-8")
    print(f"报告已生成: {output_path}")
    print(f"共 {len(configs_data)} 组配置, {total_failures} 个失败案例")


def main():
    parser = argparse.ArgumentParser(description="生成 MultiHop-RAG 评测报告")
    parser.add_argument("--inputs", nargs="+", required=True, help="results.jsonl 路径列表")
    parser.add_argument("--output", required=True, help="报告输出路径")
    args = parser.parse_args()

    input_paths = []
    for inp in args.inputs:
        p = Path(inp)
        if not p.is_absolute():
            p = PROJECT_ROOT / inp
        input_paths.append(p)

    out = Path(args.output)
    if not out.is_absolute():
        out = PROJECT_ROOT / args.output

    generate_report(input_paths, out)


if __name__ == "__main__":
    main()
