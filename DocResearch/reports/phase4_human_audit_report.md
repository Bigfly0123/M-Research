# Phase 4 Human Audit Report (Completed)

> 审计日期: 2026-06-12
> 样本数: 26 条 (TechDocQA 10 + GaRAGe 10 + Robustness 6)
> 审计文件: outputs/human_audit/phase4_human_audit_completed.jsonl
> 状态: **COMPLETED**

---

## 1. Audit Methodology

### 1.1 Sample Selection
- **TechDocQA**: 10 条随机抽样 (from 42 total)
- **GaRAGe**: 10 条随机抽样 (from 50 total)
- **Robustness**: 6 条 (out_of_domain 2 + insufficient_evidence 2 + citation_corruption 2)

### 1.2 Scoring Rubric

| Field | 2 | 1 | 0 |
|---|---|---|---|
| answer_correctness | correct / safe refusal when evidence insufficient | partially correct or safe but non-answer | incorrect or misleading |
| citation_support | citations adequately support main answer | weak/partial/irrelevant citation support | unsupported or missing when required |
| answer_completeness | fully answers the question or appropriately refuses | incomplete/truncated/partial answer | does not answer the requested question |
| hallucination | 0 = none | 1 = minor unsupported claim | 2 = clear unsupported/incorrect claim |

---

## 2. Audit Results

### 2.1 Overall Metrics

| Metric | Value |
|---|---:|
| Total samples | 26 |
| Avg correctness | **1.423 / 2** |
| Avg citation support | **1.769 / 2** |
| Avg completeness | **1.346 / 2** |
| Hallucination rate | **0.077 (7.7%)** |
| Perfect sample rate | **0.423 (42.3%)** |

### 2.2 By Dataset

| Dataset | n | Avg Correctness | Avg Citation Support | Avg Completeness | Hallucination Rate | Perfect Rate |
|---|---:|---:|---:|---:|---:|---:|
| TechDocQA | 10 | 1.5 | 1.9 | 1.5 | 0.1 | 0.5 |
| GaRAGe | 10 | 1.1 | 1.7 | 0.9 | 0.1 | 0.2 |
| Robustness OOD | 2 | 2.0 | 1.5 | 2.0 | 0.0 | 0.5 |
| Robustness Insufficient | 2 | 2.0 | 2.0 | 2.0 | 0.0 | 1.0 |
| Robustness Citation Corruption | 2 | 1.5 | 1.5 | 1.5 | 0.0 | 0.5 |

### 2.3 Error Type Distribution

| Error Type | Count | Description |
|---|---:|---|
| none | 11 | 完全正常，无任何问题 |
| truncated_answer | 7 | 答案被截断（主要影响完整性） |
| retrieval_missing_safe_refusal | 3 | 检索缺失导致安全拒答 |
| weak_citation_or_cross_metric_confusion | 1 | 弱引用或跨指标混淆 |
| incomplete_answer | 1 | 答案不完整 |
| partial_answer_missing_comparison | 1 | 部分答案缺少比较 |
| unsupported_claim_or_entity_confusion | 1 | 无支持声明或实体混淆 |
| minor_irrelevant_citation | 1 | 轻微无关引用 |

---

## 3. Key Findings

### 3.1 Strengths
1. **幻觉率极低 (7.7%)** — 系统在绝大多数情况下不会编造无依据信息
2. **引用支持度高 (1.769/2)** — 答案中的引用通常能有效支持核心声明
3. **安全拒答行为可靠** — OOD 和 insufficient evidence 场景下正确拒绝回答
4. **TechDocQA 正确率较高** — 10 条中 5 条完美 (correctness=2, citation=2, completeness=2)

### 3.2 Issues
1. **Answer Truncation** (7 cases, 27%) — 代码/步骤类答案被截断，主要影响 completeness
   - **Root cause identified**: eval 脚本保存答案时 `answer[:500]` 截断到 500 字符
   - **Fixed in Phase 5**: 移除截断 + LLM max_tokens 提高到 4096
   - **Verification**: 5 条截断问题重测，全部完整输出，0/5 truncated

