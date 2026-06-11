"""
Level 1 Retrieval Diagnosis Script (Phase 2.1)

分析 MultiHop-RAG 和 StratRAG 的检索失败案例，
生成 level1_retrieval_diagnosis.md 诊断报告。
"""
import json
import sys
from pathlib import Path
from collections import Counter, defaultdict

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def load_jsonl(path: Path) -> list:
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def analyze_multihop_failures():
    """分析 MultiHop-RAG 上 hybrid 退化案例。"""
    report_dir = PROJECT_ROOT / "reports" / "multihop_rag"

    bm25_results = load_jsonl(report_dir / "bm25_only_results.jsonl")
    dense_results = load_jsonl(report_dir / "dense_only_results.jsonl")
    hybrid_results = load_jsonl(report_dir / "hybrid_results.jsonl")
    hybrid_graph_results = load_jsonl(report_dir / "hybrid_graph_results.jsonl")

    # 按 question_id 索引
    bm25_by_id = {r["question_id"]: r for r in bm25_results}
    dense_by_id = {r["question_id"]: r for r in dense_results}
    hg_by_id = {r["question_id"]: r for r in hybrid_graph_results}

    failure_cases = []
    bm25_better = []
    hybrid_better = []
    both_equal = []

    for hr in hybrid_results:
        qid = hr["question_id"]
        bm25_r = bm25_by_id.get(qid, {})
        dense_r = dense_by_id.get(qid, {})
        hg_r = hg_by_id.get(qid, {})

        bm25_r10 = bm25_r.get("metrics", {}).get("gold_doc_recall@10", 0)
        dense_r10 = dense_r.get("metrics", {}).get("gold_doc_recall@10", 0)
        hybrid_r10 = hr.get("metrics", {}).get("gold_doc_recall@10", 0)
        hg_r10 = hg_r.get("metrics", {}).get("gold_doc_recall@10", 0)

        bm25_hit = bm25_r.get("metrics", {}).get("all_gold_hit@10", 0)
        hybrid_hit = hr.get("metrics", {}).get("all_gold_hit@10", 0)

        # 诊断 failure_type
        failure_type = None
        if bm25_r10 > hybrid_r10:
            failure_type = "hybrid_fusion_dilution"
            bm25_better.append(qid)
            # 进一步分类
            if dense_r10 < bm25_r10 and dense_r10 < hybrid_r10:
                failure_type = "bm25_strong_dense_noise"
            elif dense_r10 == hybrid_r10:
                failure_type = "hybrid_fusion_dilution"
        elif hybrid_r10 > bm25_r10:
            failure_type = None
            hybrid_better.append(qid)
        else:
            both_equal.append(qid)

        if hg_r10 < hybrid_r10:
            if failure_type is None:
                failure_type = "graph_expansion_noise"
            else:
                failure_type += "+graph_expansion_noise"

        failure_cases.append({
            "query_id": qid,
            "query": hr["question"][:120],
            "gold_doc_ids": hr.get("gold_doc_ids", []),
            "bm25_r10": round(bm25_r10, 3),
            "dense_r10": round(dense_r10, 3),
            "hybrid_r10": round(hybrid_r10, 3),
            "hybrid_graph_r10": round(hg_r10, 3),
            "bm25_all_hit": bm25_hit,
            "hybrid_all_hit": hybrid_hit,
            "bm25_retrieved": bm25_r.get("retrieved_doc_ids", [])[:10],
            "dense_retrieved": dense_r.get("retrieved_doc_ids", [])[:10],
            "hybrid_retrieved": hr.get("retrieved_doc_ids", [])[:10],
            "failure_type": failure_type or "no_failure",
        })

    return failure_cases, bm25_better, hybrid_better, both_equal


