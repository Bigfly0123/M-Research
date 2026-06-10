# TechDocQA Dataset Report

## Dataset Purpose

TechDocQA 是为评估 RAG 系统在**技术文档检索与问答**场景下的能力而自建的评测数据集。

现有公开数据集（如 MultiHop-RAG、HotpotQA）主要基于百科/新闻类语料，问题类型偏向事实型多跳推理，无法覆盖 RAG 在工程实践中的核心挑战：

- **技术概念解释**：模型能否准确理解并阐述复杂技术概念？
- **实现细节追问**：能否从文档中提取具体的配置、代码片段、API 参数？
- **跨文档对比**：能否在不同技术方案间进行横向对比？
- **故障排查**：能否根据症状/错误信息定位原因和解决方案？
- **多跳推理**：能否串联多个文档片段推导出答案？

因此，TechDocQA 选择 9 篇覆盖 RAG 生态各环节的高质量技术文档作为语料，人工审核标注问答对，确保评测与实际工程需求对齐。

## Document Sources

| # | doc_id | Title | Topic | Source URL |
|---|--------|-------|-------|------------|
| 1 | anthropic_context_001 | Effective Context Engineering for AI Agents | context engineering | https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents |
| 2 | deepeval_001 | DeepEval Metrics Introduction | evaluation metrics | https://docs.confident-ai.com/docs/metrics-introduction |
| 3 | langgraph_001 | LangGraph StateGraph Low-Level Concepts | agent framework | https://langchain-ai.github.io/langgraph/concepts/low_level/ |
| 4 | langgraph_002 | LangGraph Agentic RAG Tutorial | agentic RAG | https://langchain-ai.github.io/langgraph/tutorials/agentic_rag/ |
| 5 | lightrag_001 | LightRAG README | graph RAG | https://github.com/HKUDS/LightRAG |
| 6 | mcp_001 | MCP Tools Specification | tool protocol | https://modelcontextprotocol.io/specification/2025-03-26/server/tools |
| 7 | openai_agents_001 | OpenAI Agents SDK - Tools and Guardrails | agent SDK | https://openai.github.io/openai-agents-python/tools/ |
| 8 | ragas_001 | Ragas Available Metrics | evaluation metrics | https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/ |
| 9 | ragflow_001 | RAGFlow README | RAG engine | https://github.com/infiniflow/ragflow |

## Dataset Schema

`eval_dataset_v1.jsonl` 每行一个 JSON 对象，字段如下：

| Field | Type | Description |
|-------|------|-------------|
| `id` | string | 唯一标识，格式 `techdocqa_NNNN` |
| `source_dataset` | string | 固定为 `TechDocQA` |
| `question` | string | 评测问题 |
| `question_type` | string | 问题类型：`fact`, `concept`, `implementation`, `comparison`, `multi_hop`, `troubleshooting` |
| `expected_answer` | string | 参考答案 |
| `expected_keywords` | list[str] | 答案应包含的关键词/短语 |
| `gold_doc_ids` | list[str] | 答案所依据的文档 ID |
| `gold_chunk_ids` | list[str] | 答案所依据的 chunk ID |
| `gold_sources` | list[str] | 原始文档文件路径 |
| `difficulty` | string | 难度：`easy`, `medium`, `hard` |
| `metadata` | object | 附加元数据（topic, created_by, draft_id, review_note） |

## Question Distribution

| question_type | Count | Percentage |
|---------------|-------|------------|
| concept | 14 | 33.3% |
| implementation | 11 | 26.2% |
| multi_hop | 7 | 16.7% |
| troubleshooting | 4 | 9.5% |
| fact | 3 | 7.1% |
| comparison | 3 | 7.1% |
| **Total** | **42** | **100%** |

## Difficulty Distribution

| Difficulty | Count | Percentage |
|------------|-------|------------|
| hard | 27 | 64.3% |
| medium | 14 | 33.3% |
| easy | 1 | 2.4% |

## Gold Evidence Annotation

标注方法：

1. **LLM Draft 生成**：基于 chunks.jsonl 中每个 chunk，使用 LLM 生成初始问答对草稿（含 question, expected_answer, expected_keywords, question_type, difficulty）
2. **Gold Chunk 绑定**：每个问题自动绑定来源 chunk_id 作为 gold_chunk_ids，multi_hop 类型问题绑定多个 chunk
3. **人工审核修订**：逐条审核 LLM 草稿，修正答案偏差、调整难度标注、补充 expected_keywords，删除低质量问题
4. **Compact Set 精选**：从修订后的候选集中按 question_type 均衡筛选，最终保留 42 条

