# DocResearch-Agent 2026 Phase 3 规划

## Reliability Calibration & Full QA Stabilization

> 当前阶段目标：在 Phase 2 已经完成检索层稳定化、adaptive hybrid、selective graph 和 Level 1/Level 2 初步评测的基础上，进入可靠性校准阶段。Phase 3 不再继续堆新模块，而是校准已有 Judge / Guardrails / Repair / Evidence Composer，使系统从“能跑通、能召回”推进到“能稳定判断、能减少误修复、能形成可信完整报告”。

---

## 1. 当前状态总结

### 1.1 已完成内容

本阶段开始前，项目已经完成以下关键工作：

1. **Level 1 Retrieval Eval 已完成**
   - 覆盖 MultiHop-RAG、TechDocQA、StratRAG、GaRAGe 四个数据集。
   - 覆盖 dense_only、bm25_only、hybrid、hybrid_graph、adaptive_hybrid、selective_graph 等策略。
   - 已定位此前 MultiHop-RAG 上 hybrid 退化的主要原因：reranker 负迁移。

2. **Reranker 根因已定位并修复**
   - MultiHop-RAG hybrid r@10 从 0.656 提升到 0.803。
   - 说明此前“hybrid 无效”的结论并不成立，而是被 reranker 污染。

3. **Hybrid 检索已恢复有效**
   - MultiHop-RAG 上 hybrid 已超过 dense_only 与 bm25_only。
   - hybrid_graph 在 MultiHop-RAG 上达到当前最高 r@10 = 0.813。

4. **Adaptive Hybrid 已达成基础目标**
   - 四个数据集上均不低于 BM25 基线。
   - 说明 adaptive_hybrid 可以作为当前通用默认检索策略。

5. **TechDocQA Level 2 Full QA 已跑通**
   - retrieval_recall@10 = 0.976。
   - has_answer_rate = 1.000。
   - citation_precision = 0.929。
   - faithfulness = 1.000。

6. **新瓶颈已明确**
   - guardrail_pass_rate = 0.000。
   - avg_repair_count = 2.000。
   - avg_latency = 22.1s。
   - 问题不再主要是 retrieval，而是 Judge / Guardrails / Repair 过严，导致好答案也被不断 repair。

---

## 2. Phase 3 核心判断

Phase 3 的核心判断是：

> 检索层已经基本进入可展示状态，下一阶段不能继续围绕 dense / BM25 / graph 反复微调，而应该转向 Reliability Calibration，即校准系统如何判断答案是否可靠，以及什么时候应该 repair。

当前最关键的问题不是：

```text
系统能不能检索到 gold 文档？
```

而是：

```text
系统能不能正确判断答案是否已经足够可靠？
系统能不能避免把好答案误判成失败？
系统能不能只在真正需要时 repair？
系统能不能降低 full QA 延迟，同时保持 faithfulness 和 citation precision？
```

---

## 3. Phase 3 总目标

Phase 3 的目标不是新增复杂模块，而是完成以下四件事：

1. **校准 Self-Reflection Judge**
   - 降低误判。
   - 区分 hard fail、soft warn、pass。
   - 避免所有样本都进入 repair。

2. **优化 Guardrails 与 Repair Router**
   - 只有真实失败才触发 repair。
   - 对 citation coverage 低但 faithfulness 高的样本，不应强制 repair。
   - 减少无效循环修复。

3. **改进 Evidence Composer 与 Citation 判断逻辑**
   - 区分 primary evidence、supporting evidence、context-only evidence。
   - Judge 只要求核心证据被引用，而不是要求所有 context 都被覆盖。

4. **整理项目展示与最终报告**
   - 根 README 从 IRIS 改为 DocResearch-Agent 主项目介绍。
   - 更新 Phase 2 + Phase 3 的实验结果摘要。
   - 形成可用于简历 / 面试 / 项目展示的清晰叙事。

---

## 4. 禁止事项

Phase 3 不建议做以下事情：

