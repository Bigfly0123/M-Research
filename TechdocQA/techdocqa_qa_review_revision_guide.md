# TechDocQA QA Draft 审核修改说明

## 1. 审核结论

当前 `qa_draft_for_review.jsonl` 共 54 条 QA 草稿，不建议直接进入正式 TechDocQA v1。

主要问题：

1. `expected_answer` 大量是 source chunk 开头约 200 字的截断内容，不是完整标准答案。
2. 多个 `implementation` 问题要求“给出代码示例”，但对应 gold chunk 并没有代码或命令。
3. 多个 `troubleshooting` 问题要求“常见问题及解决方法”，但原文只是概念介绍，不包含真实失败模式或解决方案。
4. 45～52 的 `multi_hop` 问题是机械拼接两个文档标题，不是真正跨文档推理。

因此本次处理原则是：

- 明显不成立的样本直接删除；
- 重复度较高的样本可选删除；
- 其余样本全部重写 `question`、`question_type` 或 `expected_answer`；
- 最终保留样本的 `expected_answer` 必须是完整、可验证、严格对应问题的答案。

---

## 2. 必须删除的编号

```text
删除：2, 6, 9, 14, 16, 21
```

| 编号 | 删除原因 |
|---:|---|
| 2 | 问“给出代码示例”，但 `The Anatomy of Effective Context` chunk 没有代码示例。 |
| 6 | 问“给出代码示例”，但 `Context Retrieval and Agentic Search` chunk 是概念和实践说明，不是代码教程。 |
| 9 | `Quick Summary` 没有代码示例，implementation 类型不成立。 |
| 14 | 与 11～13 重复，而且问题是概念，答案却是代码片段，错位。 |
| 16 | 与 13 重复，而且答案是代码片段，不适合问“定义是什么”。 |
| 21 | `Choosing Your Metrics` 是指标选择原则，不是代码使用示例。 |

---

## 3. 可选删除的编号

如果希望把数据集控制在 40～45 条，可以额外删除：

```text
可选删除：1, 7, 10, 13, 19, 22, 25
```

这些样本不是完全错误，但和相邻样本重复度较高，主要是“定义是什么 / 作用是什么”模板题。

本次我同时生成了两个版本：

- `qa_revised_candidate.jsonl`：只删除必须删除项，保留 48 条。
- `qa_revised_candidate_compact.jsonl`：删除必须删除项 + 可选去重项，保留 41 条。

---

## 4. 全局修改要求

对所有保留样本执行以下要求：

```text
1. 不允许 expected_answer 直接使用 chunk 前 200 字截断内容。
2. expected_answer 应为 2～5 句话，完整回答问题。
3. expected_answer 必须能被 suggested_gold_chunk_ids 对应证据支持。
4. implementation 问题必须有实现步骤、代码、命令、API 或配置依据。
5. troubleshooting 问题必须有失败模式、错误处理或解决方法依据。
6. multi_hop 问题必须真正连接两个或多个 gold chunks，不能简单拼接两个文档标题。
7. 每条样本最终设置 review_status = approved。
```

---

## 5. 逐条修改清单

下面是建议修改后的问题、类型和答案要点。Agent 可直接按这些内容更新 JSONL。

### 1

- `question_type`: `concept`
- `question`: 在 Context Engineering 中，为什么需要为 agent 提供“最小但高信号”的上下文？
- `expected_answer`: 因为 LLM 的注意力预算是有限的，进入上下文的 token 越多并不一定越好。好的 context engineering 不是把所有材料都塞给模型，而是在有限上下文窗口内选择最小但最有用的信息集合，让模型更容易产生期望行为。它要求 system prompt 保持清晰、直接，并处在合适的抽象层级。
- `expected_keywords`: 有限注意力预算, 最小上下文, 高信号 token, 减少噪声, 期望行为

### 3

- `question_type`: `troubleshooting`
- `question`: 在设计 agent system prompt 时，原文指出了哪两类常见失败模式？应如何避免？
- `expected_answer`: 原文指出两类常见失败模式：一类是把复杂且脆弱的逻辑硬编码进 prompt，导致 agent 难以灵活处理变化；另一类是只给非常模糊的高层指令，使模型缺少可执行约束。更好的做法是在具体约束和灵活启发之间取得平衡，提供足够明确但不过度僵硬的上下文。
- `expected_keywords`: 硬编码逻辑, 模糊高层指令, 具体约束, 灵活启发, system prompt