## Quality Control

审核规则：

- `expected_answer` 必须非空，答案应直接回答问题而非泛泛描述
- `gold_chunk_ids` 必须非空且存在于 chunks.jsonl
- 同一问题不重复出现
- `question_type` 至少覆盖 5 类
- `multi_hop` 类型至少 5 条，`troubleshooting` 至少 3 条
- `expected_keywords` 至少包含 3 个与答案强相关的关键词

验收结果（全部通过）：

| Check | Result |
|-------|--------|
| 问题数量 30-50 | PASS (42) |
| expected_answer 非空率 100% | PASS |
| gold_chunk_ids 非空率 100% | PASS |
| gold_chunk_ids 存在率 100% | PASS |
| 重复问题 0 | PASS |
| question_type >= 5 类 | PASS (6) |
| multi_hop >= 5 | PASS (7) |
| troubleshooting >= 3 | PASS (4) |

## Example Samples

### Sample 1 — troubleshooting (hard)

**Q:** 在设计 agent system prompt 时，原文指出了哪两类常见失败模式？应如何避免？

**A:** 原文指出两类常见失败模式：一类是把复杂且脆弱的逻辑硬编码进 prompt，导致 agent 难以灵活处理变化；另一类是只给非常模糊的高层指令，使模型缺少可执行约束。更好的做法是在具体约束和灵活启发之间取得平衡，提供足够明确但不过度僵硬的上下文。

**Gold chunks:** `anthropic_context_001-s04-c000`

### Sample 2 — fact (hard)

**Q:** The Anatomy of Effective Context 中对 good context engineering 的核心定义是什么？

**A:** Good context engineering 指的是在 LLM 有限的注意力预算下，找到尽可能小但高信号的 token 集合，从而最大化模型产生期望行为的概率。它强调上下文质量比上下文数量更重要。

**Gold chunks:** `anthropic_context_001-s04-c000`

### Sample 3 — concept (hard)

**Q:** Context Retrieval and Agentic Search 为什么强调 just-in-time context？

**A:** Just-in-time context 强调不要预先把所有数据放进模型上下文，而是保留文件路径、查询、链接等轻量标识，在运行时通过工具按需加载相关信息。这样可以减少上下文浪费，避免噪声污染，并让 agent 在面对大规模外部信息时仍能灵活检索和行动。

**Gold chunks:** `anthropic_context_001-s05-c000`

### Sample 4 — concept (medium)

**Q:** DeepEval 的预定义指标通常如何对 LLM 应用进行评分？

**A:** DeepEval 的预定义指标通常使用 LLM-as-a-judge，并结合 QAG、DAG、G-Eval 等评估技术，对 LLM 应用的输出进行打分。指标一般会返回 0 到 1 之间的 score、评分理由，以及是否达到 threshold 的判断。

**Gold chunks:** `deepeval_001-s02-c000`

### Sample 5 — concept (hard)

**Q:** DeepEval 中的 Metric Categories 主要包括哪些类别？它们分别用于什么场景？

**A:** DeepEval 的指标类别包括 Custom Metrics、RAG Metrics、Agent/Tool Use Metrics、Chatbot Metrics、Safety Metrics 等。Custom Metrics 用于自定义业务评估，RAG Metrics 用于评估检索和生成质量，Agent/Tool Use Metrics 用于评估 agent 任务完成和工具调用，Chatbot Metrics 用于多轮对话质量，Safety Metrics 用于安全和合规检查。

**Gold chunks:** `deepeval_001-s03-c000`

## Limitations

- **规模有限**：仅 42 条问答，统计意义有限，更适合定性分析而非大规模定量评测
- **文档覆盖不均**：9 篇文档中部分文档（如 MCP、RAGFlow）生成的问题较少，topic 分布不完全均匀
- **难度偏向 hard**：64.3% 为 hard 难度，easy/medium 样本不足，可能影响对简单检索能力的区分
- **单语言**：问题和答案主要为中文，未覆盖英文技术文档原生查询场景
- **LLM 标注偏差**：虽然经过人工审核，但 expected_answer 仍可能存在 LLM 幻觉残留
- **静态语料**：技术文档更新后，gold evidence 可能失效，需定期维护
