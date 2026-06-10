# DocResearch-Agent 2026｜12 核心模块学习与设计指导

本目录包含 12 份 Markdown 指导文件，用于学习并实现 **DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统**。

## 推荐学习顺序

1. Context Planner
2. Contextual / Structure-aware Chunker
3. Tool Registry
4. Hybrid + Graph Retriever
5. Retrieval Evaluator
6. Evidence Composer
7. Grounded Answer Generator
8. Self-Reflection Judge
9. Citation Guardrails
10. Corrective Repair Router
11. Trace + Eval Runner
12. Skill Prompt Registry

## 总流程

```text
User Question
  ↓
Context Planner
  ↓
Contextual / Structure-aware Chunker
  ↓
Tool Registry
  ↓
Hybrid + Graph Retriever
  ↓
Retrieval Evaluator
  ↓
Evidence Composer
  ↓
Grounded Answer Generator
  ↓
Citation Guardrails
  ↓
Self-Reflection Judge
  ↓
Corrective Repair Router
  ↓
Trace + Eval Runner
  ↓
Skill Prompt Registry
```

注意：Skill Prompt Registry 是横向支撑模块，不一定在运行时最后执行；它支撑 Planner、Evaluator、Generator、Judge 等 LLM 节点。Tool Registry 也是横向支撑模块，支撑 Dense Search、BM25 Search、Graph Expansion、Citation Check 等工具调用。
