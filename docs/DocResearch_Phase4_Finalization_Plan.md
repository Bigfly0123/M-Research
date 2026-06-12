# DocResearch-Agent Phase 4 规划：Finalization, Robustness Audit & Demo Packaging

> 项目：DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统  
> 当前阶段：Phase 4  
> 上一阶段状态：Phase 3 Reliability Calibration 已完成  
> 本阶段目标：不再继续堆模块，而是完成项目收口、鲁棒性验证、人工审计、展示包装与最终报告。

---

## 1. 当前项目状态总结

Phase 3 已经完成了核心可靠性校准，说明系统已经从“能检索、能回答”推进到“能引用、能审查、能修复、能稳定输出”的阶段。

### 1.1 Phase 3 已完成成果

| 方向 | 当前结果 |
|---|---|
| TechDocQA Full QA | guardrail_pass_rate 从 0.000 提升到 0.976 |
| Repair 控制 | avg_repair_count 从 2.000 降到 0.07 |
| Citation | TechDocQA citation_precision = 0.976 |
| Faithfulness | TechDocQA faithfulness = 1.000 |
| GaRAGe Full QA | citation_precision = 1.000，faithfulness = 0.970 |
| Retrieval 回归 | MultiHop-RAG adaptive r@10 无退化，StratRAG adaptive r@10 提升到 0.875 |
| README 展示 | 根 README 已从 IRIS 改为 DocResearch-Agent 主项目 |

### 1.2 当前阶段判断

当前不建议继续大幅修改核心框架。项目已经具备完整结构：

```text
Context Planner
→ Adaptive Hybrid Retrieval
→ Selective Graph Expansion
→ Retrieval Evaluator
→ Evidence Composer
→ Grounded Answer Generator
→ Citation Guardrails
→ Self-Reflection Judge
→ Repair Router
```

下一阶段重点不是“再加一个模块”，而是让项目变成：

```text
可复现
可展示
可解释
可审计
可写进简历
可在面试中讲清楚
```

---

## 2. Phase 4 总目标

Phase 4 的目标是完成项目收口与展示包装。

本阶段命名为：

```text
Phase 4：Finalization, Robustness Audit & Demo Packaging
```

核心目标包括：

1. 固化 Phase 1～3 的实验结论。
2. 补充人工审计，避免自动指标过于乐观。
3. 增加鲁棒性评测，证明系统面对无证据、错误引用、模糊问题时不会胡答。
4. 改进 citation coverage 指标，使其与 evidence tier 对齐。
5. 整理 GitHub README、报告、demo cases，使项目能直接展示。
6. 输出 final project report 和简历描述。

---

## 3. Phase 4 不做什么

本阶段明确禁止继续发散。

不要做：

```text
不要继续新增 agent
不要继续复杂化 GraphRAG
不要引入新的大型 KG 构建流程
不要继续扩大数据集到几千条
不要为了提升 1～2 个点反复调 retrieval
不要把 Phase 4 变成新一轮架构重构
不要把项目重新变成普通 RAG benchmark 项目
```

Phase 4 的关键词是：

```text
收口、审计、展示、复现、包装
```

---

## 4. 任务一：整理最终项目结构与 README

### 4.1 目标

确保仓库首页打开后，第一眼看到的是 DocResearch-Agent，而不是 IRIS 或其他历史项目。

### 4.2 检查内容

检查根目录 README 是否包含以下内容：

```text
1. 项目名称：DocResearch-Agent 2026
2. 项目一句话定位
3. 为什么不是普通 RAG
4. 系统架构图或流程图
5. 核心模块说明
6. Level 1 Retrieval Eval 结果摘要
7. Level 2 Full QA 结果摘要
8. Phase 3 Reliability Calibration 结果摘要
9. Quick Start
10. Demo Cases
11. 项目目录结构
12. Key Findings
```

### 4.3 README 建议结构

```markdown
# DocResearch-Agent 2026

## Overview
## Why Not Vanilla RAG
## System Architecture
## Key Features
## Evaluation Results
### Level 1: Retrieval Evaluation
### Level 2: Full QA Reliability Evaluation
### Phase 3: Reliability Calibration
## Demo Cases
## Quick Start
## Project Structure
## Key Findings
## Limitations
## Roadmap
```

### 4.4 验收标准

```text
打开 GitHub 根目录，第一屏能看懂：
这是一个技术文档可靠问答 Agent，不是 IRIS，不是普通 RAG。
```

---

## 5. 任务二：Phase 3 报告格式整理

### 5.1 目标