def analyze_adaptive_results():
    """分析 adaptive_hybrid 与 bm25_only 的对比。"""
    report_dir = PROJECT_ROOT / "reports" / "multihop_rag"

    bm25_path = report_dir / "bm25_only_results.jsonl"
    adaptive_path = report_dir / "adaptive_hybrid_results.jsonl"

    if not adaptive_path.exists():
        return None

    bm25_results = load_jsonl(bm25_path)
    adaptive_results = load_jsonl(adaptive_path)

    bm25_by_id = {r["question_id"]: r for r in bm25_results}

    adaptive_wins = 0
    adaptive_loses = 0
    adaptive_ties = 0
    strategy_dist = Counter()
    adaptive_details = []

    for ar in adaptive_results:
        qid = ar["question_id"]
        bm25_r = bm25_by_id.get(qid, {})

        bm25_r10 = bm25_r.get("metrics", {}).get("gold_doc_recall@10", 0)
        adaptive_r10 = ar.get("metrics", {}).get("gold_doc_recall@10", 0)

        if adaptive_r10 > bm25_r10:
            adaptive_wins += 1
        elif adaptive_r10 < bm25_r10:
            adaptive_loses += 1
        else:
            adaptive_ties += 1

        adaptive_details.append({
            "query_id": qid,
            "query": ar["question"][:100],
            "bm25_r10": round(bm25_r10, 3),
            "adaptive_r10": round(adaptive_r10, 3),
            "diff": round(adaptive_r10 - bm25_r10, 3),
        })

    return {
        "wins": adaptive_wins,
        "loses": adaptive_loses,
        "ties": adaptive_ties,
        "details": adaptive_details,
    }


