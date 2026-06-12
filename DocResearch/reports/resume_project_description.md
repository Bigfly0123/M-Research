# Resume Project Description: DocResearch-Agent 2026

---

## 中文版 (简历用)

**项目名称**: DocResearch-Agent 2026 — 面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统

**项目描述**: 构建了一个包含 Context Planner、Adaptive Hybrid Retrieval、Selective Graph Expansion、Retrieval Evaluator、Evidence Tier Composer、Grounded Answer Generator、Citation Guardrails、Self-Reflection Judge 与 Repair Router 的 8 节点 LangGraph 工作流，实现技术文档问答中的动态检索规划、证据组合、引用校验与错误修复闭环。

**核心工作**:
- 设计 Adaptive Hybrid Retrieval 策略，根据 Dense/BM25 信号强度动态调整融合权重，新增 dense_strong_bm25_weak 分支优化策略文档检索
- 实现三层 Self-Reflection Judge (PASS/SOFT_WARN/HARD_FAIL) 决策机制，解决 Judge 过严导致的无效 repair 循环问题
- 修复 Citation Guardrails 正则匹配 Bug，使 guardrail_pass_rate 从 0.000 提升至 0.952
- 引入 Evidence Tier 分层 (primary/supporting/context_only)，新增 primary_evidence_coverage 评测指标
- 构建 20 条鲁棒性评测数据集，验证系统在 domain 外问题、证据不足、模糊问题等场景下的安全行为

**实验结果**:
- MultiHop-RAG hybrid_graph recall@10 = 0.813
- StratRAG adaptive_hybrid recall@10 = 0.875 (Phase 3 提升 +3.5%)
- TechDocQA Full QA: faithfulness = 0.988, citation_precision = 0.952, guardrail_pass_rate = 0.952
- GaRAGe Full QA: citation_precision = 0.980, faithfulness = 0.970
- 平均 repair 次数从 2.000 降至 0.06~0.12
- Out-of-domain 拒答正确率 80%

---

## English Version (Resume/CV)

**Project**: DocResearch-Agent 2026 — Context-Engineered Agentic GraphRAG for Reliable Technical Document QA

**Description**: Built an 8-node LangGraph workflow with Context Planner, Adaptive Hybrid Retrieval, Selective Graph Expansion, Retrieval Evaluator, Evidence-Tier Composer, Grounded Answer Generator, Citation Guardrails, Self-Reflection Judge, and Repair Router. The system forms a closed loop from query understanding to grounded, cited, and verified answers for technical document QA.

**Key Contributions**:
- Designed Adaptive Hybrid Retrieval with dynamic weight fusion based on Dense/BM25 signal analysis, including a dense_strong_bm25_weak branch for strategy documents
- Implemented a 3-tier Self-Reflection Judge (PASS/SOFT_WARN/HARD_FAIL) that eliminated destructive repair loops, reducing average repair count from 2.0 to 0.06–0.12
- Fixed citation pattern regex mismatch in Guardrails, improving guardrail pass rate from 0.000 to 0.952
- Introduced Evidence Tier classification (primary/supporting/context_only) with a new primary_evidence_coverage metric
- Built a 20-sample robustness evaluation covering out-of-domain, insufficient evidence, ambiguous queries, and citation corruption scenarios

**Results**:
- MultiHop-RAG hybrid_graph recall@10: 0.813
- StratRAG adaptive_hybrid recall@10: 0.875 (+3.5% after Phase 3)
- TechDocQA Full QA: faithfulness 0.988, citation_precision 0.952, guardrail_pass_rate 0.952
- GaRAGe Full QA: citation_precision 0.980, faithfulness 0.970
- 80% correct refusal on out-of-domain queries

**Tech Stack**: Python, LangGraph, FAISS, sentence-transformers, BM25, GPT-4o-mini, Streamlit

---

## Interview Talking Points

### What problem does this solve?
Standard RAG pipelines just retrieve and generate — they don't verify citations, don't detect unsupported answers, and don't repair failures. DocResearch-Agent adds a reliability loop that catches and fixes these issues.

### What's the most interesting technical challenge?
The Judge/Guardrails over-strictness problem in Phase 2. The system was stuck in a repair loop because the judge flagged every answer as failing. Root cause: the citation regex didn't match the actual citation format, AND the judge didn't distinguish between minor warnings and critical failures. The fix required both a regex correction and a 3-tier decision architecture.

### What would you do differently?
Add an active clarification mechanism for ambiguous queries (currently 40% correct). Also, I'd implement LLM-as-judge for semantic answer correctness rather than relying purely on rule-based metrics.

### What's the scale?
- 4 datasets: TechDocQA (42 QA), MultiHop-RAG (251 queries), StratRAG (44 queries), GaRAGe (50 QA)
- 8-node LangGraph workflow
- 4 phases of iterative development over ~6 weeks
