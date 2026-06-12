"""
Phase 4 Robustness Eval: 测试系统在异常输入下的行为。

用法:
  python eval/robustness_eval.py

测试类型:
  - out_of_domain: 系统应拒答或声明不在文档范围内
  - insufficient_evidence: 证据不足时应 warning 或 fail
  - ambiguous_question: 模糊问题应有 scope 说明或 clarification
  - citation_corruption: 正常问题，验证引用完整性

指标:
  - refusal_accuracy: out_of_domain 正确拒答率
  - unsupported_answer_rate: out_of_domain 给出无支持答案率
  - hard_fail_detection_rate: insufficient_evidence 检测率
  - soft_warn_or_hard_fail_rate: insufficient_evidence 触发 warning/fail 率
  - ambiguous_safe_answer_rate: ambiguous 不安全回答率
  - citation_integrity_rate: citation_corruption 引用完整率
"""

import json
import time
import sys
import os
from pathlib import Path
from typing import List, Dict

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


def build_initial_state(question: str) -> dict:
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
    }


def load_index(index_dir: str):
    """加载索引并设置全局 retriever。"""
    from app.retrieval.hybrid_retriever import HybridGraphRetriever
    from app import graph as graph_module

    retriever = HybridGraphRetriever()
    ok = retriever.load_index(str(PROJECT_ROOT / index_dir))
    if not ok:
        raise RuntimeError(f"无法加载索引: {index_dir}")
    print(f"  索引已加载: {len(retriever._chunks_by_id)} chunks")

    # 替换 graph.py 中的全局 retriever
    graph_module.retriever = retriever
    return retriever


