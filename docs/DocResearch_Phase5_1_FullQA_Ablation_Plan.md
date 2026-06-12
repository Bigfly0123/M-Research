# DocResearch-Agent 2026 — Phase 5.1 Full QA Ablation Baseline Plan

## 0. 背景与目的

当前 DocResearch-Agent 已经完成 v1.0 收口，包含 Level 1 Retrieval Eval、Level 2 Full QA Eval、Robustness Eval、Human Audit、截断修复与 Release Tag。

但是当前最终结论里仍有一个展示短板：

> Retrieval 指标已经有 dense / BM25 / hybrid / hybrid_graph / adaptive_hybrid 等策略对比；但 Full QA 指标主要是最终系统的绝对数值，缺少与 Vanilla RAG / No-Guardrail RAG / Full System 的直接对比。

因此，Phase 5.1 的目标不是继续加新模块，而是补充一个小规模、低风险、强说服力的 **Full QA Ablation Baseline**，用于证明：

1. 最终系统不是只是在检索层有效；
2. Evidence Composer、Citation Guardrails、Judge、Repair 等可靠性模块确实改善了答案可靠性；
3. 最终报告和简历表述可以从“绝对指标”升级为“相对 baseline 提升”。

---

## 1. Phase 5.1 总目标

本阶段只做一件事：

> 在 TechDocQA 与 GaRAGe 上补充 Full QA 消融对比，比较 Vanilla RAG、Hybrid RAG、Full System 三种方式在 citation precision、faithfulness、unsupported claim、answer completeness、latency 等指标上的差异。

本阶段禁止扩展新架构、禁止新增复杂 agent、禁止重写检索框架。

---

## 2. 需要对比的 3 种 Full QA 配置

### 2.1 Baseline A：Vanilla RAG

定位：最普通的 RAG baseline。

配置要求：

```text
Retriever: dense_only
Evidence Composer: disabled or simple top-k concatenation
Citation Guardrails: disabled
Self-Reflection Judge: disabled
Repair Router: disabled
Answer Generator: direct generation from retrieved context
```

作用：

```text
证明普通 dense RAG 在引用准确性、faithfulness、unsupported claim 控制方面的表现。
```

建议配置名：

```text
vanilla_rag
```

---

### 2.2 Baseline B：Hybrid RAG without Reliability Modules

定位：检索增强但没有可靠性闭环的中间 baseline。

配置要求：

```text
Retriever: adaptive_hybrid or hybrid_graph
Evidence Composer: simple or current evidence composer without guardrail enforcement
Citation Guardrails: disabled
Self-Reflection Judge: disabled
Repair Router: disabled
Answer Generator: direct generation
```

作用：

```text
区分“检索增强带来的收益”和“可靠性模块带来的收益”。
```

建议配置名：

```text
hybrid_no_guardrails
```

---

### 2.3 Full System：DocResearch-Agent v1.0

定位：最终系统。

配置要求：

```text
Retriever: adaptive_hybrid / selective_graph / hybrid_graph according to existing config
Evidence Composer: enabled, with primary/supporting/context_only tiers
Citation Guardrails: enabled
Self-Reflection Judge: enabled, PASS / SOFT_WARN / HARD_FAIL
Repair Router: enabled, only HARD_FAIL triggers targeted repair
Answer Completion Check: enabled
```

作用：

```text
作为最终系统，与 Vanilla RAG 和 Hybrid RAG 做直接对比。
```

建议配置名：

```text
full_system
```

---

## 3. 评测数据范围

Phase 5.1 不需要跑全量大数据，只跑已有 Full QA 数据即可。

### 3.1 TechDocQA

```text
数量：42 条
用途：技术文档 QA 主评测集
重点：API / framework / workflow / constraint / design question
```

### 3.2 GaRAGe

```text
数量：50 条
用途：grounding / citation 评测
重点：开放域问题下的证据支持、safe refusal、unsupported claim 控制
```

### 3.3 可选小样本

如果成本较高，可以先跑：

```text
TechDocQA: 20 条
GaRAGe: 20 条
```

但最终报告建议使用完整：

```text
TechDocQA 42 + GaRAGe 50
```

---

## 4. 需要新增或修改的文件

建议新增：

```text
DocResearch/eval/level2_ablation_eval.py
DocResearch/eval/configs/level2_vanilla_rag.yaml
DocResearch/eval/configs/level2_hybrid_no_guardrails.yaml
DocResearch/eval/configs/level2_full_system.yaml
DocResearch/reports/phase5_1_fullqa_ablation_report.md
DocResearch/reports/final_eval_summary.md
DocResearch/reports/final_project_report.md
README.md
```

也可以在已有 `level2_fullqa_eval.py` 中增加 `--mode` 参数：