def generate_diagnosis_report():
    """生成 level1_retrieval_diagnosis.md。"""
    failure_cases, bm25_better, hybrid_better, both_equal = analyze_multihop_failures()
    adaptive_info = analyze_adaptive_results()

    # 统计 failure types
    failure_types = Counter(c["failure_type"] for c in failure_cases if c["failure_type"] != "no_failure")

    # 统计 all_gold_hit
    bm25_all_hit = sum(1 for c in failure_cases if c["bm25_all_hit"] == 1)
    hybrid_all_hit = sum(1 for c in failure_cases if c["hybrid_all_hit"] == 1)

    lines = []
    lines.append("# Level 1 Retrieval Diagnosis Report")
    lines.append("")
    lines.append("> Phase 2.1 诊断报告：分析 MultiHop-RAG 上 hybrid 退化和 graph 无增益的根因。")
    lines.append("")
    lines.append("## 1. MultiHop-RAG Hybrid 退化分析")
    lines.append("")
    lines.append("### 1.1 总体统计")
    lines.append("")
    lines.append(f"- 总评测样本: {len(failure_cases)}")
    lines.append(f"- BM25 优于 Hybrid: **{len(bm25_better)} 条** ({len(bm25_better)/len(failure_cases)*100:.1f}%)")
    lines.append(f"- Hybrid 优于 BM25: **{len(hybrid_better)} 条** ({len(hybrid_better)/len(failure_cases)*100:.1f}%)")
    lines.append(f"- 两者相同: **{len(both_equal)} 条** ({len(both_equal)/len(failure_cases)*100:.1f}%)")
    lines.append("")
    lines.append("### 1.2 all_gold_hit@10 统计")
    lines.append("")
    lines.append(f"- BM25 all_gold_hit@10: {bm25_all_hit}/100 = {bm25_all_hit/100*100:.1f}%")
    lines.append(f"- Hybrid all_gold_hit@10: {hybrid_all_hit}/100 = {hybrid_all_hit/100*100:.1f}%")
    lines.append("")
    lines.append("### 1.3 退化原因分类")
    lines.append("")
    lines.append("| 退化类型 | 数量 | 占比 |")
    lines.append("|---|---:|---:|")
    for ft, cnt in failure_types.most_common():
        lines.append(f"| {ft} | {cnt} | {cnt/len(failure_cases)*100:.1f}% |")
    lines.append("")

    lines.append("### 1.4 核心发现")
    lines.append("")
    lines.append("1. **BM25 在 MultiHop-RAG 上是最强单路检索器**。BM25 的 recall@10 显著高于 Dense，")
    lines.append("   说明在英文新闻文本上，关键词精确匹配比语义向量检索更有效。")
    lines.append("")
    lines.append("2. **Hybrid 退化主要来自 Dense 噪声稀释 BM25 信号**。")
    lines.append("   当 BM25 找到正确文档但 Dense 返回无关文档时，固定权重的 RRF 融合")
    lines.append("   会将 Dense 的噪声文档提升到 BM25 的高质量文档之前。")
    lines.append("")
    lines.append("3. **Graph expansion 对新闻文本无效**。")
    lines.append("   当前术语抽取规则 (CamelCase, snake_case, 技术白名单) 面向技术文档设计，")
    lines.append("   对英文新闻文本几乎抽不出有效术语，导致 graph 路无贡献。")
    lines.append("")

    lines.append("### 1.5 典型案例")
    lines.append("")

    # 找 3 个退化案例
    regression_cases = [c for c in failure_cases if c["failure_type"] != "no_failure"][:5]
    for i, c in enumerate(regression_cases):
        lines.append(f"#### 案例 {i+1}: {c['query_id']}")
        lines.append(f"- Query: {c['query']}...")
        lines.append(f"- Gold: {c['gold_doc_ids']}")
        lines.append(f"- BM25 recall@10: {c['bm25_r10']} | Dense: {c['dense_r10']} | Hybrid: {c['hybrid_r10']} | Hybrid+Graph: {c['hybrid_graph_r10']}")
        lines.append(f"- Failure type: `{c['failure_type']}`")
        lines.append(f"- BM25 top3: {c['bm25_retrieved'][:3]}")
        lines.append(f"- Hybrid top3: {c['hybrid_retrieved'][:3]}")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 2. Adaptive Hybrid 效果")
    lines.append("")

    if adaptive_info:
        lines.append(f"- Adaptive 优于 BM25: **{adaptive_info['wins']} 条**")
        lines.append(f"- Adaptive 劣于 BM25: **{adaptive_info['loses']} 条**")
        lines.append(f"- 两者相同: **{adaptive_info['ties']} 条**")
        lines.append("")

        # 找 adaptive 退化案例
        regression = [d for d in adaptive_info["details"] if d["diff"] < 0]
        if regression:
            lines.append("### 2.1 Adaptive 退化案例")
            lines.append("")
            for d in regression[:5]:
                lines.append(f"- {d['query_id']}: BM25={d['bm25_r10']}, Adaptive={d['adaptive_r10']}, diff={d['diff']}")
                lines.append(f"  - Query: {d['query']}...")
            lines.append("")
    else:
        lines.append("Adaptive hybrid 结果尚未生成，请先运行 eval。")
        lines.append("")

    lines.append("---")
    lines.append("")
    lines.append("## 3. 结论与改进方向")
    lines.append("")
    lines.append("1. **修复 RRF 融合**: 使用无权重标准 RRF 或让 BM25 权重 >= Dense 权重。")
    lines.append("2. **默认关闭 Reranker**: 在 eval 中 reranker 不带来稳定提升。")
    lines.append("3. **Graph 路对新闻文本无效**: 需要使用 NER 或 LLM 实体抽取替代技术术语规则。")
    lines.append("4. **Adaptive hybrid 应至少不低于 BM25**: 通过 query 分析和置信信号动态选择融合权重。")
    lines.append("")

    return "\n".join(lines)


if __name__ == "__main__":
    report = generate_diagnosis_report()

    out_path = PROJECT_ROOT / "reports" / "level1_retrieval_diagnosis.md"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(report)
    print(f"Diagnosis report written to: {out_path}")
    print("\n" + "=" * 60)
    print(report[:2000])
