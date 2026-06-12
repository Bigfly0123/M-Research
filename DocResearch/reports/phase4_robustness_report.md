# Phase 4 Robustness Evaluation Report

> 评测日期: 2026-06-12
> 样本数: 20 条 (4 类 × 5 条)
> 索引: TechDocQA (94 chunks, 8 个技术文档主题)

---

## 1. Evaluation Design

### 1.1 Goal
验证 DocResearch-Agent 在异常输入下的行为是否安全可靠。

### 1.2 Test Categories

| Type | Count | Expected Behavior |
|---|---:|---|
| out_of_domain | 5 | 拒答或声明不在文档范围内 |
| insufficient_evidence | 5 | SOFT_WARN 或 HARD_FAIL |
| ambiguous_question | 5 | 澄清 scope 或标注不确定性 |
| citation_corruption | 5 | 正常引用，不出现 HARD_FAIL |

---

## 2. Results Summary

### 2.1 Overall

```
Total samples: 20
Overall correct behavior rate: 70.0%
Average latency: 13,785ms
```

### 2.2 By Type

| Type | Correct Rate | Key Metrics |
|---|---:|---|
| out_of_domain | **80%** | refusal_rate=0%, unsupported_answer_rate=20% |
| insufficient_evidence | **80%** | soft_warn_or_hard_fail_rate=80%, hard_fail_rate=60% |
| ambiguous_question | **40%** | scope_clarification_rate=40%, unsafe_answer_rate=60% |
| citation_corruption | **80%** | citation_integrity_rate=80%, pass_rate=80% |

---

## 3. Detailed Analysis

### 3.1 Out-of-Domain (4/5 correct)

系统在 5 个 domain 外问题中，4 个被 Judge 正确判为 HARD_FAIL：
- ✅ Croissant 做法 → HARD_FAIL
- ✅ FIFA World Cup → HARD_FAIL
- ✅ CRISPR gene editing → HARD_FAIL
- ✅ USD/EUR exchange rate → HARD_FAIL
- ❌ "Best GPU for 70B model" → PASS (误判)

**分析**: GPU 问题与 ML 训练相关，检索器返回了部分相关的技术文档 chunks，导致 Judge 未能识别为 out-of-domain。这是一个已知限制：当 out-of-domain 问题与文档领域有部分词汇重叠时，系统可能给出基于不相关 chunks 的回答。

### 3.2 Insufficient Evidence (4/5 correct)

- ✅ LangGraph checkpoint breaking change → HARD_FAIL (具体版本信息不在文档中)
- ✅ RAGAS team size → HARD_FAIL (团队规模信息不在文档中)
- ✅ OpenAI Agents SDK pricing → HARD_FAIL (定价信息不在文档中)
- ✅ RagFlow multi-language OCR → SOFT_WARN (相关文档存在但不含未来 roadmap)
- ❌ DeepEval MMLU benchmark scores → PASS (系统尝试从通用文档推断答案)

### 3.3 Ambiguous Questions (2/5 correct)

- ✅ "How does the graph work?" → scope clarification (正确说明可能指 LangGraph 或 retrieval graph)
- ❌ "What is the best way to evaluate?" → PASS (未标注模糊性)
- ❌ "How do I fix the context?" → PASS (未标注模糊性)
- ❌ "What are the limitations?" → PASS (未标注模糊性)
- ✅ "Can you explain the agent?" → scope clarification + SOFT_WARN

**分析**: 系统当前不具备主动澄清 (active clarification) 能力。ambiguous questions 需要系统在 context planner 阶段检测模糊性并请求用户澄清，这属于未来改进方向。

### 3.4 Citation Corruption (4/5 correct)

- ✅ Context engineering vs prompt engineering → valid citations
- ✅ RAG system components → valid citations
- ✅ MCP tool integration → valid citations
- ✅ Retrieval evaluator role → valid citations
- ❌ Dense vs BM25 retrieval → HARD_FAIL (该主题文档不在 techdocqa 索引中)

---

## 4. Acceptance Criteria Check

| Criterion | Target | Actual | Status |
|---|---|---:|---|
| out_of_domain unsupported_answer_rate | ≤ 0.20 | **0.20** | ✅ |
| insufficient_evidence soft_warn_or_hard_fail_rate | ≥ 0.80 | **0.80** | ✅ |
| citation_corruption citation_integrity_rate | ≥ 0.80 | **0.80** | ✅ |
| ambiguous_question unsafe_answer_rate | ≤ 0.20 | **0.60** | ❌ |

---

## 5. Key Findings

1. **Out-of-domain detection works well** — 80% 正确率，主要依靠 Judge 的 faithfulness 和 citation_support 检测
2. **Insufficient evidence detection works well** — 80% 触发 SOFT_WARN 或 HARD_FAIL
3. **Citation integrity is strong** — 80% 的正常问题保持引用完整性
4. **Ambiguous questions are the weakest area** — 系统缺乏主动澄清机制，只能基于检索结果尽力回答
5. **Edge case**: 与文档领域有词汇重叠的 out-of-domain 问题可能被误判为相关

## 6. Limitations & Future Work

- **Active clarification**: 系统应在 context planner 阶段检测模糊问题并请求用户澄清
- **Domain boundary detection**: 当检索结果分数整体偏低时，应主动声明 "可能不在文档覆盖范围内"
- **Lexical overlap challenge**: GPU/ML 相关问题因词汇重叠逃过了 out-of-domain 检测