1. **不要继续新增 Agent 模块**
   - 当前已有 Context Planner、Retriever、Evaluator、Composer、Generator、Guardrails、Judge、Repair Router。
   - 问题不是模块不够，而是已有模块判断标准不准。

2. **不要继续扩大数据集规模**
   - 当前应该先稳定 TechDocQA full QA 和 GaRAGe citation eval。
   - 不要一上来全量跑大规模公开数据集。

3. **不要为了提高 pass rate 简单关闭 judge**
   - 目标不是让所有答案都 pass。
   - 目标是让 judge 能区分真正错误和可接受答案。

4. **不要为了提高 graph 表现强行调高 graph 权重**
   - Phase 2 已经证明 graph 有小幅正增益，但不是全局增强器。
   - 后续仍应保持 selective graph 的叙事。

5. **不要用 TechDocQA/GaRAGe 的满分检索去夸大 retrieval 能力**
   - TechDocQA 和 GaRAGe 更适合验证 full QA、citation、faithfulness。
   - Retrieval 区分度主要看 MultiHop-RAG 和 StratRAG。

---

## 5. Phase 3 任务拆解

---

# Task 1：Self-Reflection Judge 校准

## 5.1 当前问题

TechDocQA Level 2 Full QA 当前表现为：

```text
retrieval_recall@10 = 0.976
has_answer_rate     = 1.000
citation_precision  = 0.929
faithfulness        = 1.000
guardrail_pass_rate = 0.000
avg_repair_count    = 2.000
avg_latency         = 22.1s
```

这个结果说明：

```text
答案本身质量并不差；
检索召回较高；
引用精度较高；
faithfulness 满分；
但 judge / guardrails 将所有样本判为失败。
```

当前判断标准过严，尤其是 citation_support / citation_coverage 相关阈值可能被误用。

---

## 5.2 修改目标

将 Judge 输出从简单 pass/fail 改成三层：

```text
PASS
SOFT_WARN
HARD_FAIL
```

### PASS

满足以下条件时直接通过：

```text
- 有答案；
- 有 citation；
- citation_precision 较高；
- faithfulness 较高；
- 没有明显 unsupported claim；
- 没有 evidence contradiction。
```

### SOFT_WARN

满足以下情况时只记录 warning，不触发强制 repair：

```text
- citation_coverage 偏低，但答案核心 claim 有 citation；
- citation_support 分数偏低，但 faithfulness 高；
- answer completeness 一般，但没有事实错误；
- context 中有部分证据未被使用。
```

### HARD_FAIL

以下情况必须触发 repair：

```text
- answer 为空；
- 没有 citation；
- citation 指向不存在的 chunk；
- answer 中存在明显 unsupported claim；
- answer 与 evidence 冲突；
- gold evidence 已检索到但答案明显没回答问题；
- citation_precision 低于最低阈值；
- faithfulness 低于最低阈值。
```

---

## 5.3 建议实现位置

优先检查并修改以下模块：

```text
DocResearch/app/judge/
DocResearch/app/repair/
DocResearch/app/evidence/
DocResearch/app/graph.py
```

如果当前 judge 逻辑集中在某个文件中，例如：

```text
self_reflection_judge.py
citation_guardrails.py
repair_router.py
```

则优先从这些文件中调整。

---

## 5.4 输出字段建议

Judge 结果建议统一输出以下字段：

```json
{
  "decision": "PASS | SOFT_WARN | HARD_FAIL",
  "should_repair": false,
  "failure_type": null,
  "warnings": [],
  "scores": {
    "faithfulness": 1.0,
    "citation_precision": 0.93,
    "citation_coverage": 0.17,
    "claim_support": 0.85,
    "answer_completeness": 0.80
  },
  "reason": "..."
}
```

其中：

```text
PASS       → should_repair = false
SOFT_WARN  → should_repair = false，但记录 warning
HARD_FAIL  → should_repair = true
```

---

## 5.5 验收标准

在 TechDocQA Level 2 Full QA 上：

```text
guardrail_pass_rate: 0.000 → >= 0.400
avg_repair_count:    2.000 → < 0.800
avg_latency:         22.1s → < 15.0s
faithfulness:        >= 0.950
citation_precision:  >= 0.850
has_answer_rate:     >= 0.950
```

