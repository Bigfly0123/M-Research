# DocResearch-Agent 2026 下一阶段推进计划

> 项目：DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统  
> 当前阶段：Level 1 Retrieval Eval 已完成初步跑通  
> 本文目标：根据四个数据集的检索评测结果，明确当前问题、下一步改进路线、agent 执行任务与验收标准。

---

## 0. 当前结论先行

当前不能简单判断为“框架没有效果”。更准确的结论是：

1. **Hybrid 检索有条件有效**  
   在 StratRAG 上，hybrid 明显优于 bm25_only，也略优于 dense_only，说明 dense 与 BM25 在结构化复杂文档场景中存在互补。

2. **固定融合策略存在负作用**  
   在 MultiHop-RAG 上，bm25_only 是当前最强策略，hybrid 反而低于 BM25，说明固定 RRF / 固定权重融合会把强 BM25 信号稀释掉。

3. **当前 lightweight graph expansion 没有稳定收益**  
   hybrid_graph 在四个数据集上基本等于 hybrid，甚至在 MultiHop-RAG 上略降，说明当前基于术语共现的轻量图扩展还没有真正发挥作用。

4. **TechDocQA 与 GaRAGe 的 Retrieval 区分度不足**  
   TechDocQA 和 GaRAGe 的 recall 已接近满分，不能再主要用于证明检索模块差异。它们更适合用于 Level 2 / Level 3 的答案质量、citation、grounding、judge、repair 评测。

5. **Level 1 只评估了检索，不等于完整 Agentic GraphRAG 评估**  
   当前结果主要验证 dense、BM25、hybrid、graph retrieval。Context Planner、Evidence Composer、Grounded Answer、Citation Guardrails、Self-Reflection Judge、Repair Router 的价值还没有被正式评估。

因此，下一阶段不要继续堆模块，而是要把系统从：

```text
固定 hybrid + always-on graph
```

调整为：

```text
adaptive hybrid + selective graph + full QA reliability eval
```

---

## 1. 当前 Level 1 Retrieval Eval 汇总

| 数据集 | 策略 | r@5 | r@10 | all_hit@10 | MRR@10 | 延迟 |
|---|---:|---:|---:|---:|---:|---:|
| MultiHop-RAG | dense_only | 0.516 | 0.656 | 0.360 | 0.608 | 598ms |
| MultiHop-RAG | bm25_only | 0.548 | 0.707 | 0.410 | 0.627 | 47ms |
| MultiHop-RAG | hybrid | 0.503 | 0.656 | 0.360 | 0.604 | 352ms |
| MultiHop-RAG | hybrid_graph | 0.503 | 0.640 | 0.350 | 0.602 | 375ms |
| TechDocQA | dense_only | 0.988 | 1.000 | 1.000 | 0.964 | 914ms |
| TechDocQA | bm25_only | 1.000 | 1.000 | 1.000 | 0.964 | 20ms |
| TechDocQA | hybrid | 0.988 | 1.000 | 1.000 | 0.964 | 314ms |
| TechDocQA | hybrid_graph | 0.988 | 1.000 | 1.000 | 0.964 | 331ms |
| StratRAG | dense_only | 0.835 | 0.905 | 0.830 | 0.941 | 563ms |
| StratRAG | bm25_only | 0.755 | 0.820 | 0.720 | 0.886 | 26ms |
| StratRAG | hybrid | 0.845 | 0.925 | 0.870 | 0.946 | 336ms |
| StratRAG | hybrid_graph | 0.845 | 0.925 | 0.870 | 0.946 | 317ms |
| GaRAGe | dense_only | 1.000 | 1.000 | 1.000 | 1.000 | 945ms |
| GaRAGe | bm25_only | 0.960 | 0.960 | 0.960 | 0.960 | 21ms |
| GaRAGe | hybrid | 1.000 | 1.000 | 1.000 | 1.000 | 311ms |
| GaRAGe | hybrid_graph | 1.000 | 1.000 | 1.000 | 1.000 | 307ms |

---

## 2. 数据集分工重新定义

后续不要把四个数据集都当成同一种检索评测数据集。每个数据集承担不同作用。

### 2.1 MultiHop-RAG

定位：检索难度最高的数据集，用于测试多跳文档召回和融合策略稳定性。

