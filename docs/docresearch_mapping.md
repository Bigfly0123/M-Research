# 从 IRIS 到 DocResearch-Agent 的迁移映射文档

> 目标：把 IRIS 中值得学习的 Agentic Workflow、RAG、Reviewer Loop 经验，转化为 DocResearch-Agent 的项目设计。本文档强调“借鉴思想，不复制业务”。

---

## 1. 项目定位差异

### IRIS 的定位

IRIS 是一个自动化深度调研与报告生成系统。

核心目标：

```text
输入研究主题 / 文档
    ↓
规划调研路径
    ↓
检索本地文档或网络信息
    ↓
生成深度报告
    ↓
Reviewer 审查
    ↓
必要时返工
```

### DocResearch-Agent 的定位

DocResearch-Agent 是一个面向技术文档的 Agentic RAG 评测与自修复系统。

核心目标：

```text
上传技术文档 / 项目文档 / 论文 / README
    ↓
用户提出技术问题
    ↓
系统检索证据
    ↓
生成带引用答案
    ↓
Judge 检查答案可靠性
    ↓
发现问题后自动修复
    ↓
输出答案、引用、trace 和评测结果
```

### 一句话区别

```text
IRIS 关注：如何自动生成一篇调研报告。
DocResearch-Agent 关注：如何让技术文档问答更可靠、可验证、可修复。
```

---

## 2. 核心模块映射

| IRIS 模块 | IRIS 作用 | DocResearch-Agent 对应模块 | 改造方向 |
|---|---|---|---|
| Intent Router | 判断是新研究还是修改已有报告 | Query Planner | 判断问题类型、是否需要检索、是否需要多步检索 |
| Task Planner | 规划研究任务和搜索步骤 | Retrieval Planner / Query Decomposer | 生成检索计划、必要时拆分复杂问题 |
| Deep Researcher | 检索本地文档或网络内容 | Hybrid Retriever | 使用 Dense + BM25 + Rerank 检索技术文档证据 |
| Relevance Grader | 判断文档和问题是否相关 | Evidence Selector / Retrieval Judge | 判断 chunk 是否能支持答案 |
| Content Writer | 生成深度报告 | Answer Generator | 基于证据生成带引用答案 |
| Quality Reviewer | 审查报告质量 | Answer Judge | 判断 relevance、faithfulness、citation support |
| Refiner | 根据用户指令局部修改报告 | Repair Router / Answer Rewriter | 根据失败类型修复答案或重新检索 |
| SQLite Checkpoint | 保存会话状态 | Trace Store / Eval Log | 保存 Agent 执行路径、Judge 分数、修复动作 |
| SSE 流式输出 | 展示生成进度 | Trace Streaming / Dashboard | 展示每个节点的执行状态 |

---

## 3. 工作流迁移

### 3.1 IRIS 工作流

```text
User Input
    ↓
Intent Router
    ├── NEW_TOPIC → Task Planner
    └── REFINE → Content Refiner → Final Output
Task Planner
    ↓
Deep Researcher
    ↓
Relevance Grader
    ↓
Content Writer
    ↓
Quality Reviewer
    ├── FAIL → Back to Planner
    └── PASS → Final Output
```

### 3.2 DocResearch-Agent 工作流

```text
User Question
    ↓
Query Planner
    ↓
Hybrid Retriever
    ↓
Evidence Selector
    ↓
Answer Generator
    ↓
Answer Judge
    ├── PASS → Final Answer
    └── FAIL → Repair Router
                    ├── retrieval_miss → Query Rewrite + Retrieve
                    ├── weak_evidence → Increase top_k + Rerank
                    ├── citation_error → Reselect Evidence
                    ├── hallucination → Regenerate with Evidence Only
                    └── incomplete_answer → Decompose Query
```

### 3.3 关键区别

IRIS 的修复逻辑：

```text
FAIL → Back to Planner
```

DocResearch-Agent 的修复逻辑：

```text
FAIL → failure_type → repair_action → specific node
```

这就是 DocResearch-Agent 的核心升级点。

---

## 4. AgentState 映射

### 4.1 IRIS AgentState

```python
query: str
plan: List[str]
search_results: List[str]
final_report: str
critique: str
revision_number: int
review_status: str
search_mode: str
should_stop: bool
```

### 4.2 DocResearch-Agent AgentState

```python
class AgentState(TypedDict):
    # User input
    question: str
    query_type: str
    rewritten_query: str

    # Retrieval
    retrieval_strategy: str
    retrieved_chunks: list[dict]
    selected_evidence: list[dict]

    # Generation
    answer: str
    citations: list[dict]

    # Judge and repair
    judge_result: dict
    failure_type: str
    repair_action: str
    repair_count: int
    max_repair_count: int

    # Observability
    trace: list[dict]
    latency_ms: float
    token_cost: float
```