```bash
python DocResearch/eval/level2_fullqa_eval.py --dataset techdocqa --mode vanilla_rag
python DocResearch/eval/level2_fullqa_eval.py --dataset techdocqa --mode hybrid_no_guardrails
python DocResearch/eval/level2_fullqa_eval.py --dataset techdocqa --mode full_system
```

建议优先复用已有评测脚本，避免新增过多重复代码。

---

## 5. 需要记录的指标

### 5.1 核心指标

每个 dataset × method 都必须记录：

```text
has_answer_rate
citation_precision
faithfulness
unsupported_claim_rate
answer_completeness
guardrail_pass_rate
avg_repair_count
avg_latency
truncation_rate
```

其中：

```text
Vanilla RAG / Hybrid No-Guardrails:
  guardrail_pass_rate 可以记为 N/A
  avg_repair_count = 0

Full System:
  guardrail_pass_rate / avg_repair_count 正常记录
```

### 5.2 如果 unsupported_claim_rate 目前没有现成指标

可以用以下规则近似：

```text
unsupported_claim_rate = 1 - faithfulness
```

但报告中要注明：

```text
Unsupported claim rate is approximated from the faithfulness evaluator.
```

如果已有人工/LLM judge 能直接判断 unsupported claims，则优先使用直接指标。

---

## 6. 输出结果表格模板

### 6.1 TechDocQA Full QA Ablation

| Method | Citation Precision | Faithfulness | Unsupported Claim Rate | Answer Completeness | Avg Repair | Avg Latency |
|---|---:|---:|---:|---:|---:|---:|
| Vanilla RAG | TBD | TBD | TBD | TBD | 0.00 | TBD |
| Hybrid RAG w/o Guardrails | TBD | TBD | TBD | TBD | 0.00 | TBD |
| Full System | 0.952 | 0.988 | TBD | TBD | 0.12 | TBD |

### 6.2 GaRAGe Full QA Ablation

| Method | Citation Precision | Faithfulness | Unsupported Claim Rate | Answer Completeness | Avg Repair | Avg Latency |
|---|---:|---:|---:|---:|---:|---:|
| Vanilla RAG | TBD | TBD | TBD | TBD | 0.00 | TBD |
| Hybrid RAG w/o Guardrails | TBD | TBD | TBD | TBD | 0.00 | TBD |
| Full System | 0.980 | 0.970 | TBD | TBD | 0.06 | TBD |

### 6.3 Relative Improvement 表格

| Dataset | Metric | Full System vs Vanilla RAG | Full System vs Hybrid w/o Guardrails |
|---|---|---:|---:|
| TechDocQA | Citation Precision | TBD | TBD |
| TechDocQA | Faithfulness | TBD | TBD |
| TechDocQA | Unsupported Claim Reduction | TBD | TBD |
| GaRAGe | Citation Precision | TBD | TBD |
| GaRAGe | Faithfulness | TBD | TBD |
| GaRAGe | Unsupported Claim Reduction | TBD | TBD |

计算方式：

```text
相对提升 = (Full System - Baseline) / Baseline
错误率下降 = (Baseline Error - Full Error) / Baseline Error
```

注意：如果 baseline 为 0 或接近 0，使用绝对提升更合理。

---

## 7. 预期结论写法

### 7.1 如果 Full System 明显优于 Vanilla RAG

可以写：

```text
Compared with Vanilla RAG, the full DocResearch-Agent system improves citation precision and faithfulness by introducing evidence-tier composition, citation guardrails, self-reflection judging, and targeted repair. This confirms that the reliability gain does not come only from retrieval quality, but also from explicit evidence control and post-generation validation.
```

中文：

```text
与 Vanilla RAG 相比，完整系统在 citation precision 和 faithfulness 上进一步提升，说明项目收益不仅来自检索增强，也来自证据分层、引用校验、自我审查和定向修复组成的可靠性闭环。
```

### 7.2 如果 Hybrid RAG 已经很强，Full System 提升不大

可以写：

```text
Hybrid retrieval already provides strong context coverage, so the full system does not always yield large gains in answer accuracy. However, it improves reliability by reducing unsupported claims, enforcing citation validity, detecting hard failures, and avoiding unnecessary repair loops.
```

中文：

```text
Hybrid 检索已经提供了较强的上下文覆盖，因此完整系统在 answer accuracy 上不一定大幅提升；但它通过减少 unsupported claim、校验引用有效性、识别 hard failure 和控制无效 repair，提高了系统可靠性。
```

### 7.3 如果 Vanilla RAG 指标也很高

不要硬吹。应该写：

```text
On relatively easy datasets, Vanilla RAG can already achieve strong results. The value of DocResearch-Agent is more visible in reliability diagnostics, citation enforcement, repair control, and robustness evaluation rather than raw answer accuracy alone.
```