### 4

- `question_type`: `fact`
- `question`: The Anatomy of Effective Context 中对 good context engineering 的核心定义是什么？
- `expected_answer`: Good context engineering 指的是在 LLM 有限的注意力预算下，找到尽可能小但高信号的 token 集合，从而最大化模型产生期望行为的概率。它强调上下文质量比上下文数量更重要。
- `expected_keywords`: 有限注意力预算, 最小集合, 高信号 token, 期望行为, 上下文质量

### 5

- `question_type`: `concept`
- `question`: Context Retrieval and Agentic Search 为什么强调 just-in-time context？
- `expected_answer`: Just-in-time context 强调不要预先把所有数据放进模型上下文，而是保留文件路径、查询、链接等轻量标识，在运行时通过工具按需加载相关信息。这样可以减少上下文浪费，避免噪声污染，并让 agent 在面对大规模外部信息时仍能灵活检索和行动。
- `expected_keywords`: just-in-time context, 按需加载, 工具检索, 减少上下文浪费, 大规模数据

### 7

- `question_type`: `fact`
- `question`: Context Retrieval and Agentic Search 的核心思想是什么？
- `expected_answer`: 它的核心思想是让 agent 在运行时主动检索所需上下文，而不是一次性把全部信息塞进 prompt。系统可以保存轻量索引、路径或查询线索，并在需要时调用搜索、文件读取或其他工具获取相关内容。
- `expected_keywords`: 运行时检索, 主动检索, 轻量索引, 工具调用, 上下文管理

### 8

- `question_type`: `concept`
- `question`: DeepEval 的预定义指标通常如何对 LLM 应用进行评分？
- `expected_answer`: DeepEval 的预定义指标通常使用 LLM-as-a-judge，并结合 QAG、DAG、G-Eval 等评估技术，对 LLM 应用的输出进行打分。指标一般会返回 0 到 1 之间的 score、评分理由，以及是否达到 threshold 的判断。
- `expected_keywords`: LLM-as-a-judge, QAG, DAG, G-Eval, score, threshold

### 10

- `question_type`: `fact`
- `question`: DeepEval 指标输出通常包含哪些内容？
- `expected_answer`: DeepEval 指标通常输出一个 0 到 1 的 score、对应的 score reasoning，以及该样本是否达到预设 threshold 的判断。这些输出可以用于自动化测试、回归评估和不同模型或 prompt 的对比。
- `expected_keywords`: score, score reasoning, threshold, 自动化测试, 评估

### 11

- `question_type`: `concept`
- `question`: DeepEval 中的 Metric Categories 主要包括哪些类别？它们分别用于什么场景？
- `expected_answer`: DeepEval 的指标类别包括 Custom Metrics、RAG Metrics、Agent/Tool Use Metrics、Chatbot Metrics、Safety Metrics 等。Custom Metrics 用于自定义业务评估，RAG Metrics 用于评估检索和生成质量，Agent/Tool Use Metrics 用于评估 agent 任务完成和工具调用，Chatbot Metrics 用于多轮对话质量，Safety Metrics 用于安全和合规检查。
- `expected_keywords`: Custom Metrics, RAG Metrics, Agent Metrics, Tool Use Metrics, Safety Metrics

### 12

- `question_type`: `implementation`
- `question`: 如何使用 DeepEval 的 RAG Metrics 评估 RAG 系统？请说明 retriever 和 generator 分别可用哪些指标。
- `expected_answer`: 可以把 RAG 系统拆成 retriever 和 generator 两部分评估。Retriever 侧可使用 contextual relevancy、contextual precision、contextual recall 等指标，衡量检索上下文是否相关、排序是否合理、是否覆盖标准证据。Generator 侧可使用 answer relevancy 和 faithfulness，评估答案是否回答问题以及是否忠于检索上下文。
- `expected_keywords`: contextual relevancy, contextual precision, contextual recall, answer relevancy, faithfulness

### 13

- `question_type`: `fact`
- `question`: DeepEval 的 Metric Categories 这一节主要想说明什么？
- `expected_answer`: 这一节主要说明 DeepEval 提供多类评测指标，用户应根据应用类型选择合适指标。例如 RAG 系统应关注上下文相关性、召回和忠实度，agent 系统应关注任务完成和工具调用，多轮聊天系统则应关注对话质量与安全性。
- `expected_keywords`: 指标类别, RAG 系统, agent 系统, 聊天系统, 选择指标