2. **GaRAGe retrieval mismatch** (3 cases) — 开放域问题检索不到相关文档，导致安全拒答
   - 这不是幻觉问题，而是检索覆盖不足
   - 系统正确地选择了拒答而非编造，但用户没有得到答案

3. **Entity confusion** (1 case) — GaRAGe q_34 把女足 Aitana Bonmatí 关联到 UEFA Euro 2024 男足夺冠
   - 孤立事件，但说明 entity disambiguation 仍是开放域 RAG 的挑战

### 3.3 Phase 5 Fix Impact

| Issue | Before (Audit) | After (Phase 5 Fix) |
|---|---|---|
| Truncation rate | 27% (7/26) | **0%** (verified on 5 truncation cases) |
| Avg answer length (code questions) | ~150 chars | **393 chars** (avg of 5 test cases) |
| Code examples | Incomplete (cut at import/def) | Complete with full code blocks |

---

## 4. Typical Success Cases

### Case 1: TechDocQA — G-Eval 自定义指标
- **Question**: DeepEval 中 G-Eval 的作用是什么？
- **Correctness**: 2/2 | **Citation**: 2/2 | **Completeness**: 2/2
- **Why it works**: 直接引用两个相关 chunk，准确解释 G-Eval 框架用途

### Case 2: Robustness — OOD 安全拒答
- **Question**: What is the current exchange rate between USD and EUR?
- **Correctness**: 2/2 | **Citation**: 2/2 | **Completeness**: 2/2
- **Why it works**: 系统正确识别无相关信息，直接拒答且不编造

### Case 3: TechDocQA — LangGraph retriever_tool
- **Question**: 在 LangGraph Agentic RAG 中，retriever_tool 的作用是什么？
- **Correctness**: 2/2 | **Citation**: 2/2 | **Completeness**: 2/2
- **Why it works**: 准确描述工具功能（包括无结果返回逻辑），引用精确

---

## 5. Typical Failure Cases

### Case 1: GaRAGe — Entity Confusion (q_34)
- **Question**: What factors contributed to Spain's victory in UEFA Euro 2024?
- **Problem**: 把女足 Aitana Bonmatí 关联到男足 Euro 2024，hallucination=2
- **Root cause**: 检索返回了女足相关文档，LLM 未区分性别语境

### Case 2: GaRAGe — Retrieval Missing (q_7, q_15, q_5)
- **Question**: 名人出席 / MariMed 专利 / GHG 法规
- **Problem**: 安全拒答 (correctness=1)，但没有回答原问题
- **Root cause**: 开放域问题超出索引覆盖范围

---

## 6. Audit Conclusion

**English**:
Human audit confirms that the system is generally well-grounded and rarely hallucinates (7.7% hallucination rate). The main remaining issues are answer incompleteness caused by truncation (fixed in Phase 5) and retrieval-missing safe refusals on open-domain GaRAGe-style questions. Citation support is strong (1.769/2), indicating the guardrails and evidence composer work as designed.

**中文**:
人工审计表明，系统整体具备较好的证据约束能力，幻觉率较低（7.7%）；引用支持度较高（1.769/2），说明 guardrails 和 evidence composer 按设计工作。剩余问题主要集中在：(1) 生成完整性——审计中发现 27% 的答案被截断，已在 Phase 5 修复并验证；(2) 开放域检索覆盖——GaRAGe 上 3 条因检索缺失导致安全拒答。这些问题不影响系统的引用真实性或审查机制有效性。

---

## 7. Recommendations for Future Work

1. **Do NOT add clarification agent** for ambiguous questions (keep as known limitation)
2. **Consider answer length monitoring** in production to detect truncation at runtime
3. **Improve retrieval coverage** for open-domain questions (multi-index or web retrieval)
4. **Entity disambiguation** could be added as a lightweight pre-processing step
