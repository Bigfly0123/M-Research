# 08｜Self-Reflection Judge 设计指导

> 项目定位：**DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统**。
> 目标不是普通 RAG 问答，而是围绕上下文规划、图增强检索、证据组合、自动评测、可追踪修复构建一个小而硬的高级项目。

## 1. 模块作用
Self-Reflection Judge 在答案生成后评估答案质量，并输出失败类型和修复动作。它不是简单打分器，而是可靠性控制节点。

## 2. 必须理解的知识点
- **LLM-as-a-Judge**：用 LLM 做评估，但必须有 rubric 和 schema。
- **Self-RAG 启发**：判断检索是否必要、证据是否有用、答案是否被支持。
- **四个核心评分**：answer_relevance、citation_support、faithfulness、context_sufficiency。

## 3. 技术参考
- [Ragas Metrics](https://docs.ragas.io/en/v0.1.21/concepts/metrics/)
- [Ragas Faithfulness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)
- [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents)

## 4. 输出示例
```json
{
  "pass": false,
  "answer_relevance": 0.82,
  "citation_support": 0.55,
  "faithfulness": 0.70,
  "context_sufficiency": 0.62,
  "failure_type": "citation_error",
  "reason": "The cited evidence defines BM25 but does not support graph expansion.",
  "repair_action": "recompose_evidence"
}
```

## 5. failure_type
```text
pass
retrieval_miss
weak_evidence
citation_error
hallucination
incomplete_answer
context_noise
off_topic
```

## 6. 实施步骤
1. 定义 JudgeResult schema。
2. 编写 judge rubric。
3. LLM 输出 JSON。
4. 规则兜底：没有引用直接 citation_error。
5. 根据阈值判定 pass。
6. 写 trace。

## 7. 推荐阈值
```python
pass = (
    answer_relevance >= 0.75 and
    citation_support >= 0.75 and
    faithfulness >= 0.75 and
    context_sufficiency >= 0.65
)
```

## 8. 验收标准
- 能识别 citation_error / weak_evidence / hallucination。
- 失败时给 repair_action。
- trace 记录四个分数。
- eval report 能统计 judge_pass_rate。

## 9. 常见坑
- 只输出“好/不好”，没有 failure_type。
- Judge 太严格，导致成本过高。
- Judge 太松，幻觉答案通过。
- 不做规则兜底。
