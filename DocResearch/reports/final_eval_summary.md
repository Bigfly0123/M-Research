# Final Evaluation Summary: DocResearch-Agent 2026

> 汇总日期: 2026-06-12
> 覆盖: Phase 1~4 所有评测结果

---

## 1. Level 1 Retrieval Evaluation

| Dataset | Strategy | recall@10 | Best Config | Key Finding |
|---|---|---:|---|---|
| MultiHop-RAG | hybrid_graph | **0.813** | dense+bm25+graph_expand | Graph expansion 对多跳新闻检索最有效 |
| MultiHop-RAG | adaptive_hybrid | **0.802** | dynamic weights | 接近 hybrid_graph，无需手动选择 |
| StratRAG | dense_only | **0.900** | pure dense | 策略文档最适合 dense retrieval |
| StratRAG | adaptive_hybrid | **0.875** | dense_strong_bm25_weak | Phase 3 改进后提升 +3.5% |
| TechDocQA | adaptive_hybrid | **1.000** | saturated | 检索饱和，更适合 Full QA 评测 |
| GaRAGe | adaptive_hybrid | **1.000** | saturated | 检索饱和，适合 grounding 评测 |

### Level 1 Key Findings
1. Fixed hybrid + always-on graph 不是总有效
2. Reranker 可能带来负迁移，需通过 trace 定位
3. Adaptive hybrid 比固定策略更适合跨数据集使用
4. Graph expansion 适合 selective use，不适合 always-on

---

## 2. Level 2 Full QA Evaluation (Phase 4 Updated)

### TechDocQA (42 samples)

| Metric | Value |
|---|---:|
| has_answer_rate | 1.000 |
| avg_citation_precision | 0.952 |
| avg_citation_coverage | 0.158 |
| avg_primary_evidence_coverage | 0.210 |
| **has_primary_cited_rate** | **0.738** |
| avg_faithfulness | 0.988 |
| guardrail_pass_rate | 0.952 |
| avg_repair_count | 0.12 |
| avg_latency_ms | 16,449 |

### GaRAGe (50 samples)

| Metric | Value |
|---|---:|
| has_answer_rate | 1.000 |
| avg_citation_precision | 0.980 |
| avg_citation_coverage | 0.154 |
| avg_primary_evidence_coverage | 0.693 |
| **has_primary_cited_rate** | **0.980** |
| avg_faithfulness | 0.970 |
| guardrail_pass_rate | 0.980 |
| avg_repair_count | 0.06 |
| avg_latency_ms | 11,603 |

### Level 2 Key Findings
1. Faithfulness 极高 (0.97-0.99)，答案几乎总是被 context 支持
2. Citation precision 极高 (0.95-0.98)，引用几乎总是有效
3. primary_evidence_coverage 偏低 (0.21-0.69)，因为 LLM 每条答案只引用 1-2 个 chunks
4. has_primary_cited_rate 更有意义：GaRAGe 0.98，TechDocQA 0.74

---

## 3. Reliability Calibration (Phase 3)

| Metric | Before (Phase 2) | After (Phase 3) | Change |
|---|---:|---:|---|
| TechDocQA guardrail_pass_rate | 0.000 | 0.952 | **+0.952** |
| TechDocQA avg_repair_count | 2.000 | 0.12 | **-1.88** |
| TechDocQA avg_latency_ms | 22,100 | 16,449 | **-5,651** |
| TechDocQA citation_precision | 0.929 | 0.952 | +0.023 |
| TechDocQA faithfulness | 1.000 | 0.988 | -0.012 |

### Phase 3 Key Fixes
1. **CITATION_PATTERN 正则修复**: `[D\d+-C\d+]` → `[.+?-s\d+-c\d+]`
2. **三层 Judge 决策**: PASS / SOFT_WARN / HARD_FAIL，只有 HARD_FAIL 触发 repair
3. **Repair Router 校准**: SOFT_WARN/PASS 直接返回 end
4. **Evidence Tier 分层**: primary / supporting / context_only

---

## 4. Robustness Evaluation (Phase 4)

| Test Type | Samples | Correct Rate | Key Metric | Value |
|---|---:|---:|---|---:|
| out_of_domain | 5 | 80% | unsupported_answer_rate | 0.20 |
| insufficient_evidence | 5 | 80% | soft_warn_or_hard_fail_rate | 0.80 |
| ambiguous_question | 5 | 40% | unsafe_answer_rate | 0.60 |
| citation_corruption | 5 | 80% | citation_integrity_rate | 0.80 |

### Robustness Key Findings
1. Out-of-domain 检测 80% 正确（依赖 Judge faithfulness 检测）
2. Insufficient evidence 检测 80% 正确
3. Citation integrity 80%（正常问题保持引用完整）
4. Ambiguous questions 是弱项（缺乏主动澄清机制）

---

## 5. Human Audit (Phase 4)

| Status | Details |
|---|---|
| Samples prepared | 26 (TechDocQA 10 + GaRAGe 10 + Robustness 6) |
| Audit file | outputs/human_audit/phase4_human_audit_samples.jsonl |
| Status | **Pending human review** |
| Report | reports/phase4_human_audit_report.md |

---

## 6. Final Verdict

DocResearch-Agent 2026 已完成从 "能检索" 到 "能引用、能审查、能修复、能安全失败" 的完整可靠性闭环。

### Strengths
- **Faithfulness**: 0.97-0.99 (答案高度忠实于检索上下文)
- **Citation Precision**: 0.95-0.98 (引用几乎总是有效)
- **Guardrail Pass Rate**: 0.95-0.98 (Phase 3 校准后稳定)
- **Repair Efficiency**: avg_repair_count 0.06-0.12 (极少无效 repair)
- **Out-of-Domain Safety**: 80% 正确拒答

### Limitations
- **Ambiguous Questions**: 缺乏主动澄清机制 (40% correct)
- **Citation Coverage**: 原始 coverage 偏低 (LLM 倾向于只引用 1-2 个 chunks)
- **Domain Boundary**: 与文档领域有词汇重叠的 OOD 问题可能逃过检测
