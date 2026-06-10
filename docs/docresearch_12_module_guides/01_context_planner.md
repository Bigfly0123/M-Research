# 01｜Context Planner 设计指导

> 项目定位：**DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统**。
> 目标不是普通 RAG 问答，而是围绕上下文规划、图增强检索、证据组合、自动评测、可追踪修复构建一个小而硬的高级项目。

## 1. 模块作用
Context Planner 是整个系统的入口决策层。它不直接回答问题，而是决定本轮任务需要什么上下文、使用什么检索策略、给多少 context budget、是否需要代码块/表格/图扩展，以及这次回答的风险级别。

普通 RAG 是 `query -> top-k -> answer`。Context-Engineered RAG 是 `任务理解 -> 上下文规划 -> 多源检索 -> 证据组织 -> 生成 -> 评测/修复`。

## 2. 必须理解的知识点
- **Context Engineering**：RAG 只是上下文工程的一种手段。更完整的系统会动态选择文件、chunk、工具、记忆和预算。
- **Context Budget**：每轮给模型的证据 token 上限。预算太少会证据不足，太多会引入噪声。
- **Query Type**：建议区分 `fact / concept / multi_hop / comparison / code_understanding`。
- **Risk Level**：技术文档 QA 默认 citation_sensitive，不能无证据强答。

## 3. 技术参考
- [Anthropic Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents)
- [LangGraph StateGraph](https://reference.langchain.com/python/langgraph/graph/state/StateGraph)

## 4. 输入输出
输入：`question, available_sources, conversation_context, system_config`。
输出示例：
```json
{
  "query_type": "multi_hop",
  "intent": "explain_relationship",
  "retrieval_plan": ["bm25", "dense", "graph_expand"],
  "context_budget": 3500,
  "need_code_blocks": false,
  "need_tables": false,
  "risk_level": "citation_sensitive",
  "rewrite_query": "How does Answer Judge trigger Repair Router?",
  "expected_evidence": ["definition", "workflow", "failure_type mapping"]
}
```

## 5. 设计方案
1. 先做规则版 planner，保证稳定。
2. 再接 LLM planner，补充更细的意图和 expected_evidence。
3. 用 Pydantic 校验 JSON。
4. 把 plan 写入 AgentState 和 trace。
5. 后续 Retriever 根据 `retrieval_plan` 调用不同工具。

## 6. 建议 Schema
```python
class ContextPlan(BaseModel):
    query_type: Literal['fact','concept','multi_hop','comparison','code_understanding']
    intent: str
    retrieval_plan: list[Literal['dense','bm25','graph_expand']]
    context_budget: int = 3500
    need_code_blocks: bool = False
    need_tables: bool = False
    risk_level: Literal['low','medium','citation_sensitive'] = 'citation_sensitive'
    rewrite_query: str
    expected_evidence: list[str] = []
```

## 7. 实施步骤
- Step 1：实现 `rule_based_plan(question)`。
- Step 2：实现 `llm_refine_plan(question, base_plan)`。
- Step 3：校验输出，不合法就回退规则版。
- Step 4：写入 `state['context_plan']`。
- Step 5：trace 记录 query_type、retrieval_plan、budget。

## 8. 验收标准
- 能区分五类问题。
- 不同问题能触发不同 retrieval_plan。
- 输出稳定 JSON。
- trace 中能看到 planner 决策。
- 后续 eval 能按 query_type 统计表现。

## 9. 常见坑
- 让 Planner 直接回答问题。
- LLM 输出不稳定，没有 schema 校验。
- 检索策略太多，一开始只保留 dense/bm25/graph_expand。
- 不记录 planner trace，后面无法复盘。
