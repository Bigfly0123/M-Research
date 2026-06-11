# DocResearch-Agent 正式 Eval Report 规划

## 0. 当前问题背景

当前 4 个数据集已经完成接入、转换、索引和端到端 sanity check：

| 数据集 | 定位 | eval 条数 | corpus | chunks/索引 | 当前状态 |
|---|---|---:|---:|---:|---|
| MultiHop-RAG | 多跳检索 | 100 | 2556 篇 | 2556 | pipeline 跑通，recall=1.00 |
| TechDocQA | 自建技术文档 QA | 42 | 9 篇 | 94 | 7 步 pipeline 跑通 |
| StratRAG | noisy candidate-pool 多跳检索 | 100 | 25203 篇 | 当前小索引 696 | pipeline 跑通，recall=1.00 |
| GaRAGe | grounding / citation | 50 | 2364 篇 | 当前小索引 550 | pipeline 跑通，recall=1.00 |

当前 `recall=1.00` 只能说明：

> 数据转换、索引加载、检索调用、gold evidence 对齐、eval runner 基本链路是通的。

它不能说明：

> 检索策略真的强，Graph Retriever 有明显收益，Evidence Composer 能抗干扰，Citation Guardrails 可靠。

主要原因是：

1. 当前索引规模偏小，尤其 StratRAG 只用了小索引而不是完整 25203 chunk corpus。
2. distractor 太少或太随机，不能模拟真实 noisy candidate-pool。
3. 样本量较小，10 条 sanity check 不能作为正式结论。
4. 还没有 dense、BM25、hybrid、hybrid_graph、agentic repair 的系统对比。
5. 还没有失败案例分析和成本/延迟分析。

因此，下一步应该进入正式 Eval Report 阶段。

---

## 1. 是否真的需要这么做？

需要，但不要一上来就做“最大规模全量实验”。

更合理的做法是：

> 分层正式评测：先做 Hard Setting，再做可选 Full Corpus Setting。

也就是说，不是马上把所有数据集都全量跑一遍，而是按优先级分三档。

---

## 2. 推荐评测层级

### Level 0：Sanity Check，已完成

目的：证明 pipeline 能跑通。

特点：

- 小样本；
- 小索引；
- 允许 recall 很高；
- 不作为正式性能结论。

当前状态：已完成。

报告中只能写：

```text
Pipeline sanity check passed on 4 datasets.
```

不要写成：

```text
The retriever achieves 100% recall.
```

---

### Level 1：Controlled Hard Setting，必须做

目的：在可控难度下比较不同检索策略。

这是正式报告最推荐的主实验。

#### StratRAG

使用每条 QA 原始 candidate pool：

```text
2 gold docs + 13 topical distractors = 15 candidate docs per query
```

为什么这样合理：

- 保留 StratRAG 原始设计的 topical distractor 难点；
- 比随机 500 distractor 更真实；
- 比全量 25203 索引更省资源；
- 适合快速做多策略消融。

#### MultiHop-RAG

使用当前 100 条 sample，但要确保：

- 不只检索 gold docs；
- corpus 至少包含完整 sample corpus；
- 可加入一定比例 distractor；
- 对比 dense / BM25 / hybrid / hybrid_graph。

#### TechDocQA

使用完整 42 条，完整 94 chunks。

TechDocQA 本身是小型真实技术文档集，不需要强行扩成很大。重点是：

- gold_chunk_recall；
- selected_evidence_recall；
- answer faithfulness；
- citation support；
- repair success。

#### GaRAGe

使用 50 条 sample。

重点不是 full QA，而是：

- grounding passage recall；
- evidence selection recall；
- citation support rate；
- faithfulness。

---

### Level 2：Full Corpus Setting，可选增强

目的：展示系统在更真实大索引中的表现。

建议只对 StratRAG 做，不要求 4 个数据集都做。

#### StratRAG Full Corpus

```text
索引：25203 chunks 全量索引
评测：sample 100
策略：dense / BM25 / hybrid / hybrid_graph
指标：recall@5, recall@10, all_gold_hit@10, MRR@10, latency
```

做这个的价值：

