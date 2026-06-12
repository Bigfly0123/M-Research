# Phase 4 Human Audit Report

> 审计日期: 2026-06-12
> 样本数: 26 条 (TechDocQA 10 + GaRAGe 10 + Robustness 6)
> 审计文件: outputs/human_audit/phase4_human_audit_samples.jsonl

---

## 1. Audit Methodology

### 1.1 Sample Selection
- **TechDocQA**: 10 条随机抽样 (from 42 total)
- **GaRAGe**: 10 条随机抽样 (from 50 total)
- **Robustness**: 6 条 (out_of_domain 2 + insufficient_evidence 2 + citation_corruption 2)

### 1.2 Audit Fields

| Field | Scale | Description |
|---|---|---|
| answer_correctness | 0/1/2 | 0=wrong, 1=partial, 2=correct |
| citation_support | 0/1/2 | 0=no support, 1=partial, 2=full |
| answer_completeness | 0/1/2 | 0=incomplete, 1=partial, 2=complete |
| hallucination | bool | true if answer contains unsupported claims |
| error_type | enum | none / retrieval_missing / weak_citation / incomplete_answer / unsupported_claim / over_refusal / wrong_answer |

### 1.3 How to Audit

1. 打开 `outputs/human_audit/phase4_human_audit_samples.jsonl`
2. 对每条样本：
   - 阅读 question 和 answer
   - 检查 citations 是否实际支持答案中的声明
   - 填写 answer_correctness, citation_support, answer_completeness, hallucination, error_type
3. 汇总统计

---

## 2. Audit Results (TO BE FILLED)

### 2.1 Summary Statistics

| Metric | Value |
|---|---:|
| correct_or_partially_correct_rate | TBD |
| fully_supported_citation_rate | TBD |
| hallucination_rate | TBD |
| complete_answer_rate | TBD |

### 2.2 By Dataset

| Dataset | Samples | Avg Correctness | Avg Citation Support | Hallucination Rate |
|---|---:|---:|---:|---:|
| TechDocQA | 10 | TBD | TBD | TBD |
| GaRAGe | 10 | TBD | TBD | TBD |
| Robustness | 6 | TBD | TBD | TBD |

---

## 3. Typical Success Cases

### Case 1: (TBD after audit)
- **Question**: ...
- **Answer**: ...
- **Why it works**: ...

### Case 2: (TBD after audit)
- **Question**: ...
- **Answer**: ...
- **Why it works**: ...

### Case 3: (TBD after audit)
- **Question**: ...
- **Answer**: ...
- **Why it works**: ...

---

## 4. Typical Failure Cases

### Case 1: (TBD after audit)
- **Question**: ...
- **Problem**: ...
- **Root cause**: ...

### Case 2: (TBD after audit)
- **Question**: ...
- **Problem**: ...
- **Root cause**: ...

---

## 5. Audit Conclusion

(To be written after human audit is completed.)

Key questions:
- Are the automatic metrics (faithfulness, citation_precision) reliable?
- Do the answers actually help users understand the topic?
- Are there systematic failure modes not captured by automatic metrics?
