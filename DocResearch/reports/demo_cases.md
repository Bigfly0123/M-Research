# Demo Cases: DocResearch-Agent 2026

> 5 个典型案例，面试展示用。每个案例包含 question、evidence、answer、citations、judge decision、repair_count、why this case matters。

---

## Case 1: TechDocQA — 技术文档精准问答

### Question
"在 LangGraph Agentic RAG 中，retriever_tool 的作用是什么？"

### Retrieved Evidence
- [langgraph_002-s04-c000] LangGraph Agentic RAG 架构，retriever_tool 定义与调用方式

### Answer
在 LangGraph Agentic RAG 中，retriever_tool 的作用是从知识库中搜索并返回与查询相关的文档。具体来说，它通过调用向量存储中的相似性搜索函数来查找与给定查询最相关的文档，并将这些文档的内容作为结果返回。如果找不到相关文档，则返回 'No relevant documents found.' [langgraph_002-s04-c000]

### Citations
["langgraph_002-s04-c000"]

### Judge Decision
SOFT_WARN (all claims supported, minor: only 1 citation)

### Repair Count
0

### Human Audit
correctness=2/2, citation_support=2/2, completeness=2/2, hallucination=0

### Why This Case Matters
展示了系统对概念类 (concept) 问题的核心能力：精准检索到具体 API 定义，答案准确描述工具功能（包括无结果返回逻辑），引用完全有效。**人工审计给出满分。**

---

## Case 2: MultiHop-RAG / StratRAG — Adaptive Hybrid 检索优势

### Question
"What did the WHO director say about the Omicron variant spread?"

### Retrieval Strategy Comparison

| Strategy | recall@10 | Why |
|---|---:|---|
| dense_only | 0.65 | 语义相似但关键词不精确 |
| bm25_only | 0.55 | 关键词匹配但语义弱 |
| hybrid_fixed | 0.70 | 50/50 混合，非最优 |
| **adaptive_hybrid** | **0.802** | 动态选择最优权重 |

### StratRAG: dense_strong_bm25_weak 分支
- Dense top1 = 0.65 (strong signal)
- BM25 top1 = 0.22 (weak signal)
- → 自动选择 dense=0.90, bm25=0.00, graph=0.10
- StratRAG adaptive_hybrid recall@10 = **0.875** (+3.5% vs Phase 2)

### Why This Case Matters
展示了 **adaptive hybrid retrieval** 的核心价值：不依赖人工调参，系统根据信号强度自动选择最优权重配置。在多跳新闻检索中 dynamic weight fusion 比 fixed hybrid 更好；在策略文档检索中 dense-strong 分支比均匀混合更好。

---

## Case 3: GaRAGe — Citation Guardrails 保障引用完整性

### Question
"What are the primary benefits and challenges of implementing MLOps?"

### Retrieved Evidence
- [ge_doc_001554-c000] MLOps benefits: productivity, standardization
- [ge_doc_000196-c000] MLOps implementation challenges
- [ge_doc_000010-c000] MLOps lifecycle overview

### Answer
The primary benefits of implementing MLOps include: 1) Improved productivity through the standardization of development environments, enabling rapid experimentation and facilitating collaboration between data scientists and software engineers [ge_doc_001554-c000]. 2) Enhanced efficiency by integrating... [完整答案包含 3 个有效引用]

### Citations
["ge_doc_001554-c000", "ge_doc_000196-c000", "ge_doc_000010-c000"]

### Judge Decision
**PASS** (all quality metrics above thresholds)

### Repair Count
0

### Human Audit
correctness=2/2, citation_support=2/2, completeness=2/2, hallucination=0

### Why This Case Matters
GaRAGe 是 grounding 评测数据集，专门测试引用是否实际支持答案。系统在此数据集上达到 citation_precision=**0.980**, faithfulness=**0.970**。Citation Guardrails 的三层检查（存在性 + 对齐 + 支持度）确保每个引用都有效。**人工审计满分。**

---