注意：

```text
不能为了提高 pass rate 牺牲 faithfulness。
不能简单关闭 repair。
不能把所有 HARD_FAIL 改成 PASS。
```

---

# Task 2：Repair Router 降低无效修复

## 6.1 当前问题

当前 full QA 中 avg_repair_count = 2.000，说明很多样本都走到了最大 repair 次数。

这可能意味着：

```text
1. Judge 阈值过严；
2. Repair 没有真正修复失败类型；
3. Repair Router 没有判断是否值得继续 repair；
4. 同一种失败被重复修复；
5. citation_coverage 类 soft issue 被当作 hard failure。
```

---

## 6.2 修改目标

Repair Router 应该根据 failure_type 决定修复路径，而不是所有失败都重复走同一条 repair。

建议 failure_type 分类：

```text
NO_ANSWER
NO_CITATION
INVALID_CITATION
LOW_CITATION_PRECISION
UNSUPPORTED_CLAIM
LOW_COMPLETENESS
LOW_RETRIEVAL_RECALL
EVIDENCE_CONFLICT
SOFT_LOW_COVERAGE
```

建议 repair 策略：

| failure_type | 是否 repair | 推荐动作 |
|---|---|---|
| NO_ANSWER | 是 | 重新生成答案 |
| NO_CITATION | 是 | 重新生成带引用答案 |
| INVALID_CITATION | 是 | 修复引用格式 / citation mapping |
| LOW_CITATION_PRECISION | 是 | 重新选择 evidence 并生成 |
| UNSUPPORTED_CLAIM | 是 | 删除 unsupported claim 或补证据 |
| LOW_COMPLETENESS | 可选 | 如果问题是多点问题，则补充回答 |
| LOW_RETRIEVAL_RECALL | 是 | 重新检索或 graph expansion |
| EVIDENCE_CONFLICT | 是 | 重新整理 evidence |
| SOFT_LOW_COVERAGE | 否 | 记录 warning，不 repair |

---

## 6.3 Repair 早停机制

新增 early stop：

```text
如果连续两次 repair 后 judge score 没有提升，则停止 repair。
如果当前 decision = SOFT_WARN，则停止 repair。
如果 faithfulness >= 0.95 且 citation_precision >= 0.85，则停止 repair。
```

建议 trace 中记录：

```json
{
  "repair_round": 1,
  "failure_type": "NO_CITATION",
  "action": "regenerate_with_citation",
  "score_before": {...},
  "score_after": {...},
  "improved": true,
  "stop_reason": null
}
```

---

## 6.4 验收标准

```text
avg_repair_count < 0.8
repair_success_rate 可计算
无效 repair 占比下降
重复 repair loop 消失
latency 明显下降
```

建议新增指标：

```text
repair_trigger_rate
repair_success_rate
repair_no_improve_rate
soft_warn_rate
hard_fail_rate
```

---

# Task 3：Evidence Composer 分层

## 7.1 当前问题

当前 citation_coverage 低可能不一定说明答案质量差。因为检索上下文中可能有很多背景 chunk，并不是每个 chunk 都需要被引用。

如果 Judge 要求所有 context 都被 citation 覆盖，就会导致误判。

---

## 7.2 修改目标

Evidence Composer 输出时，将 evidence 分成三类：

```text
primary_evidence
supporting_evidence
context_only_evidence
```

### primary_evidence

用于支撑答案核心结论，应该被引用。

例如：

```text
定义、API 约束、关键步骤、gold chunk、直接回答问题的段落。
```

### supporting_evidence

用于补充背景，引用可选。

例如：

```text
上游概念解释、相关模块说明、背景性流程描述。
```

### context_only_evidence

只用于帮助 LLM 理解上下文，不要求引用。

例如：

```text
相邻 chunk、graph expansion 带来的弱相关 chunk、overview 类背景。
```

---

## 7.3 Judge 判断调整

citation_coverage 不应该计算所有 context，而应该重点计算：