当前现象：

```text
bm25_only > dense_only ≈ hybrid > hybrid_graph
```

说明：

- BM25 对 MultiHop-RAG 当前样本更有效。
- Dense 检索引入了噪声。
- 固定 hybrid 不能保证不退化。
- 当前 graph expansion 在该数据集上没有帮助。

后续用途：

```text
主要用于 adaptive_hybrid 的压力测试。
目标不是让 graph 强行提升，而是至少让 adaptive_hybrid 不低于 bm25_only。
```

---

### 2.2 StratRAG

定位：当前最能体现 hybrid 检索收益的数据集。

当前现象：

```text
hybrid r@10 = 0.925
bm25_only r@10 = 0.820
```

说明：

- Dense 与 BM25 在该数据集上存在互补。
- Hybrid 是 Level 1 当前最有说服力的正向结果。

后续用途：

```text
作为 Level 1 Retrieval 的主展示数据集。
用于证明 adaptive_hybrid 不能破坏原有 hybrid 优势。
```

---

### 2.3 TechDocQA

定位：自建技术文档 QA 主数据集。

当前现象：

```text
r@10 基本满分
```

说明：

- 检索任务偏简单。
- 不适合继续用来证明 retrieval 差异。

后续用途：

```text
用于 Level 2 Full QA Eval。
重点评估答案正确性、引用准确性、faithfulness、unsupported claims、repair 效果。
```

---

### 2.4 GaRAGe

定位：Grounding / citation 评测数据集。

当前现象：

```text
dense / hybrid / hybrid_graph 均接近满分
```

说明：

- 检索区分度不足。
- 适合从 retrieval eval 转向 grounded answer eval。

后续用途：

```text
用于 Level 3 Reliability Eval。
重点评估 citation coverage、citation precision、evidence support、guardrails 和 repair。
```

---

## 3. 下一阶段总目标

下一阶段不再追求“所有模块都必须在 recall@10 上提升”。

新的目标是：

```text
让系统学会什么时候用 BM25，什么时候用 Dense，什么时候用 Hybrid，什么时候才需要 Graph。
```

也就是说，项目叙事从：

```text
GraphRAG 一定提升检索
```

改为：

```text
Agentic Retrieval 通过 planner/evaluator 自适应选择检索策略，避免固定融合和 always-on graph 带来的退化。
```

这是更合理、更高级、也更可信的方向。

---

## 4. Phase 2.1：Retrieval Diagnosis

### 4.1 目标

先不要急着优化分数。第一步要解释清楚：

```text
Graph 为什么没提升？
Hybrid 为什么在 MultiHop-RAG 上低于 BM25？
Dense 和 BM25 的互补到底发生在哪些样本上？
```

### 4.2 样本范围

建议先选：

```text
MultiHop-RAG：20 条失败或退化样本
StratRAG：10 条 hybrid 有收益样本
```

总计 30 条，足够诊断，不要全量分析。

### 4.3 输出文件

需要新增或生成：

```text
reports/level1_retrieval_diagnosis.md
outputs/diagnosis/multihop_graph_failures.jsonl
outputs/diagnosis/stratrag_hybrid_success_cases.jsonl
outputs/diagnosis/retrieval_case_traces.jsonl
```

### 4.4 每条 case 需要记录的字段

```json
{
  "dataset": "multihop_rag",
  "query_id": "...",
  "query": "...",
  "gold_doc_ids": [],
  "dense_top10_doc_ids": [],
  "bm25_top10_doc_ids": [],
  "hybrid_top10_doc_ids": [],
  "hybrid_graph_top10_doc_ids": [],
  "dense_hit": true,
  "bm25_hit": true,
  "hybrid_hit": false,
  "hybrid_graph_hit": false,
  "graph_expanded_terms": [],
  "graph_candidate_chunk_ids": [],
  "graph_candidate_doc_ids": [],
  "graph_entered_top10_count": 0,
  "graph_hit_gold_count": 0,
  "failure_type": "...",
  "diagnosis_note": "..."
}
```

### 4.5 failure_type 建议分类