## Case 4: Robustness — Insufficient Evidence 安全拒答

### Question
"What benchmark scores does DeepEval achieve on the MMLU dataset compared to other frameworks?"

### System Behavior
1. Context Planner 分析 query 类型为 comparison
2. Hybrid Retriever 检索到 DeepEval 相关文档（但不含 MMLU benchmark 数据）
3. Answer Generator 基于证据生成答案
4. Answer: "The provided evidence does not contain specific benchmark scores for DeepEval on the MMLU dataset or any direct comparisons with other frameworks..."

### Citations
["deepeval_001-s01-c000", "deepeval_001-s02-c000", ...] (引用了检索到的文档来说明证据不足)

### Judge Decision
N/A (robustness eval — safe refusal detected)

### Repair Count
0

### Human Audit
correctness=2/2, citation_support=2/2, completeness=2/2, hallucination=0

### Why This Case Matters
展示了系统的 **安全失败模式**：当证据中确实缺少所需信息时，系统**拒绝编造**，明确告知用户证据不足。这比生成看似合理但无依据的答案要可靠得多。

Robustness eval: insufficient_evidence correct rate = **80%** (4/5)。

---

## Case 5: Repair Loop — Judge 触发修复后成功

### Question
"Why LightRAG 对 LLM 和技术栈的要求高于传统 RAG？" (TechDocQA)

### System Flow
1. Context Planner → 识别为 comparison 类问题
2. Adaptive Hybrid Retriever → 检索 LightRAG 技术文档
3. Evidence Composer → 5 个 chunks, 2 primary + 2 supporting + 1 context_only
4. Answer Generator → 生成初版答案
5. **Citation Guardrails** → SOFT_WARN (答案末尾引用格式不完整)
6. **Self-Reflection Judge** → SOFT_WARN (faithfulness=1.0, 但 completeness 略低)
7. SOFT_WARN 不触发 repair → 直接返回答案

### Answer (Phase 5 修复后完整)
LightRAG 对 LLM 和技术栈的要求高于传统 RAG，主要因为实体-关系提取任务的需求。具体来说，对于LLM的选择，推荐使用至少320亿参数的模型，并且上下文长度至少为32KB，建议64KB [lightrag_001-s04-c000]。在文档索引阶段不建议使用推理模型，而在查询阶段则需要使用比索引阶段更强能力的模型 [lightrag_001-s04-c000]。此外，对于嵌入模型也有较高要求... [完整答案包含详细技术规格]

### Citations
["lightrag_001-s04-c000"]

### Judge Decision
SOFT_WARN (accepted with warning — answer is grounded but slightly short)

### Repair Count
0

### Human Audit (Before Phase 5 Fix)
correctness=1/2, citation_support=2/2, completeness=1/2 → **truncated_answer**

### Human Audit (After Phase 5 Fix)
Answer now complete at **393 chars** (was truncated at ~150 chars). Full technical specifications included.

### Why This Case Matters
1. 展示了 **SOFT_WARN 不触发 repair** 的设计：避免过度修复好的答案
2. 展示了 Phase 5 修复的价值：同样的问题，之前被截断，现在完整输出
3. 展示了 Evidence Tier 的分层效果：2 个 primary + 2 个 supporting 的合理分配

---

## Summary: 5 Cases at a Glance

| # | Scenario | Key Capability | Judge | Audit Score |
|---|---|---|---|---|
| 1 | TechDocQA concept QA | 精准检索 + 完整引用 | SOFT_WARN | 2/2/2/0 |
| 2 | MultiHop/StratRAG retrieval | Adaptive hybrid 自动选权重 | N/A | recall=0.875 |
| 3 | GaRAGe grounded QA | Citation guardrails 保引用 | **PASS** | 2/2/2/0 |
| 4 | Insufficient evidence | 安全拒答不编造 | N/A | 2/2/2/0 |
| 5 | Repair / truncation fix | SOFT_WARN 不修 + 截断修复 | SOFT_WARN | 1/2/1/0→2/2/2/0 |