### 15

- `question_type`: `implementation`
- `question`: DeepEval 中如何用 TaskCompletionMetric 和 observe 评估一个 agent 流程？
- `expected_answer`: 可以先用 Golden 构造测试输入，再用 TaskCompletionMetric 定义任务完成指标，并通过 observe 装饰器标记 agent 或子函数，使 DeepEval 能记录组件级执行过程。最后调用 evaluate 或 observed callback，对 agent 流程的任务完成情况进行评估。
- `expected_keywords`: Golden, TaskCompletionMetric, observe, agent 流程, evaluate

### 17

- `question_type`: `concept`
- `question`: DeepEval 中 G-Eval 的作用是什么？
- `expected_answer`: G-Eval 用自然语言定义评估标准，让用户可以构建自定义 LLM-as-a-judge 指标。它适合评估 correctness、coherence、tone、helpfulness 等难以用固定公式衡量的输出质量。
- `expected_keywords`: G-Eval, 自然语言标准, 自定义指标, LLM-as-a-judge, correctness

### 18

- `question_type`: `implementation`
- `question`: 如何用 DeepEval 的 G-Eval 自定义一个 correctness 指标？
- `expected_answer`: 可以使用 LLMTestCase 构造输入、实际输出和期望输出，再用 GEval 定义指标名称、criteria 和 evaluation_params。之后对 test case 调用 measure 或 evaluate，即可根据自定义 correctness 标准得到评分和理由。
- `expected_keywords`: LLMTestCase, GEval, criteria, evaluation_params, correctness

### 19

- `question_type`: `concept`
- `question`: G-Eval 和普通固定指标相比有什么优势？
- `expected_answer`: G-Eval 的优势是可以用自然语言描述任务相关的评估标准，因此更适合主观性强、业务相关或领域特定的评估任务。相比固定指标，它更灵活，但也需要设计清晰的 criteria 以减少 judge 不稳定性。
- `expected_keywords`: 自然语言标准, 领域特定, 灵活, criteria, judge 不稳定性

### 20

- `question_type`: `concept`
- `question`: 选择 LLM 评测指标时，DeepEval 建议为什么不要选择太多指标？
- `expected_answer`: 过多指标会增加评估复杂度、运行成本和结果解释难度。DeepEval 建议通常控制在 5 个以内，其中包含 2 到 3 个系统通用指标，以及 1 到 2 个业务自定义指标，从而保持评测清晰且可执行。
- `expected_keywords`: 指标过多, 评估复杂度, 运行成本, 5 个以内, 业务自定义指标

### 22

- `question_type`: `fact`
- `question`: DeepEval 建议如何组合通用指标和自定义指标？
- `expected_answer`: DeepEval 建议用通用指标覆盖系统架构相关能力，例如 RAG 的 contextual precision、contextual recall 或 agent 的 tool correctness；再用少量自定义指标衡量具体业务目标，例如 helpfulness、格式合规或领域正确性。
- `expected_keywords`: 通用指标, 自定义指标, contextual precision, tool correctness, 业务目标

### 23

- `question_type`: `concept`
- `question`: DeepEval 为什么支持配置不同的 LLM Judge？
- `expected_answer`: 不同团队可能使用 OpenAI、Azure OpenAI、Ollama、Anthropic、Gemini、LiteLLM 等不同模型作为 judge。DeepEval 支持配置不同 LLM Judge，可以适配成本、私有部署、模型可用性和评估稳定性等需求。
- `expected_keywords`: LLM Judge, OpenAI, Azure OpenAI, Ollama, 成本, 私有部署

### 24

- `question_type`: `implementation`
- `question`: DeepEval 中配置 LLM Judge 可以有哪些方式？请举例说明。
- `expected_answer`: DeepEval 可以通过配置 OpenAI API key、Azure OpenAI endpoint/model/deployment、本地 Ollama 模型，以及 Anthropic、Gemini、LiteLLM 等方式选择不同的 LLM Judge。这样用户可以根据环境、成本和安全要求切换评估模型。
- `expected_keywords`: OpenAI API key, Azure OpenAI, Ollama, Anthropic, LiteLLM