- 最能说明检索器在真实大 corpus 下是否有效；
- 能避免 “小索引导致 recall 虚高” 的质疑；
- 对简历和 README 包装很有说服力。

但它不是第一优先级。如果时间紧，可以只做 Level 1。

---

## 3. 总体规划

下一阶段目标：

> 生成正式 Eval Report，证明 DocResearch-Agent 的检索、证据选择、grounding、citation 和 repair 机制在多个数据集上有效。

不再新增数据集，不再增加复杂模块。

核心产物：

```text
reports/final_eval_summary.md
reports/multihop_rag/eval_report.md
reports/techdocqa/eval_report.md
reports/stratrag/eval_report.md
reports/garage/eval_report.md
reports/failure_cases/*.md
```

---

## 4. Phase A：补齐 Eval Configs

### 4.1 目录结构

建议整理为：

```text
eval/configs/
├── multihop_rag/
│   ├── dense_only.yaml
│   ├── bm25_only.yaml
│   ├── hybrid.yaml
│   ├── hybrid_graph.yaml
│   └── agentic_graph_repair.yaml
│
├── techdocqa/
│   ├── dense_only.yaml
│   ├── hybrid.yaml
│   ├── hybrid_graph.yaml
│   └── agentic_graph_repair.yaml
│
├── stratrag/
│   ├── dense_only.yaml
│   ├── bm25_only.yaml
│   ├── hybrid.yaml
│   ├── hybrid_graph.yaml
│   └── full_corpus_hybrid_graph.yaml
│
└── garage/
    ├── dense_only.yaml
    ├── hybrid.yaml
    ├── hybrid_graph.yaml
    └── citation_guarded.yaml
```

### 4.2 配置字段建议

每个 yaml 至少包含：

```yaml
dataset_name: stratrag
split: sample_100
corpus_path: data/processed/stratrag/corpus_docs.jsonl
chunks_path: data/processed/stratrag/chunks.jsonl
eval_path: data/processed/stratrag/eval_dataset_sample_100.jsonl
index_dir: data/indexes/stratrag/hybrid_graph
retrieval_mode: hybrid_graph
top_k: 10
use_graph: true
use_evidence_composer: true
use_generation: false
use_judge: false
use_repair: false
metrics:
  - gold_doc_recall@5
  - gold_doc_recall@10
  - all_gold_docs_hit@10
  - gold_chunk_recall@10
  - mrr@10
  - latency_ms
```

---

## 5. Phase B：Retrieval-only Eval，必须先做

### 5.1 为什么先做 retrieval-only？

因为 full QA 会引入 LLM 生成波动。先评估检索，可以更清楚地判断：

- dense 是否有效；
- BM25 是否补充 dense；
- hybrid 是否优于单路；
- graph expansion 是否提高多跳召回；
- 是否引入 graph noise。

### 5.2 数据集范围

必须跑：

```text
MultiHop-RAG sample 100
StratRAG sample 100 controlled hard setting
TechDocQA 42
GaRAGe 50
```

可选跑：

```text
StratRAG sample 100 full corpus setting
```

### 5.3 策略对比

每个检索型数据集至少跑：

```text
dense_only
bm25_only
hybrid
hybrid_graph
```

TechDocQA 和 GaRAGe 可以不跑 bm25_only，取决于工程成本。

### 5.4 指标

```text
gold_doc_recall@5
gold_doc_recall@10
all_gold_docs_hit@10
gold_chunk_recall@10
selected_evidence_recall
mrr@10
avg_latency_ms
avg_context_tokens
```

### 5.5 预期表格

报告中应该生成类似表格：

| dataset | setting | strategy | recall@5 | recall@10 | all_gold_hit@10 | MRR@10 | latency_ms |
|---|---|---|---:|---:|---:|---:|---:|
| StratRAG | hard_15_pool | dense | - | - | - | - | - |
| StratRAG | hard_15_pool | bm25 | - | - | - | - | - |
| StratRAG | hard_15_pool | hybrid | - | - | - | - | - |
| StratRAG | hard_15_pool | hybrid_graph | - | - | - | - | - |

---

## 6. Phase C：Full QA / Grounding Eval

Retrieval-only 跑完后，再跑 full QA。