将 Phase 3 报告整理成适合 GitHub 阅读和面试展示的格式。

当前报告内容已经有价值，但需要保证：

```text
标题清楚
表格清楚
段落不要过长
结论突出
失败原因和修复逻辑明确
```

### 5.2 建议整理文件

```text
DocResearch/reports/docresearch_phase3_reliability_report.md
```

### 5.3 报告建议结构

```markdown
# Phase 3 Reliability Calibration Report

## 1. Background
## 2. Phase 2 Problems
## 3. Root Cause Analysis
## 4. Key Fixes
## 5. TechDocQA Full QA Results
## 6. GaRAGe Full QA Results
## 7. Retrieval Regression Check
## 8. Ablation / Before-After Comparison
## 9. Remaining Limitations
## 10. Conclusion
```

### 5.4 必须强调的结论

报告里要明确写：

```text
Phase 2 的问题不是答案质量差，而是 Judge/Guardrails 过严和 citation pattern 不匹配。
Phase 3 通过三层 Judge 决策、Guardrail 正则修复、Repair Router 校准和 Evidence Tier 分层解决了无效 repair 问题。
```

### 5.5 验收标准

```text
报告可以被直接放进 GitHub / 简历项目说明中。
读者可以在 3 分钟内看明白：问题是什么、怎么修、修完有什么效果。
```

---

## 6. 任务三：新增 primary_evidence_coverage 指标

### 6.1 背景

Phase 3 后 citation_precision 和 faithfulness 已经很高，但 citation_coverage 仍然偏低。

原因不是系统没引用，而是当前 citation_coverage 计算方式不合理：

```text
当前 citation_coverage = 被引用 context 数量 / 所有 context 数量
```

但 Evidence Composer 已经把 evidence 分成：

```text
primary
supporting
context_only
```

不是所有 context 都应该被引用。

### 6.2 新指标定义

新增：

```text
primary_evidence_coverage = 被引用的 primary evidence 数量 / primary evidence 总数量
```

### 6.3 评估逻辑

只要求 primary evidence 被引用。

对于 supporting evidence：

```text
可引用，也可不引用
```

对于 context_only evidence：

```text
不要求引用
```

### 6.4 代码修改建议

可能涉及文件：

```text
DocResearch/eval/metrics.py
DocResearch/eval/level2_fullqa_eval.py
DocResearch/app/evidence/evidence_composer.py
```

新增输出字段：

```json
{
  "citation_coverage": 0.17,
  "primary_evidence_coverage": 0.92,
  "primary_evidence_count": 5,
  "cited_primary_evidence_count": 4
}
```

### 6.5 验收标准

```text
TechDocQA 和 GaRAGe 的 level2 结果中新增 primary_evidence_coverage。
报告中解释为什么 primary_evidence_coverage 比原始 citation_coverage 更合理。
```

---

## 7. 任务四：人工审计小实验

### 7.1 目标

防止项目过度依赖自动指标。

当前自动指标很高：

```text
TechDocQA faithfulness = 1.000
GaRAGe citation_precision = 1.000
```

但面试官或 reviewer 可能会质疑：

```text
这些指标是不是只检查格式？
答案真的对吗？
引用真的支持答案吗？
```

所以需要补一个小规模人工审计。

### 7.2 样本规模

建议总计 30 条以内：

| 数据集 | 样本数 |
|---|---:|
| TechDocQA | 10 |
| GaRAGe | 10 |
| MultiHop-RAG | 5 |
| StratRAG | 5 |

### 7.3 审计字段

每条记录建议包含：

```json
{
  "dataset": "techdocqa",
  "question_id": "...",
  "question": "...",
  "answer": "...",
  "citations": [],
  "answer_correctness": 2,
  "citation_support": 2,
  "answer_completeness": 2,
  "hallucination": false,
  "error_type": "none",
  "human_note": "The answer is correct and all major claims are supported."
}
```

字段解释：

```text
answer_correctness:
  0 = wrong
  1 = partially correct
  2 = correct

citation_support:
  0 = citation does not support answer
  1 = partially supports answer
  2 = fully supports answer

answer_completeness:
  0 = incomplete
  1 = partially complete
  2 = complete

hallucination:
  true / false

error_type:
  none
  retrieval_missing
  weak_citation
  incomplete_answer
  unsupported_claim
  over_refusal
  wrong_answer
```

### 7.4 输出文件

```text
DocResearch/eval/human_audit_template.jsonl
DocResearch/outputs/human_audit/phase4_human_audit_results.jsonl
DocResearch/reports/phase4_human_audit_report.md
```

### 7.5 报告指标