### 25

- `question_type`: `fact`
- `question`: Configuring LLM Judges 这一节主要说明了什么？
- `expected_answer`: 这一节主要说明 DeepEval 不限制使用单一 judge 模型，而是允许用户根据实际环境配置不同 LLM 作为评估器。这样可以支持云端模型、本地模型和企业私有模型等多种评测部署方式。
- `expected_keywords`: 配置 LLM Judge, 评估器, 云端模型, 本地模型, 私有模型

### 26

- `question_type`: `concept`
- `question`: DeepEval 的 End-to-End Evals 和 Component-Level Evals 有什么区别？
- `expected_answer`: End-to-End Evals 直接评估完整 LLM 应用从输入到输出的最终表现。Component-Level Evals 则通过 tracing、observe 等方式评估应用内部组件或节点，例如 retriever、reranker、generator 或 agent tool call，从而定位问题来源。
- `expected_keywords`: End-to-End Evals, Component-Level Evals, tracing, observe, 内部组件

### 27

- `question_type`: `implementation`
- `question`: 如何用 DeepEval 对一个 LLM 应用进行 end-to-end evaluation？
- `expected_answer`: 可以先构造 LLMTestCase，包含 input、actual_output、expected_output 或 retrieval_context；再选择 AnswerRelevancyMetric、FaithfulnessMetric 等指标；最后调用 evaluate(test_cases, metrics) 执行端到端评估并查看评分与理由。
- `expected_keywords`: LLMTestCase, AnswerRelevancyMetric, FaithfulnessMetric, evaluate, 端到端评估

### 28

- `question_type`: `concept`
- `question`: 为什么需要自定义 DeepEval metric prompt？
- `expected_answer`: 默认 metric prompt 不一定适合具体业务或领域标准。通过自定义 prompt，用户可以让 LLM Judge 按照更贴近任务的 criteria 进行判断，从而提升评估结果的相关性和可解释性。
- `expected_keywords`: 自定义 prompt, 业务标准, 领域标准, LLM Judge, criteria

### 29

- `question_type`: `implementation`
- `question`: 如何在 DeepEval 中自定义 AnswerRelevancyMetric 的 prompt 模板？
- `expected_answer`: 可以继承 AnswerRelevancyTemplate，重写 generate_statements 等静态方法，然后把自定义模板传给 AnswerRelevancyMetric。这样指标在生成判断语句或评分时会使用自定义 prompt。
- `expected_keywords`: AnswerRelevancyTemplate, generate_statements, AnswerRelevancyMetric, 自定义模板, prompt

### 30

- `question_type`: `concept`
- `question`: LangGraph Agentic RAG 的核心架构通常包含哪些部分？
- `expected_answer`: LangGraph Agentic RAG 通常包含 AgentState、检索工具、agent 节点、retrieve 节点、grade_documents 节点、rewrite_query 节点和 generate 节点。agent 负责决定是否需要工具，retrieve 获取证据，grade_documents 判断相关性，rewrite_query 在证据不足时改写问题，generate 基于证据生成答案。
- `expected_keywords`: AgentState, retrieve, grade_documents, rewrite_query, generate

### 31

- `question_type`: `implementation`
- `question`: 在 LangGraph Agentic RAG 中，retriever_tool 的作用是什么？
- `expected_answer`: retriever_tool 用来封装知识库检索能力，使 agent 可以在需要时调用它获取相关文档，而不是固定每次都检索。它通常把向量库或其他检索器包装成工具，并返回与用户问题相关的文档内容。
- `expected_keywords`: retriever_tool, 知识库检索, agent 调用, 工具, 相关文档

### 32

- `question_type`: `concept`
- `question`: LangGraph Agentic RAG 中为什么需要 grade_documents 和 query rewriting？
- `expected_answer`: grade_documents 用来判断检索到的文档是否与问题相关，避免无关上下文进入生成阶段。如果评分结果显示证据不足或不相关，系统可以通过 query rewriting 改写用户问题并重新检索，从而提升召回质量。
- `expected_keywords`: grade_documents, query rewriting, 证据不足, 重新检索, 召回质量

### 33