```text
primary_evidence_coverage
claim_citation_support
citation_precision
```

建议新指标：

```text
primary_evidence_coverage
supporting_evidence_usage
context_noise_ratio
claim_support_rate
```

---

## 7.4 验收标准

```text
primary_evidence_coverage >= 0.70
citation_precision >= 0.85
faithfulness >= 0.95
soft_warn_rate 合理上升
hard_fail_rate 合理下降
```

---

# Task 4：Adaptive Hybrid 小幅修正 StratRAG

## 8.1 当前问题

Phase 2 报告显示 StratRAG 上 dense_only 是最佳策略，而 adaptive_hybrid 低于 dense_only。

当前结果大致为：

```text
StratRAG dense_only r@10 ≈ 0.900
StratRAG adaptive_hybrid r@10 ≈ 0.845
```

这说明某些场景下 BM25 信号较弱，adaptive 仍然引入了 BM25 噪声。

---

## 8.2 修改目标

新增一个 dense-dominant 分支：

```text
dense_strong_bm25_weak
```

触发条件可以包括：

```text
1. dense_top1_score 高；
2. dense_top1_top5_gap 明显；
3. bm25_top1_score 低；
4. dense/bm25 overlap 低；
5. query 偏语义描述，不是关键词/API 精确匹配。
```

对应权重：

```text
dense_weight = 0.85 ~ 0.95
bm25_weight  = 0.00 ~ 0.10
graph_weight = 0.00 ~ 0.10
```

---

## 8.3 注意事项

不要为了 StratRAG 牺牲 MultiHop-RAG。

验收目标：

```text
StratRAG adaptive_hybrid r@10 >= 0.880
MultiHop-RAG adaptive_hybrid r@10 >= 0.800
TechDocQA adaptive_hybrid r@10 = 1.000 或接近 1.000
GaRAGe adaptive_hybrid r@10 >= 0.980
```

---

# Task 5：Level 2 Full QA 扩展到 GaRAGe

## 9.1 当前状态

TechDocQA 已完成 Level 2 Full QA。

下一步建议将 GaRAGe sample_50 用于 grounding / citation 评测。

---

## 9.2 目标

GaRAGe 不适合继续证明 retrieval，因为它在 Level 1 中已经接近满分。

它更适合证明：

```text
1. answer 是否 grounded；
2. citation 是否真实支持答案；
3. unsupported claim 是否减少；
4. Judge 是否能发现 citation 问题；
5. Repair 是否能修复 grounding 问题。
```

---

## 9.3 评测指标

建议指标：

```text
answer_rate
faithfulness
citation_precision
citation_recall / coverage
unsupported_claim_rate
guardrail_pass_rate
repair_trigger_rate
repair_success_rate
avg_latency
```

---

## 9.4 验收标准

```text
GaRAGe sample_50 full QA 跑通
faithfulness >= 0.90
citation_precision >= 0.85
unsupported_claim_rate <= 0.15
avg_repair_count < 1.0
avg_latency < 20s
```

---

# Task 6：根 README 与项目展示整理

## 10.1 当前问题

当前仓库根 README 仍然偏 IRIS 项目介绍，不利于展示 DocResearch-Agent。

别人打开仓库第一眼可能不知道 DocResearch 才是主项目。

---

## 10.2 修改目标

根 README 改成 M-Research 项目总览，并突出：

```text
DocResearch-Agent 2026 是当前主项目。
IRIS / 其他目录是历史参考或数据集目录。
```

建议根 README 结构：

```text
# M-Research

## Main Project: DocResearch-Agent 2026

一句话定位：
Context-Engineered Agentic GraphRAG for reliable technical document QA.

## Why not ordinary RAG?

普通 RAG 的问题：固定 top-k、缺少检索规划、缺少证据校验、缺少修复闭环。

## System Architecture

Context Planner → Adaptive Hybrid Retriever → Selective Graph Expansion → Evidence Composer → Grounded Answer → Citation Guardrails → Self-Reflection Judge → Repair Router

## Current Results

Phase 2 Level 1 Retrieval Eval summary
Phase 2 Level 2 TechDocQA Full QA summary

## How to Run

build index
run level1 eval
run level2 full QA
start backend/frontend

## Reports

links to DocResearch/reports/*.md
```