```text
bm25_strong_dense_noise
hybrid_fusion_dilution
graph_no_expansion
graph_expansion_noise
graph_candidate_not_enter_top10
graph_metadata_mapping_error
gold_doc_id_mapping_error
query_requires_exact_keyword
query_requires_semantic_match
insufficient_gold_annotation
```

### 4.6 验收标准

Phase 2.1 完成后，必须能回答：

1. graph 是否真的扩展出了候选？
2. graph 扩展候选中是否有 gold doc？
3. 如果 graph 有 gold，为什么没有进 final top10？
4. MultiHop-RAG 上 hybrid 退化主要是 dense 噪声，还是 fusion 策略问题？
5. StratRAG 上 hybrid 成功样本具有什么共同特征？

---

## 5. Phase 2.2：实现 adaptive_hybrid

### 5.1 目标

新增一个策略：

```text
adaptive_hybrid
```

它不是固定融合 dense 和 BM25，而是根据 query 和检索置信信号动态选择权重。

目标：

```text
MultiHop-RAG：不低于 bm25_only
StratRAG：保留 hybrid 优势
TechDocQA / GaRAGe：不退化
```

### 5.2 为什么必须做

当前 MultiHop-RAG 的结果说明：

```text
bm25_only r@10 = 0.707
hybrid r@10 = 0.656
```

固定 hybrid 已经产生退化。后续如果继续固定 RRF，会导致系统无法自圆其说。

### 5.3 初版 adaptive 规则

先不要用 LLM。用轻量统计信号即可。

建议提取以下信号：

```text
query_length
capitalized_terms_count
code_like_terms_count
has_api_pattern
has_exact_entity
bm25_top1_score
bm25_top1_top5_gap
dense_top1_score
dense_top1_top5_gap
dense_bm25_overlap_at_10
```

### 5.4 策略逻辑草案

```python
if query_has_many_exact_terms or bm25_confidence_high:
    use bm25_dominant_fusion
elif dense_confidence_high and bm25_confidence_low:
    use dense_dominant_fusion
elif dense_bm25_overlap_high:
    use balanced_hybrid
else:
    use hybrid_with_diversity_control
```

其中：

```text
bm25_dominant_fusion: BM25 权重大，Dense 只补充不覆盖
balanced_hybrid: 接近当前 hybrid
hybrid_with_diversity_control: 防止 dense 低质量结果挤掉 BM25 高质量结果
```

### 5.5 实现位置建议

可以新增：

```text
DocResearch/app/retrieval/adaptive_hybrid_retriever.py
DocResearch/app/retrieval/query_analyzer.py
```

也可以在现有 `hybrid_retriever.py` 中增加 strategy 参数：

```text
strategy = dense_only | bm25_only | hybrid | hybrid_graph | adaptive_hybrid
```

建议优先保持结构简单，不要大拆。

### 5.6 输出报告

新增：

```text
reports/level1_adaptive_hybrid_report.md
```

表格需要包含：

```text
dense_only
bm25_only
hybrid
adaptive_hybrid
hybrid_graph
```

### 5.7 验收标准

最低验收线：

```text
MultiHop-RAG adaptive_hybrid r@10 >= 0.707
StratRAG adaptive_hybrid r@10 >= 0.925 或不明显低于 0.925
TechDocQA adaptive_hybrid r@10 = 1.000
GaRAGe adaptive_hybrid r@10 = 1.000
```

如果不能达到，也必须通过 diagnosis report 解释退化原因。

---

## 6. Phase 2.3：Graph 改为 selective_graph

### 6.1 当前问题

当前 hybrid_graph 是 always-on graph expansion。结果显示：

```text
hybrid_graph ≈ hybrid
MultiHop-RAG 上 hybrid_graph 还略低于 hybrid
```

说明 graph 不应该默认启用。

### 6.2 新目标

新增策略：

```text
selective_graph
```

它只在需要的时候触发 graph expansion。

### 6.3 触发条件

满足以下任一条件时可以触发 graph：

```text
1. query 中存在多个技术术语或实体
2. query 包含 compare / difference / relation / workflow / dependency / how / why 等多跳或关系型意图
3. dense 和 BM25 的 top-k 结果覆盖不足
4. dense 与 BM25 分歧大，且各自置信度都不高
5. Retrieval Evaluator 判断当前 evidence insufficient
6. Level 2 full QA 中 citation coverage 不足，需要补充证据
```