### 6.1 TechDocQA：完整 7 步 pipeline

TechDocQA 是项目核心目标场景，应跑完整 pipeline：

```text
Context Planner
→ Hybrid + Graph Retriever
→ Retrieval Evaluator
→ Evidence Composer
→ Grounded Answer Generator
→ Self-Reflection Judge
→ Corrective Repair Router
→ Trace + Eval Runner
```

策略对比：

```text
dense_qa
hybrid_qa
hybrid_graph_qa
agentic_graph_repair_qa
```

指标：

```text
keyword_coverage
answer_relevance
faithfulness
citation_support_rate
judge_pass_rate
repair_trigger_rate
repair_success_rate
avg_latency_ms
avg_context_tokens
```

### 6.2 GaRAGe：grounding / citation eval

GaRAGe 不一定强调生成答案的主观质量，而是强调证据支持：

```text
grounding_hit_rate
selected_grounding_recall
citation_support_rate
faithfulness
unsupported_claim_rate
```

策略：

```text
hybrid
hybrid_graph
citation_guarded
agentic_repair，可选
```

---

## 7. Phase D：Failure Case Analysis

每个数据集至少抽取 5 个失败案例。

失败类型：

```text
retrieval_miss：gold evidence 没有被召回
graph_noise：graph expansion 引入无关 chunk
evidence_drop：召回了 gold，但 Evidence Composer 丢掉了
citation_error：答案引用了不支持的证据
answer_incomplete：答案缺少关键点
judge_false_positive：judge 误判通过
repair_failed：repair 后仍未解决
```

每个失败案例记录：

```json
{
  "question_id": "...",
  "question": "...",
  "gold_chunk_ids": ["..."],
  "retrieved_chunk_ids": ["..."],
  "selected_chunk_ids": ["..."],
  "answer": "...",
  "judge_result": "...",
  "failure_type": "retrieval_miss",
  "reason": "...",
  "possible_fix": "..."
}
```

生成文件：

```text
reports/failure_cases/multihop_rag_failure_cases.md
reports/failure_cases/techdocqa_failure_cases.md
reports/failure_cases/stratrag_failure_cases.md
reports/failure_cases/garage_failure_cases.md
```

---

## 8. Phase E：Final Eval Summary

最终总报告 `reports/final_eval_summary.md` 应包含：

```text
1. 项目评测目标
2. 四个数据集分别测试什么能力
3. 数据规模和设置
4. 检索策略对比
5. Full QA / grounding 结果
6. Graph Retriever 是否有效
7. Evidence Composer 是否有效
8. Citation Guardrails 是否有效
9. Corrective Repair 是否有效
10. 失败案例和局限性
11. 成本 / 延迟 trade-off
12. 最终结论
```

---

## 9. 最小可交付版本

如果时间紧，必须完成以下最小版本：

```text
1. StratRAG controlled hard setting：100 条，4 种检索策略
2. MultiHop-RAG：100 条，4 种检索策略
3. TechDocQA：42 条，完整 QA pipeline，至少 3 种策略
4. GaRAGe：50 条，grounding / citation eval，至少 2 种策略
5. final_eval_summary.md
6. 每个数据集 3～5 个失败案例
```

这个版本已经足够写进 README 和简历。

---

## 10. 推荐执行顺序

### Step 1：StratRAG controlled hard setting

目标：先修正最容易被质疑的 recall=1.00 问题。

任务：

```text
1. 使用每条 QA 原始 15 candidate docs。
2. 构建 hard_15_pool 索引或 per-query candidate pool 检索。
3. 跑 dense / bm25 / hybrid / hybrid_graph。
4. 输出 reports/stratrag/eval_report.md。
```

### Step 2：MultiHop-RAG retrieval-only

任务：

```text
1. 跑 dense / bm25 / hybrid / hybrid_graph。
2. 对比 multi-hop recall。
3. 输出 reports/multihop_rag/eval_report.md。
```

### Step 3：TechDocQA full pipeline

任务：

```text
1. 跑 dense_qa / hybrid_qa / hybrid_graph_qa / agentic_graph_repair_qa。
2. 输出 answer relevance / faithfulness / citation support / repair success。
3. 输出 reports/techdocqa/eval_report.md。
```