中文：

```text
在较简单的数据集上，Vanilla RAG 已经可以取得较好结果。DocResearch-Agent 的价值不只体现在原始答案准确率，而体现在可靠性诊断、引用约束、修复控制和鲁棒性评测闭环上。
```

---

## 8. 最终 README / 简历表述更新规则

Phase 5.1 完成后，README 和简历描述不能再只写绝对指标。

### 8.1 README 里应增加

```text
Full QA Ablation Study
```

内容包括：

```text
Vanilla RAG vs Hybrid RAG vs Full System
TechDocQA / GaRAGe 两个数据集
citation precision / faithfulness / unsupported claim / latency 对比
```

### 8.2 简历项目描述升级版

当前简历描述可以升级为：

```text
在 MultiHop-RAG、StratRAG、TechDocQA、GaRAGe 四个数据集上完成检索与 Full QA 评测；MultiHop-RAG 上 hybrid_graph recall@10 达到 0.813，相比 BM25-only 提升 8.7%，相比 dense-only 提升 2.5%。进一步补充 Vanilla RAG / Hybrid RAG / Full System 消融实验，验证 evidence-tier composer、citation guardrails、self-reflection judge 与 targeted repair 对 citation precision、faithfulness 和 unsupported claim 控制的贡献。
```

等 Phase 5.1 结果出来后，把 `TBD` 替换成具体提升数字。

---

## 9. 验收标准

Phase 5.1 完成标准如下：

```text
1. 能在 TechDocQA 上跑通 vanilla_rag / hybrid_no_guardrails / full_system 三种配置
2. 能在 GaRAGe 上跑通 vanilla_rag / hybrid_no_guardrails / full_system 三种配置
3. 每种配置输出完整 JSONL 结果
4. phase5_1_fullqa_ablation_report.md 生成完整对比表
5. final_eval_summary.md 增加 Full QA Ablation Section
6. final_project_report.md 增加 Full QA Ablation Discussion
7. README.md 增加 Full QA Ablation Summary
8. 不引入新的大模块，不破坏 v1.0 release 结果
```

建议输出文件：

```text
DocResearch/outputs/level2_ablation/techdocqa_vanilla_rag.jsonl
DocResearch/outputs/level2_ablation/techdocqa_hybrid_no_guardrails.jsonl
DocResearch/outputs/level2_ablation/techdocqa_full_system.jsonl
DocResearch/outputs/level2_ablation/garage_vanilla_rag.jsonl
DocResearch/outputs/level2_ablation/garage_hybrid_no_guardrails.jsonl
DocResearch/outputs/level2_ablation/garage_full_system.jsonl
DocResearch/reports/phase5_1_fullqa_ablation_report.md
```

---

## 10. 禁止事项

本阶段必须保持收口，不允许重新打开大开发。

禁止：

```text
1. 新增 clarification agent
2. 新增 memory 模块
3. 新增复杂 KG 构建
4. 重写 answer generator
5. 重写 retrieval pipeline
6. 引入新的大数据集
7. 为了提升指标修改 gold labels
8. 为了结果好看隐藏失败样本
```

允许：

```text
1. 增加 eval mode
2. 增加配置文件
3. 增加结果报告
4. 增加少量指标计算
5. 修复明显 eval bug
```

---

## 11. 推荐执行顺序

```text
Step 1：确认现有 level2_fullqa_eval.py 是否支持关闭 guardrails / judge / repair
Step 2：实现 --mode vanilla_rag / hybrid_no_guardrails / full_system
Step 3：先在 TechDocQA 5 条样本上 sanity check
Step 4：跑 TechDocQA 42 条三配置
Step 5：跑 GaRAGe 50 条三配置
Step 6：生成 phase5_1_fullqa_ablation_report.md
Step 7：更新 README / final_eval_summary / final_project_report
Step 8：检查最终叙事是否从“绝对指标”升级为“相对 baseline 提升”
Step 9：提交并打一个小版本 tag，例如 v1.1-fullqa-ablation
```

---

## 12. 最终阶段判断

Phase 5.1 不是为了继续扩大项目，而是为了补齐最终展示逻辑。

当前项目已经完成：

```text
能检索
能回答
能引用
能审查
能修复
能做鲁棒性测试
能人工审计
```

Phase 5.1 要补的是：

```text
能证明这些可靠性模块相比普通 RAG 到底带来了什么增益
```

完成后，最终结论可以从：

```text
Full System 达到 citation precision 0.952 / faithfulness 0.988
```

升级为：

```text
相比 Vanilla RAG / Hybrid RAG，Full System 在 citation precision、faithfulness、unsupported claim 控制和 repair 稳定性上取得可量化提升。
```

这会让项目报告、README 和简历表述更有说服力。
