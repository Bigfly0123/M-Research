# Context Planner Instructions

## 角色描述
Context Planner 是上下文决策入口层，负责判断本轮问题需要什么上下文、调用哪些检索工具、上下文预算多少、风险级别和 Judge 应重点检查什么。

遵循流程: Rule-based Planner -> LLM Refiner -> Pydantic Validation -> Fallback。

## 输入
- question: 用户问题
- use_llm: 是否使用 LLM 细化 (默认 True)

## 处理逻辑
1. **空问题检查**: 若 question 为空，直接返回 fail
2. **规则版规划 (rule_based_plan)**: 根据关键词匹配 query_type，确定 retrieval_plan 和 context_budget
3. **LLM 细化 (llm_refine_plan)**: 补充 intent、expected_evidence，可能调整 retrieval_plan
4. **Pydantic 验证**: 确保输出符合 ContextPlan schema
5. **Fallback**: LLM 失败时回退到规则版结果

## LLM Prompt

```
You are a context planner for a technical documentation Q&A system.

Question: {question}
Current plan: {base_plan_json}

Refine the plan. Output ONLY valid JSON with these fields:
- query_type: one of [fact, concept, multi_hop, comparison, code_understanding, troubleshooting]
- intent: brief description of what the question asks
- retrieval_plan: list of [dense, bm25, graph_expand]
- context_budget: integer, max context tokens
- rewritten_query: improved query for retrieval
- expected_evidence: list of what kind of evidence is needed
- judge_focus: list of dimensions judge should focus on
```

## 输出
ContextPlan 字段:
- query_type: 6种类型之一
- intent: 意图描述
- rewritten_query: 改写后的查询
- retrieval_plan: 检索策略列表
- top_k_dense / top_k_bm25: 各路检索数量
- graph_hops: 图扩展跳数
- use_reranker: 是否使用重排
- context_budget: 上下文 token 预算
- need_code_blocks / need_tables: 是否需要代码块/表格
- risk_level: low / medium / citation_sensitive
- expected_evidence: 期望的证据类型列表
- judge_focus: Judge 应关注的维度

## 规则
- 始终至少包含 dense 和 bm25
- multi_hop 和 comparison 必须加 graph_expand
- 复杂问题设更高 context_budget (comparison=4500, multi_hop=3500)
- risk_level 默认 citation_sensitive
- judge_focus 默认包含 citation_support + faithfulness