### Step 4：GaRAGe grounding / citation

任务：

```text
1. 跑 hybrid / hybrid_graph / citation_guarded。
2. 输出 grounding hit / citation support / faithfulness。
3. 输出 reports/garage/eval_report.md。
```

### Step 5：可选 StratRAG full corpus

如果前 4 步完成且时间允许：

```text
1. 构建 StratRAG 25203 chunks 全量索引。
2. 跑 sample 100。
3. 对比 controlled hard setting 和 full corpus setting。
4. 更新 reports/stratrag/eval_report.md。
```

---

## 11. 给 Agent 的具体执行 Prompt

```text
当前任务：进入 DocResearch-Agent 正式 Eval Report 阶段，不再新增数据集或新模块。

背景：
目前 4 个数据集 MultiHop-RAG、TechDocQA、StratRAG、GaRAGe 都已完成 raw → convert → corpus/chunks/eval → index → pipeline sanity check。当前 recall=1.00 只能说明 pipeline 跑通，不能作为正式性能结论，因为当前索引规模和 distractor 设置太简单。

目标：
构建正式评测流程，完成多策略对比、失败分析和最终报告。

必须完成：

1. 补齐 eval/configs/stratrag/ 和 eval/configs/garage/。
2. 为 StratRAG 实现 controlled hard setting：每条 QA 使用原始 15 candidate docs，即 2 gold + 13 topical distractors。
3. 对 MultiHop-RAG、StratRAG、TechDocQA、GaRAGe 跑 retrieval-only eval。
4. 对 TechDocQA 跑 full QA pipeline。
5. 对 GaRAGe 跑 grounding / citation eval。
6. 每个数据集输出 eval_report.md。
7. 输出 reports/final_eval_summary.md。
8. 每个数据集至少输出 3～5 个失败案例。

策略：
- dense_only
- bm25_only
- hybrid
- hybrid_graph
- agentic_graph_repair，主要用于 TechDocQA 和 GaRAGe

指标：
Retrieval:
- gold_doc_recall@5
- gold_doc_recall@10
- all_gold_docs_hit@10
- gold_chunk_recall@10
- selected_evidence_recall
- MRR@10

Generation / Grounding:
- keyword_coverage
- answer_relevance
- faithfulness
- citation_support_rate
- grounding_hit_rate
- selected_grounding_recall

Agent:
- judge_pass_rate
- repair_trigger_rate
- repair_success_rate

Cost:
- avg_latency_ms
- avg_context_tokens

执行顺序：
1. 先做 StratRAG controlled hard setting。
2. 再跑 MultiHop-RAG retrieval-only。
3. 再跑 TechDocQA full pipeline。
4. 再跑 GaRAGe grounding/citation。
5. 最后生成 final_eval_summary.md。

注意：
- 不要把当前 recall=1.00 写成正式性能结果。
- 不要继续新增数据集。
- 不要为了 full corpus 阶段阻塞主线。
- StratRAG full corpus 是可选增强，不是最小交付要求。
```

---

## 12. README / 简历包装建议

正式结果出来后，可以这样包装：

```text
构建统一 Eval Runner，接入 MultiHop-RAG、StratRAG、GaRAGe 和自建 TechDocQA 四类数据集，覆盖 multi-hop retrieval、noisy candidate-pool retrieval、grounding/citation 和真实技术文档 QA 场景。通过 dense-only、BM25、hybrid、hybrid+graph、agentic repair 多策略消融，评估 gold evidence recall、citation support、faithfulness、repair success、latency 和 context tokens，并生成 trace-level failure analysis。
```

---

## 13. 最终结论

当前不是重新规划项目，而是进入项目最关键的收口阶段：

```text
数据接入完成 → 正式 Eval → 消融对比 → 失败分析 → 报告包装
```

必须做的是：

```text
Controlled Hard Setting + 多策略对比 + Eval Report
```

可选做的是：

```text
StratRAG Full Corpus Setting
```

不建议做的是：

```text
继续加新数据集
继续堆新模块
为了全量索引拖慢正式报告
```