- `question_type`: `concept`
- `question`: Self-RAG 在 Agentic RAG 中增加了什么能力？
- `expected_answer`: Self-RAG 在 Agentic RAG 中加入反思能力，使系统不仅检索并生成答案，还会检查生成内容是否忠于检索上下文。如果答案不可靠或上下文不足，系统可以触发重新检索、重写问题或重新生成。
- `expected_keywords`: Self-RAG, 反思, 忠于上下文, 重新检索, 重新生成

### 34

- `question_type`: `implementation`
- `question`: LangGraph 中如何把 agent、retrieve、grade_documents、rewrite_query 和 generate 组合成完整图？
- `expected_answer`: 可以用 StateGraph 定义共享状态，然后添加 agent、retrieve、grade_documents、rewrite_query 和 generate 等节点。通过 conditional edges 控制流程：agent 决定是否调用检索工具，检索后进入文档评分，不合格则改写 query 并重新检索，合格则进入 generate 生成答案。
- `expected_keywords`: StateGraph, conditional edges, agent, retrieve, grade_documents, generate

### 35

- `question_type`: `concept`
- `question`: LangGraph 的 subgraphs 解决了什么工程问题？
- `expected_answer`: Subgraphs 允许把复杂工作流拆成可复用的小图，并作为父图中的一个节点使用。这有助于模块化复杂 agent 流程，隔离局部状态和逻辑，也方便在多个工作流中复用相同子流程。
- `expected_keywords`: subgraphs, 模块化, 可复用, 父图, 复杂工作流

### 36

- `question_type`: `implementation`
- `question`: MCP 中客户端如何发现服务器暴露的 tools？
- `expected_answer`: 客户端可以发送 tools/list JSON-RPC 请求来发现服务器暴露的工具。服务器返回 tools 列表，每个 tool 通常包含 name、description、inputSchema 等字段，并且在工具较多时可以支持 pagination。
- `expected_keywords`: tools/list, JSON-RPC, name, description, inputSchema, pagination

### 37

- `question_type`: `troubleshooting`
- `question`: MCP tools 中 protocol errors 和 tool execution errors 有什么区别？
- `expected_answer`: Protocol errors 是协议层错误，例如工具不存在、参数无效或服务器错误，通常用 JSON-RPC error 表示。Tool execution errors 则表示工具调用请求本身成立，但工具内部执行失败，例如外部 API 返回错误或业务逻辑失败。
- `expected_keywords`: protocol errors, tool execution errors, JSON-RPC error, 参数无效, 工具执行失败

### 38

- `question_type`: `implementation`
- `question`: MCP 的 Python server-side implementation example 展示了哪些工具实现要点？
- `expected_answer`: 示例展示了如何创建 MCP server、注册工具函数、定义工具输入参数，并在工具内部执行外部逻辑后返回结果。它也体现了工具实现需要进行参数校验、错误处理，并遵守统一的 server-side tool 接口。
- `expected_keywords`: MCP server, 注册工具, 输入参数, 参数校验, 错误处理

### 39

- `question_type`: `comparison`
- `question`: Context Engineering 和 Prompt Engineering 的区别是什么？
- `expected_answer`: Prompt engineering 主要关注如何编写和组织指令，使模型按照期望方式回答。Context engineering 关注更大的上下文治理问题，包括选择哪些信息进入上下文、何时加载工具结果、如何维护历史、如何压缩和过滤文档状态等。
- `expected_keywords`: Prompt Engineering, Context Engineering, 指令, 上下文治理, 工具结果

### 40

- `question_type`: `concept`
- `question`: 为什么长上下文不一定等于更好的 agent 表现？
- `expected_answer`: 长上下文可能引入噪声，使模型注意力分散，并导致 context rot。有效的 context engineering 不追求盲目增加 token，而是保留高信号信息、移除无关内容，并在需要时动态加载或压缩上下文。
- `expected_keywords`: 长上下文, 噪声, 注意力分散, context rot, 高信号信息

### 41

- `question_type`: `concept`
- `question`: 长任务 agent 为什么需要 compaction 等 context engineering 技术？
- `expected_answer`: 长任务 agent 会在多轮行动中积累大量历史，容易超过上下文窗口或丢失关键目标。Compaction 等技术可以压缩历史、保留任务目标、关键状态和未完成事项，帮助 agent 在长时间执行中保持连续性。
- `expected_keywords`: 长任务 agent, compaction, 上下文窗口, 关键状态, 连续性

### 42

