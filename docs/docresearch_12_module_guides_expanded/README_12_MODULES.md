# DocResearch-Agent 12 个核心模块扩写版指导文档

这套文档服务于：**DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统**。

它不是普通 RAG demo，而是围绕：

```text
上下文规划 -> 结构化切块 -> 工具抽象 -> 混合图检索 -> 检索评估 -> 证据组合 -> 基于证据生成 -> 自反思评测 -> 引用护栏 -> 纠错修复 -> Trace/Eval -> Skill Prompt 管理
```

构建一个两周内能完成、但足够高级的 Agentic RAG 工程项目。

## 建议阅读顺序

1. 01_context_planner.md
2. 02_contextual_structure_aware_chunker.md
3. 03_tool_registry.md
4. 04_hybrid_graph_retriever.md
5. 05_retrieval_evaluator.md
6. 06_evidence_composer.md
7. 07_grounded_answer_generator.md
8. 08_self_reflection_judge.md
9. 09_citation_guardrails.md
10. 10_corrective_repair_router.md
11. 11_trace_eval_runner.md
12. 12_skill_prompt_registry.md

## 怎么用

每个模块先按 MVP 做，不要一开始追求工业级完整实现。核心要求是：能运行、能接入主图、能记录 trace、能被 eval 验证。
