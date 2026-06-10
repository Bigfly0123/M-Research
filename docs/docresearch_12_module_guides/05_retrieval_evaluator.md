# 05｜Retrieval Evaluator 设计指导

> 项目定位：**DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统**。
> 目标不是普通 RAG 问答，而是围绕上下文规划、图增强检索、证据组合、自动评测、可追踪修复构建一个小而硬的高级项目。

## 1. 模块作用
Retrieval Evaluator 在生成答案前评估检索证据质量，防止弱证据直接进入 Answer Generator。它对应 Corrective RAG 思想：检索可能错，先评估，再决定继续、改写 query、扩大 top_k 或 graph_expand。

## 2. 必须理解的知识点
- **Retrieval Evaluation**：评估 retrieved chunks，而不是最终答案。
- **Evidence Quality**：`strong / weak / irrelevant / conflicting`。
- **Actionable Evaluation**：评估结果必须给 recommended_action。
- **和 Judge 区别**：Retrieval Evaluator 是生成前；Self-Reflection Judge 是生成后。

## 3. 技术参考
- [Ragas Metrics](https://docs.ragas.io/en/v0.1.21/concepts/metrics/)
- [Ragas Faithfulness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)

## 4. 输入输出
```json
{
  "evidence_quality": "weak",
  "confidence": 0.62,
  "reason": "Top chunks discuss RAG generally but do not explain graph expansion.",
  "missing_evidence": ["term graph construction", "graph expansion mechanism"],
  "recommended_action": "graph_expand",
  "should_continue": false
}
```

## 5. 设计方案
先用规则评分，再用 LLM 复核。规则包括：
- top chunk 分数；
- query term overlap；
- source diversity；
- 是否有空结果；
- graph expansion 是否被触发。

## 6. 实施步骤
1. 实现 heuristic_evidence_score。
2. 定义 quality 阈值。
3. 用 LLM 输出 missing_evidence 和 recommended_action。
4. 写入 state['retrieval_eval']。
5. 如果 should_continue=false，进入 Repair Router。

## 7. recommended_action 枚举
```text
continue
rewrite_query
increase_top_k
graph_expand
fallback_bm25
stop_and_ask_clarification
```

## 8. 验收标准
- 能输出固定质量标签。
- weak/irrelevant 会触发修复。
- reason 和 missing_evidence 可读。
- trace 记录 evaluator 结果。
- eval report 能统计 evidence_quality 分布。

## 9. 常见坑
- Evaluator 太严格导致无限重试。
- recommended_action 自由文本，Repair Router 无法解析。
- 不记录 missing_evidence，query rewrite 缺方向。
- 只靠 LLM 不做规则兜底。