统计：

```text
correct_or_partially_correct_rate
fully_supported_citation_rate
hallucination_rate
complete_answer_rate
main_error_types
```

### 7.6 验收标准

```text
完成 20～30 条人工审计。
报告中给出 3～5 条典型成功案例和 2～3 条失败案例。
```

---

## 8. 任务五：鲁棒性评测 Robustness Eval

### 8.1 目标

证明系统不仅能回答正常问题，也能处理异常问题。

可靠问答系统必须具备：

```text
无证据时不胡答
引用错误时能发现
上下文不足时能触发 warning 或 repair
问题超出文档范围时能拒答
```

### 8.2 新建数据集

建议新建：

```text
DocResearch/data/eval/robustness_eval.jsonl
```

样本数 20 条左右即可。

### 8.3 样本类型

| 类型 | 数量 | 目标 |
|---|---:|---|
| out_of_domain | 5 | 测试系统是否拒答 |
| insufficient_evidence | 5 | 测试证据不足时是否 warning / repair |
| citation_corruption | 5 | 测试引用错误检测 |
| ambiguous_question | 5 | 测试模糊问题处理 |

### 8.4 样例

```json
{
  "id": "robust_001",
  "type": "out_of_domain",
  "question": "What is the best GPU for training a 70B model?",
  "expected_behavior": "refuse_or_state_not_in_docs",
  "gold_behavior": "The system should not answer from unsupported context."
}
```

```json
{
  "id": "robust_002",
  "type": "ambiguous_question",
  "question": "How does the graph work?",
  "expected_behavior": "ask_clarification_or_answer_with_scope",
  "gold_behavior": "The system should clarify whether graph means LangGraph workflow graph or retrieval graph."
}
```

### 8.5 指标

```text
refusal_accuracy
unsupported_answer_rate
hard_fail_detection_rate
soft_warn_detection_rate
repair_trigger_precision
over_refusal_rate
```

### 8.6 输出文件

```text
DocResearch/eval/robustness_eval.py
DocResearch/data/eval/robustness_eval.jsonl
DocResearch/outputs/robustness/phase4_robustness_results.jsonl
DocResearch/reports/phase4_robustness_report.md
```

### 8.7 验收标准

```text
out_of_domain unsupported_answer_rate <= 0.20
citation_corruption hard_fail_detection_rate >= 0.80
insufficient_evidence soft_warn_or_hard_fail_rate >= 0.80
ambiguous_question unsafe_answer_rate <= 0.20
```

---

## 9. 任务六：Demo Cases 整理

### 9.1 目标

整理 3～5 个可以在 README、面试、答辩中展示的案例。

### 9.2 Demo Case 类型

建议选以下 5 类：

| Case | 展示点 |
|---|---|
| Case 1: TechDocQA 技术概念问答 | 展示 grounded answer + citations |
| Case 2: MultiHop-RAG 多跳检索 | 展示 hybrid_graph / selective_graph 的价值 |
| Case 3: StratRAG 策略文档检索 | 展示 adaptive hybrid 选择 dense-dominant |
| Case 4: GaRAGe grounding | 展示 citation precision 与 faithfulness |
| Case 5: Robustness / 无证据拒答 | 展示可靠性与 guardrails |

### 9.3 每个 demo case 的格式

```markdown
## Demo Case 1: Technical Document QA

### Question
...

### Retrieval Strategy
adaptive_hybrid / selective_graph

### Retrieved Evidence
- [doc-s01-c002] ...
- [doc-s03-c004] ...

### Answer
...

### Citations
...

### Judge Result
PASS / SOFT_WARN / HARD_FAIL

### Why This Case Matters
...
```

### 9.4 输出文件

```text
DocResearch/reports/demo_cases.md
```

### 9.5 验收标准

```text
README 中能链接到 demo_cases.md。
每个 case 都能说明一个系统能力，而不是只展示普通问答。
```

---

## 10. 任务七：最终实验总表

### 10.1 目标

将 Level 1、Level 2、Phase 3、Phase 4 结果整合到一张最终项目总结表中。

### 10.2 建议总表结构