### 6.4 Graph 结果加入方式

不要让 graph 候选直接强行进入 top-k。

建议采用：

```text
先跑 adaptive_hybrid 得到 base_topk
再跑 graph expansion 得到 graph_candidates
只保留同时满足以下条件的 graph candidates：
  - 与 query terms 有交集
  - 与 base_topk 中的核心术语有交集
  - source_doc 不重复过多
  - score 达到最小阈值
最后以 evidence supplement 的方式加入，而不是覆盖 base retrieval
```

### 6.5 输出报告

新增：

```text
reports/level1_selective_graph_report.md
outputs/diagnosis/selective_graph_trigger_cases.jsonl
```

报告需要说明：

```text
触发了多少 query
触发 query 中有多少提升
触发 query 中有多少退化
未触发 query 是否保持不变
Graph candidates 进入 final context 的比例
Graph candidates 命中 gold 的比例
```

### 6.6 验收标准

最低目标：

```text
selective_graph 不应该显著低于 adaptive_hybrid
在至少一个需要跨概念补证据的子集上，selective_graph 有可解释收益
```

如果 recall@10 没提升，也可以接受，但必须在 Level 2 中证明：

```text
selective_graph 提升了答案完整性、citation coverage 或 evidence support
```

---

## 7. Phase 2.4：Level 2 Full QA Eval

### 7.1 目标

Level 1 只能证明检索召回。DocResearch-Agent 的核心卖点是可靠问答，因此必须做 Level 2。

Level 2 要评估：

```text
检索到上下文之后，答案是否正确、完整、有引用、少幻觉。
```

### 7.2 数据集

优先使用：

```text
TechDocQA：42 条，全量跑 full QA
GaRAGe：50 条，抽样跑 full QA / grounded QA
```

不要一开始跑 MultiHop-RAG 全量 full QA，成本和调试压力太大。

### 7.3 对比策略

建议对比：

```text
baseline_vector_fullqa
bm25_fullqa
hybrid_fullqa
adaptive_hybrid_fullqa
adaptive_selective_graph_fullqa
```

如果时间不足，至少对比：

```text
baseline_vector_fullqa
hybrid_fullqa
adaptive_selective_graph_fullqa
```

### 7.4 指标

建议记录：

```text
answer_correctness
answer_completeness
citation_precision
citation_coverage
faithfulness
unsupported_claim_rate
refusal_correctness
latency
cost_estimate
```

### 7.5 full QA 输出格式

每条样本输出：

```json
{
  "dataset": "techdocqa",
  "query_id": "...",
  "query": "...",
  "gold_answer": "...",
  "retrieval_strategy": "adaptive_selective_graph",
  "retrieved_contexts": [],
  "answer": "...",
  "citations": [],
  "citation_guardrail_pass": true,
  "judge_score": {
    "correctness": 0.0,
    "completeness": 0.0,
    "faithfulness": 0.0,
    "citation_quality": 0.0
  },
  "unsupported_claims": [],
  "repair_count": 0,
  "final_status": "pass"
}
```

### 7.6 验收标准

Phase 2.4 完成后，需要得到：

```text
reports/level2_fullqa_report.md
outputs/fullqa/techdocqa_fullqa_results.jsonl
outputs/fullqa/garage_fullqa_results.jsonl
```

报告中必须回答：

1. 更好的 retrieval 是否带来更好的答案？
2. citation guardrails 是否能发现无引用或错引用？
3. judge 是否能识别 unsupported claims？
4. repair router 是否真的修复了部分失败？
5. adaptive_selective_graph 是否在答案质量上优于 baseline？

---

## 8. Phase 2.5：Level 3 Reliability Eval

### 8.1 目标

证明系统不是只会答题，而是具有可靠性控制能力。

重点评估：

```text
Citation Guardrails
Self-Reflection Judge
Repair Router
```

### 8.2 构造失败场景

可以从 TechDocQA / GaRAGe 中选 20 条，人工或程序构造以下情况：

```text
1. 缺少 citation
2. citation 指向错误 context
3. answer 包含 context 不支持的 claim
4. retrieved context 不足
5. 多个 context 冲突
6. question 超出文档范围，需要拒答
```

### 8.3 指标

