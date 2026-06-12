"""Quick analysis of primary_evidence_coverage."""
import json

rows = [json.loads(l) for l in open(
    'e:/its4learning/IRIS/DocResearch/outputs/fullqa/techdocqa_hybrid_results.jsonl',
    encoding='utf-8')]

cited_counts = [len(r.get('citations', [])) for r in rows]
print(f"Total rows: {len(rows)}")
print(f"Rows with 0 citations: {cited_counts.count(0)} / {len(rows)}")
print(f"Citation count distribution: {sorted(cited_counts)}")

# Show a few rows with citations
for r in rows:
    if r.get('citations'):
        print(f"\nSample with citations:")
        print(f"  citations: {r['citations'][:5]}")
        print(f"  primary_evidence_coverage: {r['quality'].get('primary_evidence_coverage', 'N/A')}")
        break

# Check how used_citations are extracted
print("\n--- Citation extraction debug ---")
r0 = rows[5]  # Pick a middle row
print(f"Answer (first 300 chars): {r0.get('answer','')[:300]}")
print(f"Citations: {r0.get('citations', [])}")
print(f"Quality: {json.dumps(r0.get('quality', {}), indent=2)}")