```markdown
| Level | Dataset | Main Metric | Best / Final Result | Key Finding |
|---|---|---:|---:|---|
| Level 1 Retrieval | MultiHop-RAG | r@10 | 0.813 | hybrid_graph best for multi-hop news |
| Level 1 Retrieval | StratRAG | r@10 | 0.900 / 0.875 adaptive | dense strong, adaptive improved after Phase 3 |
| Level 1 Retrieval | TechDocQA | r@10 | 1.000 | retrieval saturated; better for full QA |
| Level 1 Retrieval | GaRAGe | r@10 | 1.000 | retrieval saturated; useful for grounding |
| Level 2 Full QA | TechDocQA | faithfulness | 1.000 | reliable grounded QA |
| Level 2 Full QA | GaRAGe | citation_precision | 1.000 | strong citation reliability |
| Reliability | TechDocQA | guardrail_pass_rate | 0.976 | Judge calibration solved over-repair |
| Robustness | robustness_eval | refusal_accuracy | TBD | Phase 4 target |
```

### 10.3 输出文件

```text
DocResearch/reports/final_eval_summary.md
```

---

## 11. 任务八：Final Project Report

### 11.1 目标

输出一份完整项目总结报告，用于：

```text
GitHub 展示
简历项目复盘
面试讲解
后续 PPT
```

### 11.2 建议文件名

```text
DocResearch/reports/final_project_report.md
```

### 11.3 报告结构

```markdown
# DocResearch-Agent 2026 Final Project Report

## 1. Project Motivation
## 2. Problem Definition
## 3. System Architecture
## 4. Key Technical Design
### 4.1 Context Planner
### 4.2 Adaptive Hybrid Retrieval
### 4.3 Selective Graph Expansion
### 4.4 Evidence Tier Composer
### 4.5 Citation Guardrails
### 4.6 Self-Reflection Judge
### 4.7 Repair Router

## 5. Evaluation Setup
### 5.1 Datasets
### 5.2 Metrics
### 5.3 Baselines

## 6. Main Results
### 6.1 Level 1 Retrieval Results
### 6.2 Level 2 Full QA Results
### 6.3 Reliability Calibration Results
### 6.4 Robustness Results

## 7. Key Findings
## 8. Failure Cases and Limitations
## 9. Engineering Implementation
## 10. Conclusion
```

### 11.4 必须写清楚的核心发现

```text
1. Fixed hybrid + always-on graph 不是总有效。
2. Reranker 可能带来负迁移，需要通过 trace 定位。
3. Adaptive hybrid 比固定策略更适合跨数据集使用。
4. Graph expansion 适合 selective use，而不是 always-on。
5. Judge/Guardrails 必须区分 PASS / SOFT_WARN / HARD_FAIL，否则会造成无效 repair。
6. Evidence tier 能让 citation 评估更合理。
7. 可靠性系统的价值不只是提高 recall，而是减少 unsupported answer 和无效修复。
```

---

## 12. 任务九：简历项目描述

### 12.1 目标

准备一版简历可用描述，突出这个项目不是普通 RAG。

### 12.2 中文版示例

```text
DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统。构建包含 Context Planner、Adaptive Hybrid Retrieval、Selective Graph Expansion、Evidence Tier Composer、Citation Guardrails、Self-Reflection Judge 与 Repair Router 的 8 节点 LangGraph 工作流，实现技术文档问答中的动态检索规划、证据组合、引用校验与错误修复。基于 TechDocQA、MultiHop-RAG、StratRAG、GaRAGe 四类数据集完成 Level 1 检索评测与 Level 2 Full QA 评测；MultiHop-RAG hybrid_graph recall@10 达到 0.813，TechDocQA Full QA faithfulness 达到 1.000，guardrail_pass_rate 从 0.000 提升至 0.976，平均 repair 次数从 2.000 降至 0.07。
```

### 12.3 英文版示例

```text
Built DocResearch-Agent 2026, a context-engineered Agentic GraphRAG system for reliable technical-document QA. Designed an 8-node LangGraph workflow with Context Planner, Adaptive Hybrid Retrieval, Selective Graph Expansion, Evidence-Tier Composer, Citation Guardrails, Self-Reflection Judge, and Repair Router. Evaluated the system on TechDocQA, MultiHop-RAG, StratRAG, and GaRAGe with Level-1 retrieval and Level-2 full-QA benchmarks. Achieved 0.813 recall@10 on MultiHop-RAG with hybrid_graph retrieval, 1.000 faithfulness on TechDocQA full QA, and improved guardrail pass rate from 0.000 to 0.976 while reducing average repair count from 2.000 to 0.07.
```

### 12.4 输出文件

```text
DocResearch/reports/resume_project_description.md
```

---

## 13. Phase 4 推荐执行顺序

不要同时乱改。建议按以下顺序执行：