def run_robustness_eval():
    """运行鲁棒性评测。"""
    eval_path = PROJECT_ROOT / "data" / "eval" / "robustness_eval.jsonl"
    eval_rows = load_jsonl(eval_path)
    print(f"鲁棒性评测: {len(eval_rows)} 条")

    # 使用 techdocqa 索引 (覆盖最多技术文档)
    index_dir = "data/indexes/techdocqa"
    load_index(index_dir)

    from app.graph import create_graph
    graph = create_graph()
    print(f"  Graph 构建完成\n")

    results = []
    for i, row in enumerate(eval_rows):
        question = row["question"]
        q_type = row["type"]
        q_id = row["id"]

        print(f"  [{i+1}/{len(eval_rows)}] {q_id} ({q_type}): {question[:60]}...")

        start = time.time()
        initial_state = build_initial_state(question)

        try:
            output_state = graph.invoke(initial_state)
        except Exception as e:
            print(f"    ERROR: {e}")
            results.append({
                "id": q_id,
                "type": q_type,
                "question": question,
                "error": str(e),
                "answer": "",
                "judge_decision": "ERROR",
                "guardrail_pass": False,
                "repair_count": 0,
                "latency_ms": int((time.time() - start) * 1000),
            })
            continue

        latency_ms = int((time.time() - start) * 1000)
        answer = output_state.get("answer", "")
        judge_result = output_state.get("judge_result", {})
        judge_decision = judge_result.get("decision", "PASS") if isinstance(judge_result, dict) else "PASS"
        guardrail_pass = output_state.get("guardrail_pass", True)
        repair_count = output_state.get("repair_count", 0)
        used_citations = output_state.get("used_citations", [])
        unsupported_claims = output_state.get("unsupported_claims", [])
        context_pack = output_state.get("context_pack", [])
        failure_type = output_state.get("failure_type", "")

        # 判断行为分类
        is_refusal = _is_refusal(answer)
        has_scope_clarification = _has_scope_clarification(answer)
        has_valid_citations = len(used_citations) > 0
        low_context = len(context_pack) < 3

        # 按类型判断正确行为
        if q_type == "out_of_domain":
            correct_behavior = is_refusal or judge_decision == "HARD_FAIL"
            behavior_label = "refuse" if is_refusal else ("hard_fail" if judge_decision == "HARD_FAIL" else "unsafe_answer")
        elif q_type == "insufficient_evidence":
            correct_behavior = judge_decision in ("SOFT_WARN", "HARD_FAIL")
            behavior_label = judge_decision.lower()
        elif q_type == "ambiguous_question":
            correct_behavior = has_scope_clarification or judge_decision in ("SOFT_WARN", "HARD_FAIL")
            behavior_label = "scope_clarify" if has_scope_clarification else judge_decision.lower()
        elif q_type == "citation_corruption":
            correct_behavior = has_valid_citations and judge_decision != "HARD_FAIL"
            behavior_label = "valid_citation" if has_valid_citations else "no_citation"
        else:
            correct_behavior = True
            behavior_label = "unknown"

        result = {
            "id": q_id,
            "type": q_type,
            "question": question,
            "answer": answer[:500] if answer else "",
            "answer_length": len(answer),
            "is_refusal": is_refusal,
            "has_scope_clarification": has_scope_clarification,
            "judge_decision": judge_decision,
            "guardrail_pass": guardrail_pass,
            "repair_count": repair_count,
            "used_citations": used_citations,
            "citation_count": len(used_citations),
            "unsupported_claims": unsupported_claims,
            "context_pack_size": len(context_pack),
            "failure_type": failure_type,
            "correct_behavior": correct_behavior,
            "behavior_label": behavior_label,
            "latency_ms": latency_ms,
            "expected_behavior": row.get("expected_behavior", ""),
            "note": row.get("note", ""),
        }
        results.append(result)
        print(f"    -> {behavior_label} (correct={correct_behavior}, judge={judge_decision}, latency={latency_ms}ms)")

    # 汇总统计
    n = len(results)
    type_groups = {}
    for r in results:
        t = r["type"]
        if t not in type_groups:
            type_groups[t] = []
        type_groups[t].append(r)

    summary = {"total": n, "by_type": {}}
    for q_type, group in type_groups.items():
        gn = len(group)
        correct_count = sum(1 for r in group if r["correct_behavior"])
        avg_latency = sum(r["latency_ms"] for r in group) / gn

        type_summary = {
            "count": gn,
            "correct_behavior_rate": round(correct_count / gn, 4) if gn else 0,
            "avg_latency_ms": round(avg_latency),
        }

        if q_type == "out_of_domain":
            refusal_count = sum(1 for r in group if r["is_refusal"])
            unsafe_count = sum(1 for r in group if not r["is_refusal"] and r["judge_decision"] != "HARD_FAIL")
            type_summary["refusal_rate"] = round(refusal_count / gn, 4) if gn else 0
            type_summary["unsupported_answer_rate"] = round(unsafe_count / gn, 4) if gn else 0
        elif q_type == "insufficient_evidence":
            sf_count = sum(1 for r in group if r["judge_decision"] in ("SOFT_WARN", "HARD_FAIL"))
            type_summary["soft_warn_or_hard_fail_rate"] = round(sf_count / gn, 4) if gn else 0
            hf_count = sum(1 for r in group if r["judge_decision"] == "HARD_FAIL")
            type_summary["hard_fail_detection_rate"] = round(hf_count / gn, 4) if gn else 0
        elif q_type == "ambiguous_question":
            scope_count = sum(1 for r in group if r["has_scope_clarification"])
            type_summary["scope_clarification_rate"] = round(scope_count / gn, 4) if gn else 0
            unsafe_count = sum(1 for r in group if not r["correct_behavior"])
            type_summary["unsafe_answer_rate"] = round(unsafe_count / gn, 4) if gn else 0
        elif q_type == "citation_corruption":
            valid_cite = sum(1 for r in group if r["citation_count"] > 0)
            type_summary["citation_integrity_rate"] = round(valid_cite / gn, 4) if gn else 0
            pass_count = sum(1 for r in group if r["judge_decision"] != "HARD_FAIL")
            type_summary["pass_rate"] = round(pass_count / gn, 4) if gn else 0

        summary["by_type"][q_type] = type_summary

    overall_correct = sum(1 for r in results if r["correct_behavior"])
    summary["overall_correct_behavior_rate"] = round(overall_correct / n, 4) if n else 0
    summary["avg_latency_ms"] = round(sum(r["latency_ms"] for r in results) / n) if n else 0

    # 保存
    out_dir = PROJECT_ROOT / "outputs" / "robustness"
    out_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(results, out_dir / "phase4_robustness_results.jsonl")

    summary_path = out_dir / "phase4_robustness_summary.json"
    with open(summary_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)

    # 打印汇总
    print("\n" + "=" * 60)
    print("Robustness Eval Summary")
    print("=" * 60)
    print(f"  Total: {n}")
    print(f"  Overall correct behavior: {summary['overall_correct_behavior_rate']:.2%}")
    print(f"  Avg latency: {summary['avg_latency_ms']}ms")
    print()
    for q_type, ts in summary["by_type"].items():
        print(f"  [{q_type}] ({ts['count']} samples)")
        for k, v in ts.items():
            if k != "count":
                print(f"    {k}: {v}")
        print()

    return summary


def _is_refusal(answer: str) -> bool:
    """判断答案是否为拒答。"""
    if not answer:
        return True
    refusal_keywords = [
        "i don't have", "i cannot", "not available", "not in the provided",
        "not covered", "outside the scope", "unable to answer",
        "no relevant", "not found in", "beyond the scope",
        "抱歉", "无法回答", "不在文档", "没有相关", "超出范围",
    ]
    answer_lower = answer.lower()
    return any(kw in answer_lower for kw in refusal_keywords)


def _has_scope_clarification(answer: str) -> bool:
    """判断答案是否包含 scope 说明或澄清。"""
    if not answer:
        return False
    scope_keywords = [
        "based on the available", "according to", "in the context of",
        "within the scope", "the documents cover", "based on the retrieved",
        "根据提供的文档", "在本文档范围内", "基于检索到的",
        "this could refer to", "depending on", "it depends",
    ]
    answer_lower = answer.lower()
    return any(kw in answer_lower for kw in scope_keywords)


if __name__ == "__main__":
    run_robustness_eval()
