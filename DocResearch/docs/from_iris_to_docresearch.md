# 从 IRIS 到 DocResearch-Agent：学习经验，而不是复刻项目

## IRIS 学到了什么

1. LangGraph StateGraph: 用有向图组织多节点 Agent workflow
2. 条件边与循环: Reviewer 失败后回到 Planner
3. 双模型策略: fast 做生成，smart 做审查
4. SSE 流式通信 + FastAPI + CORS

## 模块映射

| IRIS 模块 | DocResearch 模块 | 变化说明 |
|-----------|-----------------|---------|
| Router | Context Planner | 从简单分类升级为问题分类+策略规划 |
| Planner | Context Planner | 从拆子问题变为规划上下文 |
| Researcher (RAG+Tavily) | Hybrid Graph Retriever | 从单路变为 Dense+BM25+Graph |
| Writer | Grounded Answer Generator | 从写报告变为带引用答案生成 |
| Reviewer | Self-Reflection Judge | 从简单审查变为4维评分+failure_type |
| Refiner | Repair Router | 从简单修改变为failure_type驱动修复 |
| - | Evidence Composer | 新增: 证据去重/压缩/citation绑定 |
| - | Citation Guardrails | 新增: 引用三重检查 |
| - | Tool Registry | 新增: MCP-style工具抽象 |
| - | Trace Store + Eval | 新增: 全链路追踪与评测闭环 |