```text
guardrail_detection_rate
judge_detection_rate
repair_attempt_rate
repair_success_rate
false_positive_rate
unsupported_claim_reduction
citation_error_reduction
```

### 8.4 验收标准

生成：

```text
reports/level3_reliability_report.md
outputs/reliability/reliability_eval_cases.jsonl
```

报告需要证明：

```text
系统能够发现部分不可靠答案，并通过 repair 降低 unsupported claims 或 citation errors。
```

注意：不要求 repair 100% 成功，但必须有可解释案例。

---

## 9. 代码修改任务清单

### Task A：Retrieval trace 增强

需要记录每路检索结果：

```text
dense_candidates
bm25_candidates
graph_candidates
final_candidates
fusion_scores
source_strategy
```

输出到：

```text
outputs/traces/retrieval_traces.jsonl
```

---

### Task B：Graph metadata 检查

重点检查：

```text
graph result 是否有 chunk_id
graph result 是否有 doc_id
graph result 是否有 text
graph result 是否有 source
graph result 是否能参与 final ranking
load_index 后 _chunks_by_id 是否为空
```

如果 `load_index()` 后 graph 只能返回 chunk_id 但拿不到正文，必须修复。

---

### Task C：Adaptive Hybrid

新增或扩展：

```text
query_analyzer.py
adaptive_hybrid_retriever.py
```

或在现有 hybrid retriever 中加入：

```text
strategy="adaptive_hybrid"
```

---

### Task D：Selective Graph

新增：

```text
strategy="selective_graph"
```

不要删除原来的 `hybrid_graph`，它要作为 ablation baseline 保留。

---

### Task E：Full QA eval 接入 LangGraph workflow

当前如果 full_qa 仍然只是 retrieval，不算完成。

必须真正调用：

```text
create_graph()
graph.invoke(initial_state)
```

并记录：

```text
answer
citations
context_pack
judge_result
guardrail_result
repair_count
trace
```

---

## 10. 实验报告结构建议

最终应该形成一份统一报告：

```text
reports/docresearch_phase2_eval_report.md
```

结构：

```markdown
# DocResearch-Agent Phase 2 Evaluation Report

## 1. Experiment Setup
- datasets
- sample size
- strategies
- metrics

## 2. Level 1 Retrieval Eval
- dense_only / bm25_only / hybrid / adaptive_hybrid / hybrid_graph / selective_graph
- per-dataset results
- latency comparison

## 3. Retrieval Diagnosis
- MultiHop-RAG failure analysis
- StratRAG hybrid success cases
- graph expansion diagnosis

## 4. Level 2 Full QA Eval
- answer correctness
- citation quality
- faithfulness
- unsupported claims

## 5. Level 3 Reliability Eval
- guardrail detection
- judge detection
- repair success

## 6. Key Findings
- hybrid 有条件有效
- fixed fusion 会退化
- always-on graph 无稳定收益
- selective graph 更合理
- reliability modules 的贡献

## 7. Limitations
- TechDocQA/GaRAGe retrieval ceiling effect
- lightweight graph is still shallow
- LLM judge has subjectivity
- sample size limited

## 8. Next Steps
```

---

## 11. 下一阶段禁止事项

为了避免项目继续变乱，后续禁止：

```text
1. 不要继续新增 agent 模块
2. 不要直接上复杂知识图谱
3. 不要为了证明 graph 有效而强行调高 graph 权重
4. 不要修改 gold label 来迎合结果
5. 不要用 TechDocQA/GaRAGe 的满分结果吹 retrieval
6. 不要全量跑大数据集浪费时间
7. 不要把 Level 1 retrieval 结果包装成完整系统效果
8. 不要让 repair router 变成无条件重跑
```

---

## 12. 推荐执行顺序

建议严格按下面顺序执行：

```text
Step 1：补 retrieval trace 和 diagnosis 输出
Step 2：修 graph metadata / load_index 潜在问题
Step 3：生成 level1_retrieval_diagnosis.md
Step 4：实现 adaptive_hybrid
Step 5：重跑四个数据集 Level 1 retrieval eval
Step 6：实现 selective_graph
Step 7：重跑 selective_graph ablation
Step 8：接通 full_qa eval
Step 9：跑 TechDocQA 42 条 full QA
Step 10：跑 GaRAGe 50 条 grounding / citation eval
Step 11：构造 Level 3 reliability cases
Step 12：生成 phase2_eval_report.md
```