---

## 10.3 必须展示的结果

根 README 中建议只展示最有说服力的结果：

```text
MultiHop-RAG:
- hybrid r@10: 0.656 → 0.803 after reranker fix
- hybrid_graph r@10: 0.813 best

TechDocQA Full QA:
- retrieval_recall@10 = 0.976
- citation_precision = 0.929
- faithfulness = 1.000

Adaptive Hybrid:
- 4 datasets all >= BM25 baseline
```

不要把所有表格都塞到 README，完整表格放报告里。

---

# Task 7：Phase 3 报告生成

## 11.1 输出文件

Phase 3 完成后，建议生成：

```text
DocResearch/reports/docresearch_phase3_reliability_report.md
DocResearch/reports/level2_techdocqa_calibrated_report.md
DocResearch/reports/level2_garage_grounding_report.md
DocResearch/reports/readme_project_summary.md
```

---

## 11.2 Phase 3 报告结构

```text
# DocResearch-Agent Phase 3 Reliability Calibration Report

## 1. Phase 2 Problem Recap
## 2. Judge/Repair Over-Strictness Diagnosis
## 3. Calibration Method
## 4. TechDocQA Full QA Before/After
## 5. GaRAGe Grounding Eval
## 6. Repair Behavior Analysis
## 7. Latency Analysis
## 8. Remaining Problems
## 9. Final Project Status
```

---

## 11.3 Before / After 表格

必须包含：

| Metric | Before Phase 3 | After Phase 3 | Target |
|---|---:|---:|---:|
| guardrail_pass_rate | 0.000 | TBD | >= 0.400 |
| avg_repair_count | 2.000 | TBD | < 0.800 |
| avg_latency | 22.1s | TBD | < 15.0s |
| faithfulness | 1.000 | TBD | >= 0.950 |
| citation_precision | 0.929 | TBD | >= 0.850 |

---

# 12. 推荐执行顺序

建议严格按下面顺序执行：

```text
Step 1：备份当前 Phase 2 结果和报告
Step 2：修改 Judge 输出为 PASS / SOFT_WARN / HARD_FAIL
Step 3：修改 Repair Router，只对 HARD_FAIL repair
Step 4：加入 repair early stop
Step 5：重新跑 TechDocQA Level 2 Full QA
Step 6：生成 before/after 对比
Step 7：修改 Evidence Composer 分层
Step 8：再次跑 TechDocQA Level 2 Full QA
Step 9：跑 GaRAGe sample_50 Full QA / Grounding Eval
Step 10：小幅修正 adaptive_hybrid 的 dense-dominant 分支
Step 11：跑 Level 1 quick regression，确保检索不退化
Step 12：整理根 README
Step 13：生成 Phase 3 最终报告
```

---

# 13. 最小验收标准

Phase 3 最小完成标准：

```text
1. TechDocQA Full QA 校准后 guardrail_pass_rate >= 0.40
2. TechDocQA avg_repair_count < 0.80
3. TechDocQA avg_latency < 15s
4. TechDocQA faithfulness >= 0.95
5. TechDocQA citation_precision >= 0.85
6. GaRAGe sample_50 Full QA 跑通
7. Repair trace 中能看到 failure_type 和 repair action
8. Level 1 检索 quick regression 不明显退化
9. 根 README 改为 DocResearch-Agent 主项目展示
10. 生成 Phase 3 reliability report
```

---

# 14. 理想验收标准

如果时间允许，理想目标为：

```text
TechDocQA:
- guardrail_pass_rate >= 0.60
- avg_repair_count <= 0.50
- avg_latency <= 12s
- faithfulness >= 0.95
- citation_precision >= 0.90

GaRAGe:
- faithfulness >= 0.90
- citation_precision >= 0.85
- unsupported_claim_rate <= 0.15

StratRAG:
- adaptive_hybrid r@10 >= 0.880

MultiHop-RAG:
- adaptive_hybrid r@10 >= 0.800
- hybrid_graph r@10 保持 >= 0.810
```