### 4.3 字段迁移解释

| IRIS 字段 | DocResearch-Agent 字段 | 改造原因 |
|---|---|---|
| query | question | 从研究主题变成技术问题 |
| plan | query_type / rewritten_query / retrieval_strategy | 从报告规划变成检索规划 |
| search_results | retrieved_chunks | 从搜索结果变成带 metadata 的 chunk |
| final_report | answer | 从长报告变成问答答案 |
| critique | judge_result.reason | 从报告审查意见变成结构化判断原因 |
| revision_number | repair_count | 从修改轮次变成修复次数 |
| review_status | judge_result.pass | 从 PASS/FAIL 变成更细评分 |
| search_mode | retrieval_strategy | 从 document/hybrid 变成 vector/bm25/hybrid/rerank |
| should_stop | stop_reason / judge_result | 用于证据不足时停止硬答 |

---

## 5. RAG 模块迁移

### 5.1 IRIS 已有 RAG 链路

IRIS 的 RAG engine 大致是：

```text
PDF Loader
    ↓
RecursiveCharacterTextSplitter
    ↓
Embedding
    ↓
ChromaDB
    ↓
Vector Similarity Search
    ↓
CrossEncoder Rerank
    ↓
Top-k Documents
```

### 5.2 DocResearch-Agent 目标 RAG 链路

DocResearch-Agent 应升级为：

```text
PDF / Markdown / TXT / README Loader
    ↓
Chunking + Metadata
    ↓
Dense Index + BM25 Index
    ↓
Hybrid Retrieval
    ↓
Deduplication
    ↓
Rerank
    ↓
Evidence Selector
    ↓
Citation-aware Answer Generation
```

### 5.3 具体新增点

| 能力 | IRIS | DocResearch-Agent |
|---|---|---|
| PDF 解析 | 有 | 保留 |
| Markdown / README | 不突出 | 新增 |
| Vector DB | Chroma | 可用 Chroma，后续可切 Qdrant |
| Rerank | CrossEncoder | 保留并参数化 |
| BM25 | 无或不突出 | 新增 |
| Hybrid Retrieval | README 中有混合概念，但核心代码以 vector + rerank 为主 | 明确实现 Dense + BM25 合并 |
| Metadata | 基础 document metadata | 强化 source/page/section/chunk_id |
| Evidence Selector | Relevance Grader 粗粒度 | 新增细粒度证据选择 |
| Citation Verification | 不突出 | 新增 |

---

## 6. Reviewer 到 Answer Judge 的升级

### 6.1 IRIS Reviewer

IRIS Reviewer 的目标是判断报告质量是否通过。

典型输出：

```text
review_status = PASS / FAIL
critique = 审查意见
```

### 6.2 DocResearch-Agent Answer Judge

DocResearch-Agent 的 Judge 应输出结构化结果：

```json
{
  "pass": false,
  "answer_relevance": 0.82,
  "faithfulness": 0.71,
  "citation_support": 0.60,
  "failure_type": "citation_error",
  "reason": "答案中的关键结论没有被引用证据直接支持",
  "repair_action": "reselect_evidence"
}
```

### 6.3 Judge 检查维度

| 维度 | 说明 |
|---|---|
| answer_relevance | 是否回答了用户问题 |
| faithfulness | 答案是否忠于检索证据 |
| citation_support | 引用是否真的支持答案 |
| completeness | 是否遗漏关键点 |
| hallucination_risk | 是否包含无证据推断 |
| repair_needed | 是否需要修复 |

---

## 7. Self-Repair 设计

### 7.1 IRIS 修复方式

IRIS 的方式：

```text
Reviewer FAIL → 回到 Planner
```

这个方式简单，但不够精准。

### 7.2 DocResearch-Agent 修复方式

DocResearch-Agent 应使用失败类型驱动修复：

| failure_type | 触发原因 | repair_action | 回到哪个节点 |
|---|---|---|---|
| retrieval_miss | 没找到相关证据 | rewrite_query | Query Planner / Retriever |
| weak_evidence | 找到的证据太弱 | increase_top_k | Retriever |
| citation_error | 引用不支持答案 | reselect_evidence | Evidence Selector |
| hallucination | 答案包含无证据内容 | regenerate_with_evidence_only | Answer Generator |
| incomplete_answer | 答案不完整 | decompose_query | Query Planner |
| off_topic | 答非所问 | replan | Query Planner |

### 7.3 一周 MVP 版本

一周内不需要做所有修复，只做三个即可：