不要跳过 Step 1 和 Step 2。当前最重要的是先弄清楚退化原因。

---

## 13. 给 Coding Agent 的简短执行提示词

可以直接把下面这段发给 coding agent：

```text
当前 DocResearch-Agent 已完成 Level 1 Retrieval Eval。结果显示 hybrid 在 StratRAG 有收益，但在 MultiHop-RAG 低于 bm25_only；hybrid_graph 在四个数据集上几乎无增益，说明当前 always-on lightweight graph expansion 无效或被 fusion 抑制。请不要新增复杂模块，也不要强行调高 graph 权重。

下一步按以下顺序执行：
1. 增强 retrieval trace，记录 dense、bm25、graph、final top-k、fusion score、doc_id、chunk_id、source_strategy。
2. 检查并修复 graph metadata / load_index 问题，确保 graph result 有 chunk_id、doc_id、text、source，并能正确参与 final ranking。
3. 生成 reports/level1_retrieval_diagnosis.md，重点分析 MultiHop-RAG hybrid 退化和 graph 无增益原因。
4. 实现 adaptive_hybrid 策略，目标是在 MultiHop-RAG 不低于 bm25_only，同时在 StratRAG 保留 hybrid 优势。
5. 实现 selective_graph 策略，不再 always-on graph，只在多术语、多跳、证据不足、dense/BM25 低置信或 evaluator 判定 insufficient 时触发。
6. 重跑 Level 1 eval，对比 dense_only、bm25_only、hybrid、adaptive_hybrid、hybrid_graph、selective_graph。
7. 接通 full_qa eval，真正调用 LangGraph workflow，记录 answer、citations、guardrail、judge、repair_count 和 trace。
8. 使用 TechDocQA 42 条和 GaRAGe 50 条评估 answer quality、citation、faithfulness、unsupported claims 和 repair success。

禁止事项：不要新增新 agent；不要复杂化 KG；不要修改 gold；不要用 TechDocQA/GaRAGe retrieval 满分证明模块有效；不要将 Level 1 retrieval 结果包装成完整系统效果。
```

---

## 14. 阶段验收总表

| 阶段 | 输出文件 | 验收标准 |
|---|---|---|
| Phase 2.1 Diagnosis | `reports/level1_retrieval_diagnosis.md` | 能解释 MultiHop 退化和 graph 无增益原因 |
| Phase 2.2 Adaptive Hybrid | `reports/level1_adaptive_hybrid_report.md` | MultiHop 不低于 BM25，StratRAG 保留 hybrid 优势 |
| Phase 2.3 Selective Graph | `reports/level1_selective_graph_report.md` | 不显著退化，并有可解释的触发/收益案例 |
| Phase 2.4 Full QA | `reports/level2_fullqa_report.md` | TechDocQA/GaRAGe 完整 QA、citation、judge 指标跑通 |
| Phase 2.5 Reliability | `reports/level3_reliability_report.md` | guardrail/judge/repair 有检测与修复案例 |
| Final Report | `reports/docresearch_phase2_eval_report.md` | 形成完整项目阶段性结论 |

---

## 15. 最终阶段目标

这一阶段完成后，项目应该能形成如下结论：

```text
1. 固定 hybrid 并不总是可靠，在 BM25 强势数据集上可能退化。
2. 轻量 always-on graph expansion 没有稳定提升，因此不能把 GraphRAG 当成无条件增强器。
3. Adaptive retrieval 能根据 query 和检索置信动态选择策略，从而减少退化。
4. Selective graph 比 always-on graph 更符合 Agentic Retrieval 设计，只在多跳、跨概念、证据不足时作为补充工具。
5. TechDocQA 和 GaRAGe 的主要价值不在 retrieval recall，而在 full QA、citation、grounding 和 repair reliability。
6. DocResearch-Agent 的最终价值不是单个检索指标，而是“可规划、可检索、可引用、可审查、可修复、可评测”的可靠技术文档问答闭环。
```

这比简单宣称“GraphRAG 提升 recall”更可信，也更适合项目展示和后续写简历。