```text
Step 1：确认根 README 展示正常
Step 2：格式化 Phase 3 report
Step 3：新增 primary_evidence_coverage 指标
Step 4：重新跑 TechDocQA + GaRAGe Level 2 指标
Step 5：构建 robustness_eval.jsonl
Step 6：跑 robustness_eval.py
Step 7：完成人工审计 20～30 条
Step 8：整理 demo_cases.md
Step 9：生成 final_eval_summary.md
Step 10：生成 final_project_report.md
Step 11：生成 resume_project_description.md
```

---

## 14. Phase 4 验收标准

### 14.1 必须完成

```text
[ ] 根 README 首页确认显示 DocResearch-Agent
[ ] Phase 3 报告格式整理完成
[ ] 新增 primary_evidence_coverage 指标
[ ] TechDocQA / GaRAGe Level 2 结果重新计算
[ ] 完成 robustness_eval.jsonl
[ ] 完成 robustness_eval.py
[ ] 生成 phase4_robustness_report.md
[ ] 完成 20～30 条人工审计
[ ] 生成 phase4_human_audit_report.md
[ ] 生成 demo_cases.md
[ ] 生成 final_eval_summary.md
[ ] 生成 final_project_report.md
[ ] 生成 resume_project_description.md
```

### 14.2 建议指标目标

| 指标 | 目标 |
|---|---:|
| TechDocQA faithfulness | >= 0.95 |
| TechDocQA citation_precision | >= 0.90 |
| GaRAGe faithfulness | >= 0.90 |
| GaRAGe citation_precision | >= 0.90 |
| primary_evidence_coverage | >= 0.80 |
| robustness unsupported_answer_rate | <= 0.20 |
| robustness hard_fail_detection_rate | >= 0.80 |
| human audit hallucination_rate | <= 0.10 |
| human audit citation_support >= 1 | >= 0.85 |

---

## 15. 给 Coding Agent 的执行提示词

可以直接把下面这段给 coding agent：

```text
请基于当前 DocResearch-Agent 项目进入 Phase 4：Finalization, Robustness Audit & Demo Packaging。

注意：本阶段不要继续新增复杂 agent、不要重构核心架构、不要扩大为大规模 benchmark。当前目标是项目收口、鲁棒性验证、人工审计、展示包装和最终报告。

请按以下顺序执行：

1. 检查并确认根 README 已经以 DocResearch-Agent 为主项目展示，必要时优化 README 的结构与第一屏内容。
2. 整理 DocResearch/reports/docresearch_phase3_reliability_report.md 的 Markdown 格式，使其适合 GitHub 阅读。
3. 在 Level 2 评测中新增 primary_evidence_coverage 指标。该指标只统计 primary evidence 的引用覆盖，不再要求 context_only evidence 被引用。
4. 重新运行 TechDocQA 和 GaRAGe Full QA 评测，输出包含 primary_evidence_coverage 的新结果。
5. 构建 20 条左右 robustness_eval.jsonl，包括 out_of_domain、insufficient_evidence、citation_corruption、ambiguous_question 四类样本。
6. 实现 robustness_eval.py，统计 refusal_accuracy、unsupported_answer_rate、hard_fail_detection_rate、soft_warn_detection_rate、repair_trigger_precision、over_refusal_rate。
7. 输出 phase4_robustness_report.md。
8. 准备 human_audit_template.jsonl，并抽样 20～30 条结果进行人工审计，输出 phase4_human_audit_report.md。
9. 整理 3～5 个 demo cases，输出 demo_cases.md。
10. 生成 final_eval_summary.md，汇总 Level 1、Level 2、Reliability、Robustness 结果。
11. 生成 final_project_report.md，完整总结项目动机、架构、实验、发现、限制与结论。
12. 生成 resume_project_description.md，包含中文和英文简历项目描述。

验收标准：
- 不引入核心架构大改。
- Level 2 指标不能明显退化。
- robustness eval 能证明系统在无证据、错误引用、模糊问题上不会直接胡答。
- 最终报告能支撑 GitHub 展示和面试讲解。
```

---

## 16. 最终阶段判断

Phase 4 完成后，这个项目就可以作为一个完整的大项目展示。

最终项目定位可以写成：

```text
DocResearch-Agent 2026 是一个面向技术文档问答的 Context-Engineered Agentic GraphRAG 可靠性系统。它不是简单的向量检索 RAG，而是通过 adaptive retrieval、selective graph expansion、evidence-tier composition、citation guardrails、self-reflection judge 和 repair router，构建了一个可检索、可引用、可审查、可修复、可评测的技术文档 QA Agent。
```

Phase 4 的终点不是“再提高一个榜单分数”，而是：

```text
项目能展示
结果能解释
失败能承认
代码能复现
简历能写
面试能讲
```