```text
citation_error → regenerate_with_evidence_only
weak_evidence → increase_top_k
incomplete_answer → query_rewrite
```

---

## 8. 从 IRIS 的报告生成转向技术文档 QA

### 8.1 不要保留的 IRIS 业务

不建议保留：

```text
长篇调研报告生成
章节式报告写作
用户要求“扩写第一章”式 Refiner
Web Search 优先的深度调研
复杂前端报告渲染
```

### 8.2 要改成的业务

DocResearch-Agent 的业务应是：

```text
上传技术文档
问一个技术问题
返回短而准的答案
展示引用证据
展示 Agent trace
展示 Judge 结果
必要时展示修复前后对比
```

### 8.3 示例问题

```text
这个项目的核心模块有哪些？
这个 README 里提到的 reranker 作用是什么？
论文中的 self-repair 机制如何工作？
某个 API 参数应该怎么配置？
这段文档是否说明了支持 hybrid retrieval？
为什么这次回答触发了 citation_error？
```

---

## 9. 从 IRIS 前端到 DocResearch 展示层

### 9.1 IRIS 前端特点

IRIS 前端使用 Vue 3 + Tailwind，支持：

```text
文件上传
对话输入
状态流转展示
Markdown 报告渲染
公式渲染
SSE 打字机效果
```

### 9.2 当前阶段不建议深入

由于时间紧，DocResearch-Agent 第一版不建议复刻 IRIS 前端。

推荐路线：

```text
第一版：命令行 / FastAPI Swagger / JSON 输出
第二版：Streamlit dashboard
第三版：再考虑 Vue 或 React
```

### 9.3 Streamlit 展示目标

Streamlit 页面只需要展示：

```text
上传文档
输入问题
最终答案
引用 chunk
Agent trace
Judge 结果
Repair 动作
```

这已经足够用于简历 demo。

---

## 10. 一周开发范围映射

| 天数 | 任务 | 借鉴 IRIS | 自己新增 |
|---|---|---|---|
| Day 1 | 阅读 IRIS 后端，写学习笔记 | README / graph / state / rag | mapping 文档 |
| Day 2 | 新建 DocResearch 项目骨架 | 后端目录结构 | 简化 app 结构 |
| Day 3 | 基础 RAG | PDF → chunk → Chroma | Markdown / citation 输出 |
| Day 4 | Hybrid Retrieval | vector + rerank 思路 | BM25 + merge + dedup |
| Day 5 | LangGraph 工作流 | planner/researcher/writer/reviewer | planner/retriever/generator/judge |
| Day 6 | Judge + Repair | reviewer loop | failure_type-based repair |
| Day 7 | Eval + README | trace 思路 | eval_report + 简历包装 |

---

## 11. 两周增强范围

如果有第二周，建议新增：

```text
1. CrossEncoder reranker 参数化
2. Evidence Selector 独立节点
3. 20 条 QA 扩展到 50 条
4. Streamlit demo 页面
5. eval_report 中增加 baseline / hybrid / repair 对比
6. docs/tech_notes 记录大厂博客技术吸收
7. README 增加架构图和项目亮点
```

不要新增：

```text
复杂前端
自动爬虫
多用户系统
权限系统
分布式部署
完整 LLMOps 平台
```

---

## 13. 最终迁移原则

### 13.1 可以借鉴

```text
LangGraph 状态机
AgentState 设计方式
Planner / Researcher / Writer / Reviewer 分层思想
RAG engine 的 PDF + Chroma + rerank 思路
Reviewer 失败后循环的思想
SSE / trace 展示思想
```

### 13.2 不应照搬

```text
深度报告生成业务
Refiner 修改报告业务
复杂 Vue 前端
完整 Tavily Web Search 流程
粗粒度 FAIL → Planner 修复逻辑
```

### 13.3 必须变成自己的

```text
技术文档 QA 场景
Hybrid Retrieval
Evidence Selector
Citation-aware Answer Generation
Answer Judge
Failure Attribution
Self-Repair
Evaluation Runner
Eval Report
```

---

## 14. 总结

IRIS 给你的不是最终项目，而是一个学习模板。

你要吸收的是：

```text
如何组织 Agentic Workflow
如何设计共享状态
如何把 RAG 接进 Agent
如何加 Reviewer Loop
如何展示执行过程
```

你要输出的是：

```text
一个面向技术文档问答的可靠 RAG 系统
一个能判断答案是否可信的 Answer Judge
一个能根据失败类型自动修复的 Repair Router
一个能用评测报告证明改进效果的工程项目
```

这就是从 IRIS 走向 DocResearch-Agent 的正确迁移路径。
