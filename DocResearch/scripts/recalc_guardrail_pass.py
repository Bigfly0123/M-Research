"""快速重算 guardrail_pass_rate 基于 judge decision。"""
import json
from pathlib import Path

def analyze(path, label):
    rows = [json.loads(l) for l in open(path, "r", encoding="utf-8") if l.strip()]
    n = len(rows)
    pass_count = 0
    soft_count = 0
    hard_count = 0
    total_repair = 0
    total_latency = 0
    total_cp = 0
    total_cc = 0
    total_faith = 0
    total_has = 0
    
    for r in rows:
        jr = r.get("judge_result", {})
        dec = jr.get("decision", "PASS")
        if dec == "PASS":
            pass_count += 1
        elif dec == "SOFT_WARN":
            soft_count += 1
        else:
            hard_count += 1
        
        total_repair += r.get("repair_count", 0)
        m = r.get("metrics", {})
        total_latency += m.get("latency_ms", 0)
        q = r.get("quality", {})
        total_cp += q.get("citation_precision", 0)
        total_cc += q.get("citation_coverage", 0)
        total_faith += q.get("faithfulness", 0)
        total_has += int(q.get("has_answer", False))
    
    # guardrail_pass = PASS or SOFT_WARN (not HARD_FAIL)
    gpr = (pass_count + soft_count) / n if n else 0
    
    print(f"\n{'='*60}")
    print(f"  {label} (n={n})")
    print(f"{'='*60}")
    print(f"  PASS:        {pass_count} ({pass_count/n*100:.1f}%)")
    print(f"  SOFT_WARN:   {soft_count} ({soft_count/n*100:.1f}%)")
    print(f"  HARD_FAIL:   {hard_count} ({hard_count/n*100:.1f}%)")
    print(f"  guardrail_pass_rate (corrected): {gpr:.3f}")
    print(f"  avg_repair_count:     {total_repair/n:.2f}")
    print(f"  avg_latency_ms:       {total_latency/n:.0f}")
    print(f"  avg_citation_precision: {total_cp/n:.4f}")
    print(f"  avg_citation_coverage:  {total_cc/n:.4f}")
    print(f"  avg_faithfulness:       {total_faith/n:.4f}")
    print(f"  has_answer_rate:        {total_has/n:.3f}")

base = Path(r"e:\its4learning\IRIS\DocResearch\outputs\fullqa")
analyze(base / "techdocqa_hybrid_results.jsonl", "TechDocQA (Phase 3 Calibrated)")
analyze(base / "garage_hybrid_results.jsonl", "GaRAGe (Phase 3 Calibrated)")
