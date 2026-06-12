"""
Phase 4 人工审计样本生成脚本。
从 TechDocQA/GaRAGe/Robustness 结果中抽样，生成审计模板。
"""
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_jsonl(path):
    rows = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def sample_audit(rows, dataset, n):
    """从结果中抽样 n 条。"""
    import random
    random.seed(42)
    sampled = random.sample(rows, min(n, len(rows)))
    results = []
    for r in sampled:
        results.append({
            "dataset": dataset,
            "question_id": r.get("query_id", r.get("id", "")),
            "question": r.get("query", r.get("question", "")),
            "answer": r.get("answer", "")[:300],
            "citations": r.get("citations", r.get("used_citations", [])),
            "judge_decision": r.get("judge_result", {}).get("decision", "N/A") if isinstance(r.get("judge_result"), dict) else "N/A",
            "quality": {
                "citation_precision": r.get("quality", {}).get("citation_precision", 0),
                "faithfulness": r.get("quality", {}).get("faithfulness", 0),
            },
            "answer_correctness": None,
            "citation_support": None,
            "answer_completeness": None,
            "hallucination": None,
            "error_type": None,
            "human_note": "",
        })
    return results


def main():
    audit_samples = []

    # TechDocQA: 10 条
    techdoc_rows = load_jsonl(PROJECT_ROOT / "outputs" / "fullqa" / "techdocqa_hybrid_results.jsonl")
    audit_samples.extend(sample_audit(techdoc_rows, "techdocqa", 10))

    # GaRAGe: 10 条
    garage_rows = load_jsonl(PROJECT_ROOT / "outputs" / "fullqa" / "garage_hybrid_results.jsonl")
    audit_samples.extend(sample_audit(garage_rows, "garage", 10))

    # Robustness: 5 条 (每类 1-2 条)
    robust_rows = load_jsonl(PROJECT_ROOT / "outputs" / "robustness" / "phase4_robustness_results.jsonl")
    # 每类取 1-2 条
    by_type = {}
    for r in robust_rows:
        t = r["type"]
        if t not in by_type:
            by_type[t] = []
        by_type[t].append(r)
    for t in ["out_of_domain", "insufficient_evidence", "citation_corruption"]:
        if t in by_type:
            audit_samples.extend(sample_audit(by_type[t], f"robustness_{t}", 2))

    # 保存
    out_path = PROJECT_ROOT / "outputs" / "human_audit" / "phase4_human_audit_samples.jsonl"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        for s in audit_samples:
            f.write(json.dumps(s, ensure_ascii=False) + "\n")

    print(f"Generated {len(audit_samples)} audit samples -> {out_path}")
    print("\nAudit fields to fill:")
    print("  answer_correctness: 0=wrong, 1=partial, 2=correct")
    print("  citation_support:   0=no support, 1=partial, 2=full")
    print("  answer_completeness: 0=incomplete, 1=partial, 2=complete")
    print("  hallucination: true/false")
    print("  error_type: none/retrieval_missing/weak_citation/incomplete_answer/unsupported_claim/over_refusal/wrong_answer")


if __name__ == "__main__":
    main()
