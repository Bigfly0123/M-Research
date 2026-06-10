# 11｜Trace + Eval Runner 设计指导

> 项目定位：**DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统**。
> 目标不是普通 RAG 问答，而是围绕上下文规划、图增强检索、证据组合、自动评测、可追踪修复构建一个小而硬的高级项目。

## 1. 模块作用
Trace + Eval Runner 让项目从 demo 变成工程系统。它记录每次问答的完整路径，并用 eval_dataset 对不同策略做对比，输出 eval_report.md。

## 2. 必须理解的知识点
- **Trace**：记录每个节点输入输出、耗时、token、决策。
- **Evaluation Loop**：用 traces 和反馈推动改进。
- **Ablation**：对比 baseline vector、hybrid、hybrid+graph、agentic repair。
- **RAG Metrics**：retrieval_hit_rate、citation_support、faithfulness、answer_relevance。

## 3. 技术参考
- [OpenAI Agent Improvement Loop](https://developers.openai.com/cookbook/examples/agents_sdk/agent_improvement_loop)
- [Ragas Metrics](https://docs.ragas.io/en/v0.1.21/concepts/metrics/)
- [Ragas Faithfulness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)

## 4. Trace Schema
```json
{
  "trace_id": "run_001",
  "question": "...",
  "context_plan": {},
  "retrieval": {"dense_count": 20, "bm25_count": 20, "graph_count": 8},
  "retrieval_eval": {},
  "context_pack": [],
  "answer": "...",
  "guardrail_result": {},
  "judge_result": {},
  "repair_history": [],
  "final_status": "pass",
  "latency_ms": 4200,
  "context_tokens": 3100,
  "total_tokens": 5200
}
```

## 5. Eval Dataset
```json
{
  "id": "q001",
  "question": "What does Evidence Composer do?",
  "reference_answer": "It deduplicates, compresses and organizes evidence into a citation-ready context pack.",
  "reference_chunks": ["chunk_12"],
  "question_type": "concept",
  "expected_terms": ["deduplicate", "compress", "citation"]
}
```

## 6. 指标
| 指标 | 含义 |
|---|---|
| retrieval_hit_rate | 是否命中 reference chunks |
| citation_support_rate | 引用是否支持答案 |
| judge_pass_rate | Judge 通过率 |
| repair_success_rate | 修复后是否变好 |
| avg_latency_ms | 平均耗时 |
| avg_context_tokens | 平均上下文 token |
| failure_distribution | 失败类型分布 |

## 7. 实施步骤
1. 每个节点调用 add_trace。
2. 完成一次运行后写入 traces/run_trace.jsonl。
3. 建 30-50 条 eval_dataset。
4. 实现 eval_runner，支持不同 mode。
5. 生成 reports/eval_report.md。

## 8. 验收标准
- 每次问答有 trace_id。
- eval_runner 能跑 30 条问题。
- 报告包含策略对比表。
- 报告包含失败案例分析。
- 能证明 graph/repair 是否有用。

## 9. 常见坑
- 只评最终答案，不看中间检索。
- 没有 baseline，无法证明提升。
- 测试集太少且全是简单题。
- 指标太复杂，最后算不出来。