- `question_type`: `fact`
- `question`: Ragas 中 agent/tool use 相关指标主要评估什么？
- `expected_answer`: Ragas 中 agent/tool use 相关指标主要评估 agent 是否保持主题、是否正确调用工具以及工具调用是否符合任务需求。例如 topic adherence 关注对话是否围绕目标主题，tool call accuracy 关注工具选择和参数是否正确。
- `expected_keywords`: agent metrics, tool use, topic adherence, tool call accuracy, 工具调用

### 43

- `question_type`: `comparison`
- `question`: Ragas 的 factual correctness 和 semantic similarity 分别评估什么？
- `expected_answer`: Factual correctness 通常通过分解答案中的 claim，并与参考答案或证据比较来评估事实是否正确。Semantic similarity 则使用 embedding 或语义相似度方法，判断生成答案和参考答案在语义上是否接近。
- `expected_keywords`: factual correctness, semantic similarity, claim, 事实正确性, 语义相似度

### 44

- `question_type`: `fact`
- `question`: Ragas 中 Nvidia Metrics 主要覆盖哪些评估维度？
- `expected_answer`: Ragas 中的 Nvidia Metrics 主要覆盖 answer accuracy、context relevance、response groundedness 等维度，用于评估答案是否准确、检索上下文是否相关，以及回答是否基于提供的上下文。
- `expected_keywords`: Nvidia Metrics, answer accuracy, context relevance, response groundedness, groundedness

### 45

- `question_type`: `multi_hop`
- `question`: 在构建 Agentic RAG 系统时，LangGraph 的 StateGraph 和 OpenAI Agents SDK 的 tools/guardrails 分别承担什么职责？
- `expected_answer`: LangGraph 的 StateGraph 主要负责编排有状态、多节点的 agent 工作流，例如检索、评分、改写和生成。OpenAI Agents SDK 中的 tools 让 agent 能调用外部能力，guardrails 则对输入、输出或工具行为进行约束。三者结合时，LangGraph 管流程，tools 提供行动能力，guardrails 保证安全和可靠性。
- `expected_keywords`: StateGraph, workflow, tools, guardrails, 安全可靠

### 46

- `question_type`: `multi_hop`
- `question`: OpenAI Agents SDK 的 tools/guardrails 与 Ragas metrics 在一个 RAG 系统中如何互补？
- `expected_answer`: OpenAI Agents SDK 的 tools 和 guardrails 主要作用在运行时，负责让 agent 调用外部工具并约束输入、输出或工具行为。Ragas metrics 更偏评测层，用于衡量 RAG 或 agent 输出的上下文相关性、忠实度和答案质量。前者控制执行过程，后者量化系统效果。
- `expected_keywords`: tools, guardrails, Ragas metrics, 运行时控制, 评测

### 47

- `question_type`: `multi_hop`
- `question`: LightRAG 负责提升 RAG 检索能力，而 Ragas 负责评估 RAG 质量，这两者如何形成闭环？
- `expected_answer`: LightRAG 通过图索引和双层检索提升证据召回与关联知识发现能力。Ragas 则通过 context precision、context recall、faithfulness、answer relevancy 等指标评估检索和生成质量。将两者结合，可以先用 LightRAG 改进检索，再用 Ragas 指标验证改进是否真实有效。
- `expected_keywords`: LightRAG, 图索引, Ragas, context precision, faithfulness, 闭环

### 48

- `question_type`: `comparison`
- `question`: LightRAG 和 RAGFlow 在 RAG 系统定位上有什么区别？
- `expected_answer`: LightRAG 更强调通过图结构索引和轻量检索机制提升 RAG 的检索效率和关联知识发现能力。RAGFlow 更像完整 RAG 引擎和企业级工作流平台，强调文档理解、解析、上下文构建和 agent 模板。因此前者偏检索算法和索引设计，后者偏端到端 RAG 平台。
- `expected_keywords`: LightRAG, RAGFlow, 图结构索引, RAG 引擎, 端到端平台

### 49

- `question_type`: `multi_hop`
- `question`: RAGFlow 的上下文引擎和 LangGraph Agentic RAG 工作流如何结合？
- `expected_answer`: RAGFlow 可以作为文档解析、检索和上下文构建层，负责把复杂文档转成可检索证据。LangGraph 可以作为 agent workflow 编排层，决定何时检索、何时评分、何时改写 query 和何时生成答案。二者结合可以形成“文档理解 + agent 编排”的 RAG 系统。
- `expected_keywords`: RAGFlow, 上下文引擎, LangGraph, workflow 编排, query rewrite

