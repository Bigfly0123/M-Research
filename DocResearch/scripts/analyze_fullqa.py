"""Analyze Full QA results."""
import json
from collections import Counter

results = []
with open("outputs/fullqa/techdocqa_hybrid_results.jsonl", "r", encoding="utf-8") as f:
    for line in f:
        results.append(json.loads(line))

failures = Counter()
has_citation = 0
total_citations = 0
recall_hits = 0
for r in results:
    failures[r.get("failure_type", "")] += 1
    if r.get("citations"):
        has_citation += 1
        total_citations += len(r.get("citations", []))
    if r.get("retrieval_recall", 0) > 0:
        recall_hits += 1

print(f"Total: {len(results)}")
print(f"Recall > 0: {recall_hits}/{len(results)} ({recall_hits/len(results)*100:.1f}%)")
print(f"Failure types:")
for ft, cnt in failures.most_common():
    print(f"  {ft}: {cnt} ({cnt/len(results)*100:.1f}%)")
print(f"Has citations: {has_citation}/{len(results)} ({has_citation/len(results)*100:.1f}%)")
print(f"Avg citations/sample: {total_citations/max(len(results),1):.2f}")

recalls = [r.get("retrieval_recall", 0) for r in results]
avg_recall = sum(recalls) / len(recalls)
print(f"\nAvg retrieval recall: {avg_recall:.4f}")
print(f"Recall=1.0: {sum(1 for r in recalls if r==1.0)}")
print(f"Recall=0.0: {sum(1 for r in recalls if r==0.0)}")

print(f"\nSample details (first 5):")
for r in results[:5]:
    q = r.get("query", "")[:70]
    gr = r.get("guardrail_result", {})
    jr = r.get("judge_result", {})
    print(f"  Q: {q}...")
    print(f"    judge_pass={jr.get('pass_')}, failure={r.get('failure_type')}, repair={r.get('repair_count')}")
    print(f"    recall={r.get('retrieval_recall')}, citations={len(r.get('citations', []))}")
    print(f"    answer: {r.get('answer', '')[:100]}")
    print(f"    judge: relevance={jr.get('answer_relevance',0):.2f}, support={jr.get('citation_support',0):.2f}, faith={jr.get('faithfulness',0):.2f}, sufficiency={jr.get('context_sufficiency',0):.2f}")
    print()
