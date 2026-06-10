# 10｜Corrective Repair Router 设计指导

> 项目定位：**DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统**。
> 目标不是普通 RAG 问答，而是围绕上下文规划、图增强检索、证据组合、自动评测、可追踪修复构建一个小而硬的高级项目。

## 1. 模块作用
Corrective Repair Router 根据 Retrieval Evaluator、Citation Guardrails 和 Self-Reflection Judge 的失败类型，选择精准修复动作。它不是简单 retry，而是 failure_type-driven correction。

## 2. 必须理解的知识点
- **Corrective Repair**：不同失败对应不同修复路径。
- **LangGraph conditional edges**：根据 state 决定下一节点。
- **Retry Budget**：最多修复 1-2 次，防止循环。

## 3. 技术参考
- [LangGraph StateGraph](https://reference.langchain.com/python/langgraph/graph/state/StateGraph)
- [LangGraph Graph API](https://docs.langchain.com/oss/python/langgraph/graph-api)
- [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents)

## 4. 映射表
| failure_type | repair_action | next_node |
|---|---|---|
| retrieval_miss | rewrite_query | context_planner |
| weak_evidence | graph_expand / increase_top_k | hybrid_graph_retriever |
| citation_error | recompose_evidence | evidence_composer |
| hallucination | regenerate_with_evidence_only | grounded_answer_generator |
| incomplete_answer | decompose_query | context_planner |
| context_noise | reduce_context_noise | evidence_composer |

## 5. 数据结构
```python
class RepairDecision(BaseModel):
    repair_action: str
    repair_reason: str
    next_node: str
    updated_state_patch: dict
```

## 6. 实施步骤
1. 读取 failure_type。
2. 查 REPAIR_MAP。
3. 检查 repair_count 是否超过上限。
4. 更新 state，例如增加 top_k、加入 graph_expand、改写 query。
5. 通过 conditional edge 跳转到 next_node。
6. 记录 repair_history。

## 7. 验收标准
- 不同 failure_type 走不同修复路径。
- repair_count 有上限。
- 修复后会重新进入 Judge。
- trace 记录 repair_history。
- 超过上限时安全降级，说明证据不足。

## 8. 常见坑
- 所有失败都回 planner，过于粗糙。
- 无限 retry。
- 修复动作没有前后对比。
- repair_action 是自由文本，导致路由不稳定。
