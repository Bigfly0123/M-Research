# Final Evaluation Summary: DocResearch-Agent 2026

> 汇总日期: 2026-06-11 (Phase 5.1 Updated)
> 覆盖: Phase 1~5.1 所有评测结果

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

## 5. Human Audit (Phase 4 Audit + Phase 5 Fix)

### Overall Results

| Metric | Value |
|---|---:|
| Total samples | 26 |
| Avg correctness | 1.423 / 2 |
| Avg citation support | 1.769 / 2 |
| Avg completeness | 1.346 / 2 |
| Hallucination rate | **0.077 (7.7%)** |
| Perfect sample rate | 0.423 (42.3%) |

### By Dataset

| Dataset | n | Avg Correctness | Avg Citation Support | Hallucination Rate |
|---|---:|---:|---:|---:|
| TechDocQA | 10 | 1.5 | 1.9 | 0.1 |
| GaRAGe | 10 | 1.1 | 1.7 | 0.1 |
| Robustness (6 total) | 6 | 1.83 | 1.67 | 0.0 |

### Error Distribution

| Error Type | Count |
|---|---:|
| none (perfect) | 11 |
| truncated_answer | 7 |
| retrieval_missing_safe_refusal | 3 |
| other (5 types) | 5 |

### Phase 5 Truncation Fix

| Metric | Before (Audit) | After (Phase 5) |
|---|---:|---:|
| Truncation rate | 27% (7/26) | **0%** (verified on 5 cases) |
| Avg answer length | ~150 chars | **393 chars** |
| Code examples complete | No | **Yes** |

### Human Audit Conclusion

Human audit confirms that the system is generally well-grounded and rarely hallucinates. Citation support is strong (1.769/2). The main remaining issues are answer incompleteness caused by truncation (fixed in Phase 5) and retrieval-missing safe refusals on open-domain questions.

---

## 6. Full QA Ablation Study (Phase 5.1)

### TechDocQA (42 samples)

| Metric | Vanilla RAG | Hybrid RAG w/o Guardrails | Full System |
|---|---:|---:|---:|
| citation_precision | 0.9683 | 0.9735 | **0.9762** |
| faithfulness | 0.9881 | 0.9881 | 0.9821 |
| unsupported_claim_rate | 0.0119 | 0.0119 | 0.0179 |
| avg_answer_length | 318 | 354 | 334 |
| avg_latency_ms | 14,355 | 21,294 | 21,924 |

### GaRAGe (50 samples)

| Metric | Vanilla RAG | Hybrid RAG w/o Guardrails | Full System |
|---|---:|---:|---:|
| citation_precision | 0.0600 | 0.9800 | **1.0000** |
| faithfulness | 0.5300 | 0.9900 | **0.9900** |
| unsupported_claim_rate | 0.4700 | 0.0100 | **0.0100** |
| avg_answer_length | 321 | 521 | 542 |
| avg_latency_ms | 6,214 | 13,941 | 14,496 |

### Relative Improvement (Full System vs Vanilla RAG)

| Dataset | Metric | Δ (Absolute) | Δ (Relative) |
|---|---|---:|---:|
| TechDocQA | Citation Precision | +0.008 | +0.8% |
| GaRAGe | Citation Precision | +0.940 | +1567% |
| GaRAGe | Faithfulness | +0.460 | +87% |
| GaRAGe | Unsupported Claim Rate | -0.460 | -97.9% |

### Ablation Key Findings
1. TechDocQA 天花板效应：三种配置均表现优异（citation_precision > 0.96），dense retrieval 已能覆盖大部分正确上下文
2. GaRAGe 决定性提升：Vanilla RAG citation_precision=0.06 → Hybrid RAG=0.98 → Full System=1.00，证明 hybrid retrieval 是开放域 QA 的核心
3. Faithfulness 评分方法差异：Vanilla/Hybrid 使用 rule-based 近似，Full System 使用 LLM judge 实际打分
4. 综合结论：Hybrid retrieval 是 answer quality 的主要驱动力，guardrails/judge/repair 闭环提供引用校验和 failure detection

---

## 7. Final Verdict

DocResearch-Agent 2026 已完成从 "能检索" 到 "能引用、能审查、能修复、能安全失败" 的完整可靠性闭环。人工审计确认了自动指标的可信度，并在 Phase 5 修复了截断问题。

### Strengths
- **Faithfulness**: 0.97-0.99 (答案高度忠实于检索上下文)
- **Citation Precision**: 0.95-0.98 (引用几乎总是有效)
- **Guardrail Pass Rate**: 0.95-0.98 (Phase 3 校准后稳定)
- **Repair Efficiency**: avg_repair_count 0.06-0.12 (极少无效 repair)
- **Out-of-Domain Safety**: 80% 正确拒答
- **Human Audit Hallucination Rate**: 7.7% (人工确认低幻觉)
- **Human Audit Citation Support**: 1.769/2 (人工确认引用支持度)
- **Answer Completeness**: Phase 5 修复截断，验证 0% truncation

### Limitations
- **Ambiguous Questions**: 缺乏主动澄清机制 (40% correct) — known limitation, not to be fixed in this project
- **Citation Coverage**: 原始 coverage 偏低 (LLM 倾向于只引用 1-2 个 chunks)
- **Domain Boundary**: 与文档领域有词汇重叠的 OOD 问题可能逃过检测
- **Open-Domain Retrieval**: GaRAGe 上 30% 问题因检索缺失导致安全拒答（用户得不到答案，但也不会有幻觉）