---

# 15. 给 Coding Agent 的执行提示词

下面这段可以直接交给 coding agent 使用：

```text
请基于当前 M-Research / DocResearch 项目进入 Phase 3：Reliability Calibration & Full QA Stabilization。

当前 Phase 2 已完成 adaptive_hybrid、selective_graph、Level 1 四数据集评测，以及 TechDocQA Level 2 Full QA。现有结果显示 retrieval 已基本达标，但 TechDocQA Full QA 中 guardrail_pass_rate=0、avg_repair_count=2.0、avg_latency=22.1s，说明 Self-Reflection Judge / Guardrails / Repair Router 过严，导致好答案也被误判并反复 repair。

本阶段不要新增新 Agent，不要扩大数据集，不要重构检索框架。请重点完成以下任务：

1. 将 Judge 输出从二分类 pass/fail 改成 PASS / SOFT_WARN / HARD_FAIL 三层判断。
2. 只有 HARD_FAIL 触发 repair；SOFT_WARN 只记录 warning，不强制 repair。
3. 为 Repair Router 增加 failure_type 分类和 early stop，避免重复无效 repair。
4. 调整 citation_coverage 判断逻辑，不要要求所有 context chunk 都被引用；优先检查 primary evidence 和 answer claim 是否被 citation 支持。
5. Evidence Composer 尝试区分 primary_evidence、supporting_evidence、context_only_evidence。
6. 重新跑 TechDocQA Level 2 Full QA，并生成 before/after 对比报告。
7. 增加 GaRAGe sample_50 Full QA / grounding eval。
8. 小幅修正 adaptive_hybrid，在 StratRAG dense 强、BM25 弱的场景下使用 dense-dominant 分支，但不能牺牲 MultiHop-RAG。
9. 做 Level 1 quick regression，确认检索指标没有明显退化。
10. 更新根 README，让 DocResearch-Agent 2026 成为仓库首页主项目。
11. 生成 docresearch_phase3_reliability_report.md。

验收标准：
- TechDocQA guardrail_pass_rate >= 0.40
- TechDocQA avg_repair_count < 0.80
- TechDocQA avg_latency < 15s
- TechDocQA faithfulness >= 0.95
- TechDocQA citation_precision >= 0.85
- GaRAGe sample_50 full QA 跑通
- Level 1 quick regression 不明显退化
- 根 README 已更新
- Phase 3 report 已生成
```

---

# 16. Phase 3 完成后的项目叙事

如果 Phase 3 达标，项目可以这样描述：

```text
DocResearch-Agent 2026 是一个面向技术文档可靠问答的 Context-Engineered Agentic GraphRAG 系统。项目首先构建 dense、BM25、hybrid 和 lightweight graph expansion 检索层，并在 MultiHop-RAG、StratRAG、TechDocQA、GaRAGe 四类数据集上完成 Level 1 检索评测。实验发现 fixed reranker 会导致 MultiHop-RAG 上 hybrid 退化，因此通过 trace 诊断定位并移除负迁移 reranker，使 hybrid r@10 从 0.656 提升到 0.803，hybrid_graph 达到 0.813。

随后项目实现 adaptive_hybrid 和 selective_graph，使检索策略从固定融合升级为基于 query 特征、检索置信度和证据不足信号的自适应策略。Phase 3 进一步校准 Judge / Guardrails / Repair Router，将系统从“能检索、能回答”推进到“能判断、能引用、能避免无效修复”。最终形成可检索、可引用、可审查、可修复、可评测的可靠技术文档问答 Agent。
```

---

# 17. 最终建议

Phase 3 的关键不是继续做更复杂，而是让系统更可信。

当前项目已经具备：

```text
检索策略对比
adaptive 检索
selective graph
full QA
citation guardrails
judge repair
trace report
```

下一步只要把 Judge / Repair 调准，并把 README 与报告整理好，项目就可以从“实验工程”进入“可展示项目”阶段。

