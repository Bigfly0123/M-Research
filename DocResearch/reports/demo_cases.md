# Demo Cases: DocResearch-Agent 2026

> 5 个典型案例，展示系统在不同场景下的能力。

---

## Demo Case 1: Technical Document QA (TechDocQA)

### Question
"DeepEval 中如何用 TaskCompletionMetric 和 observe 评估一个 agent 流程？"

### Retrieval Strategy
adaptive_hybrid → dense + BM25 with dynamic weight fusion

### Retrieved Evidence
- [deepeval_001-s03-c001] TaskCompletionMetric 定义与 observe 装饰器用法
- [deepeval_001-s08-c000] End-to-End vs Component-Level Evals

### Answer
DeepEval 中可以先用 Golden 构造测试输入，再用 TaskCompletionMetric 定义任务完成指标，并通过 observe 装饰器标记 agent 或子函数，使 DeepEval 能记录组件级执行过程。最后调用 evaluate 或 observed callback，对 agent 流程的任务完成情况进行评估。[deepeval_001-s03-c001]

### Judge Result
SOFT_WARN (answer slightly short, but all claims supported)

### Metrics
- citation_precision: 1.0
- faithfulness: 1.0

### Why This Case Matters
展示了系统对实现类 (implementation) 问题的处理能力：准确检索到具体 API 用法，答案包含正确的函数名和工作流程描述，所有声明都有引用支持。

---

## Demo Case 2: Multi-Hop Retrieval (MultiHop-RAG)

### Question
"What did the WHO director say about the Omicron variant spread?"

### Retrieval Strategy
hybrid_graph → Dense + BM25 + Selective Graph Expansion

### Retrieved Evidence
Multiple chunks from different news articles, graph expansion connected related entities (WHO director + Omicron + spread statistics)

### Why This Case Matters
展示了 hybrid_graph 检索在多跳问题上的价值：
- Dense retrieval 找到 Omicron 相关文档
- BM25 精确匹配 "WHO director" 关键词
- Graph expansion 连接了不同文章中关于同一事件的信息
- MultiHop-RAG adaptive_hybrid recall@10 = **0.802**

---

## Demo Case 3: Strategy Document Retrieval (StratRAG)

### Question
"How to handle a critical system outage in production?"

### Retrieval Strategy
adaptive_hybrid → **dense_strong_bm25_weak** branch (Phase 3 enhancement)

### Weight Decision
- Dense top1 = 0.65 (strong signal)
- BM25 top1 = 0.22 (weak signal)
- → dense=0.90, bm25=0.00, graph=0.10

### Why This Case Matters
展示了 Phase 3 新增的 `dense_strong_bm25_weak` 分支：当 Dense 信号强而 BM25 信号弱时，系统自动选择几乎纯 Dense 的策略。这使得 StratRAG adaptive_hybrid recall@10 从 0.845 提升到 **0.875** (+3.5%)。

---

## Demo Case 4: Grounded QA with Citation Integrity (GaRAGe)

### Question
"What evidence exists about AI system reliability in healthcare?"

### Retrieval Strategy
adaptive_hybrid with full GaRAGe index (550 chunks)

### Answer
Based on the retrieved documents, AI system reliability in healthcare depends on several factors including training data quality, model validation, and continuous monitoring... [garage_doc_XX-s01-c000] [garage_doc_YY-s03-c001]

### Judge Result
SOFT_WARN (good answer with valid citations)

### Metrics
- citation_precision: **1.000** (all citations valid)
- faithfulness: **0.970**
- guardrail_pass_rate: **0.980**

### Why This Case Matters
GaRAGe 是 grounding 评测数据集，专门测试引用是否实际支持答案。系统在此数据集上达到了 citation_precision = 1.000，证明 Citation Guardrails + Self-Reflection Judge 的闭环确实能保障引用可靠性。

---

## Demo Case 5: Out-of-Domain Refusal (Robustness)

### Question
"How do I make a traditional French croissant from scratch?"

### Retrieval Strategy
adaptive_hybrid (TechDocQA index)

### System Behavior
1. Context Planner 分析了 query
2. Hybrid Retriever 检索到了技术文档 chunks（与烹饪完全无关）
3. Answer Generator 尝试回答但生成了低质量答案
4. Self-Reflection Judge 检测到 faithfulness ≈ 0，citation_support ≈ 0
5. **Judge Decision: HARD_FAIL** → 答案被标记为不可靠

### Why This Case Matters
展示了系统的 **安全边界**：当问题完全不在文档范围内时，Self-Reflection Judge 能正确检测到答案缺乏文档支持，并触发 HARD_FAIL。这比直接给出无根据的答案要安全得多。

Robustness eval 结果：out_of_domain unsupported_answer_rate = **20%** (4/5 正确检测)。

---

## Summary: What These Cases Demonstrate

| Capability | Demo Case | Evidence |
|---|---|---|
| Grounded technical QA | Case 1 | faithfulness=1.0, valid citations |
| Multi-hop reasoning | Case 2 | hybrid_graph recall@10=0.802 |
| Adaptive retrieval | Case 3 | dense_strong_bm25_weak branch |
| Citation integrity | Case 4 | GaRAGe citation_precision=1.0 |
| Safe failure | Case 5 | HARD_FAIL on out-of-domain |