### 50

- `question_type`: `multi_hop`
- `question`: LangGraph Agentic RAG 与 MCP tools specification 如何共同支持可扩展的工具调用式 RAG？
- `expected_answer`: LangGraph 负责编排 agent 状态和节点流转，例如检索、评分、改写和生成。MCP tools specification 为外部工具提供统一暴露和调用协议，使检索器、数据库、API 等能力能以标准工具形式接入。结合后，agent 可以在图流程中标准化调用外部工具。
- `expected_keywords`: LangGraph, MCP tools, 工具协议, 状态编排, 可扩展

### 51

- `question_type`: `multi_hop`
- `question`: MCP tools 和 Context Engineering 在 agent 系统中分别解决什么问题？
- `expected_answer`: MCP tools 解决外部能力如何以标准接口暴露给模型的问题，例如搜索、数据库、文件系统或 API 调用。Context Engineering 解决哪些信息应该在何时进入模型上下文的问题，包括工具结果、历史、文档和状态。前者是工具接口标准化，后者是上下文治理。
- `expected_keywords`: MCP tools, Context Engineering, 工具接口, 上下文治理, 工具结果

### 52

- `question_type`: `multi_hop`
- `question`: Context Engineering 和 DeepEval metrics 如何共同提升 agent 系统可靠性？
- `expected_answer`: Context Engineering 通过选择、压缩和组织上下文减少噪声，并提高模型获得关键信息的概率。DeepEval metrics 则用 LLM-as-a-judge、faithfulness、answer relevancy 等指标量化系统输出质量。前者改进输入和上下文，后者评估输出和行为，从而形成可靠性改进闭环。
- `expected_keywords`: Context Engineering, DeepEval metrics, 上下文压缩, faithfulness, answer relevancy, 可靠性

### 53

- `question_type`: `implementation`
- `question`: OpenAI Agents SDK 中为什么建议用 tool_namespace 组织相关工具？
- `expected_answer`: tool_namespace 可以把相关工具分组，减少工具列表混乱，让 agent 更容易理解哪些工具属于同一能力域。每个 namespace 应保持较小，避免 agent 面对过多工具选择。相比大量分散工具，namespace 或 hosted MCP server 更便于管理和扩展。
- `expected_keywords`: tool_namespace, 工具分组, 工具列表, hosted MCP server, 可管理性

### 54

- `question_type`: `concept`
- `question`: 为什么 LightRAG 对 LLM 和技术栈的要求高于传统 RAG？
- `expected_answer`: LightRAG 不只是简单向量检索，它在索引阶段通常需要实体和关系抽取、图结构构建以及双层检索，因此对 LLM 能力、上下文长度、embedding 模型和存储检索组件有更高要求。相比传统 RAG，它的实现复杂度和系统依赖更高。
- `expected_keywords`: LightRAG, 实体关系抽取, 图结构, 双层检索, 传统 RAG


---

## 6. 交付文件说明

本次已生成两个可直接使用的候选文件：

1. `qa_revised_candidate.jsonl`
   - 删除编号：2,6,9,14,16,21
   - 保留 48 条
   - 适合希望保留更多样本时使用

2. `qa_revised_candidate_compact.jsonl`
   - 删除编号：2,6,9,14,16,21 以及可选去重编号 1,7,10,13,19,22,25
   - 保留 41 条
   - 适合希望数据集更精炼时使用

---

## 7. 后续复查建议

在正式发布 TechDocQA v1 前，还需要做一次 gold evidence 复查：

```text
1. 对每条样本读取 suggested_gold_chunk_ids；
2. 在 chunks.jsonl 中找到对应 chunk；
3. 检查 expected_answer 的每个关键结论是否能被 gold chunk 支持；
4. 如果不能支持，修改 gold chunk 或重写答案；
5. 对 multi_hop 样本尤其要检查两个 gold chunks 是否都被答案实际使用。
```

建议用抽查 + 自动检查结合：

- 全量自动检查字段完整性；
- 人工重点检查 multi_hop、implementation、troubleshooting 类型；
- 最终输出 `techdocqa_v1.jsonl`。
