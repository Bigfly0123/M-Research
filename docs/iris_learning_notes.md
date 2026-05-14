# IRIS 学习笔记：从学习性 Agent 项目中提炼可复用经验

> 目标：这份笔记不是为了完整复刻 IRIS，而是为了快速理解 IRIS 的后端技术结构，并提炼出能迁移到 `DocResearch-Agent` 的经验。
>
> 建议学习重点：**后端 Agent 工作流、RAG 检索、Reviewer 自审循环、状态管理、API/SSE 交互思路**。前端 Vue 页面可以先放到最后。

---

## 1. IRIS 项目定位

IRIS，全称 `Intelligent Research Insight System`，是一个基于 Agentic Workflow 的自动化深度调研与报告生成系统。

它的核心目标不是普通聊天问答，而是：

```text
用户输入研究主题 / 上传文档
        ↓
系统判断意图
        ↓
规划研究路径
        ↓
检索本地文档或网络信息
        ↓
撰写深度报告
        ↓
Reviewer 审查报告质量
        ↓
不合格则回到 Planner 重新规划和修改
        ↓
输出最终报告
```

所以 IRIS 的本质是一个：

> **基于 LangGraph 的研究型 Agent 工作流项目。**

它有两个关键价值：

1. 展示了如何把 LLM 应用从“单次调用”变成“多节点工作流”；
2. 展示了如何通过 Reviewer 和循环边实现初步的自我修正。

---

## 2. IRIS 的核心技术栈

根据仓库 README，IRIS 的主要技术栈如下。

### 2.1 后端技术栈

| 类别 | 技术 | 作用 |
|---|---|---|
| 后端框架 | Python 3.10+ / FastAPI | 提供 API 服务、处理上传文件、驱动 Agent 工作流 |
| Agent 框架 | LangChain / LangGraph | 构建多节点 Agent 工作流，支持条件分支和循环 |
| 向量数据库 | ChromaDB | 存储本地文档 chunk 的向量索引 |
| 文档解析 | PyPDFLoader | 加载 PDF 文档 |
| 文本切分 | RecursiveCharacterTextSplitter | 将文档切成适合检索的 chunk |
| Embedding | DashScopeEmbeddings / HuggingFaceEmbeddings | 将文本片段转成向量 |
| Reranker | sentence-transformers CrossEncoder | 对初步召回结果进行精排 |
| 持久化 | SQLite / aiosqlite / AsyncSqliteSaver | 用于 LangGraph checkpoint 和会话级记忆 |
| 网络搜索 | Tavily Search API | 在混合模式下补充网络搜索结果 |
| 流式输出 | SSE | 将 Agent 状态和生成内容实时推送到前端 |

### 2.2 前端技术栈

| 类别 | 技术 | 作用 |
|---|---|---|
| 前端框架 | Vue 3 | 构建交互页面 |
| UI 样式 | Tailwind CSS | 快速构建现代化界面 |
| Markdown 渲染 | markdown-it | 渲染模型生成的 Markdown 报告 |
| 数学公式 | markdown-it-katex / KaTeX | 渲染 LaTeX 公式 |
| API 通信 | 前端 service 封装 | 调用后端 API / 接收 SSE |

### 2.3 当前学习建议

你现在不需要优先学 Vue、Tailwind、前端组件和 UI 动效。

最应该优先学习：

```text
LangGraph 工作流
AgentState 状态设计
RAG engine
Reviewer 自审循环
FastAPI 如何封装 Agent 接口
SSE 的思想，而不是具体前端实现
```

---

## 3. IRIS 的系统架构

IRIS README 中的核心架构可以概括为：

```text
User Input
    ↓
Intent Router
    ├── NEW_TOPIC → Task Planner
    └── REFINE    → Content Refiner → Final Output
Task Planner
    ↓
Deep Researcher
    ↓
Relevance Grader
    ├── Doc Only & Not Relevant
    │       → Stop & Warn User
    │
    ├── Hybrid Mode & Not Relevant
    │       → Web Search
    │       → Content Writer
    │
    └── Relevant
            → Content Writer
                    ↓
            Quality Reviewer
                    ├── FAIL → Back to Planner
                    └── PASS → Final Output
```

这个架构最值得学习的不是每个业务节点本身，而是这三个思想：

1. **Router：先判断用户意图，再决定流程入口；**
2. **Graph：不是线性链条，而是可分支、可循环的状态机；**
3. **Reviewer Loop：生成结果后由审查节点判断是否需要返工。**

---

## 4. IRIS 的后端目录结构

README 中给出的后端结构大致如下：

```text
backend/
├── app/
│   ├── api/          # FastAPI 路由与中间件，负责 SSE 流式分发等
│   ├── graph/        # LangGraph 核心逻辑
│   │   ├── nodes/    # Planner, Researcher, Writer, Router, Refiner, Reviewer
│   │   ├── state.py  # AgentState 定义
│   │   └── graph.py  # 状态机拓扑构建与条件边连线
│   ├── rag/          # 文档解析、向量化与检索引擎
│   └── tools/        # Tavily 等外部工具
├── main.py           # FastAPI 入口
└── requirements.txt
```

### 对学习的启发

对于 DocResearch-Agent，完全可以借鉴这种后端分层：

```text
app/
├── api/              # 上传、问答、评测、trace API
├── graph/            # LangGraph 工作流
├── rag/              # 文档解析、索引、检索、rerank
├── eval/             # 评测集、评测指标、评测报告
└── storage/          # trace、文档 metadata、实验记录
```

---

## 5. AgentState：共享状态设计

IRIS 的 `AgentState` 是一个 `TypedDict`，用于在不同节点之间传递中间结果。

它的核心字段包括：

```python
query: str                 # 用户原始问题
plan: List[str]            # 规划的搜索步骤
search_results: List[str]  # 搜索到的内容
final_report: str          # 最终报告
critique: str              # 审查意见
revision_number: int       # 当前修改轮次，防止死循环
review_status: str         # PASS / FAIL
search_mode: str           # document / hybrid
should_stop: bool          # 是否提前停止
```

### 5.1 这个设计的意义

IRIS 的状态不是只保存最终答案，而是保存了完整中间过程：

- 用户问题；
- 规划结果；
- 检索结果；
- 生成结果；
- 审查意见；
- 是否通过；
- 当前修改次数；
- 是否停止。

这说明 Agentic 系统不应该只关心“输入和输出”，而应该关心整个执行轨迹。

### 5.2 对 DocResearch-Agent 的启发

DocResearch-Agent 的状态可以设计成：

```python
class AgentState(TypedDict):
    question: str
    query_type: str
    rewritten_query: str

    retrieved_chunks: list[dict]
    selected_evidence: list[dict]

    answer: str
    citations: list[dict]

    judge_result: dict
    failure_type: str
    repair_action: str
    repair_count: int

    trace: list[dict]
    latency_ms: float
    token_cost: float
```

核心变化是：

| IRIS 字段 | DocResearch-Agent 字段 |
|---|---|
| query | question |
| plan | query_type / rewritten_query / retrieval_plan |
| search_results | retrieved_chunks |
| final_report | answer |
| critique | judge_result.reason |
| review_status | judge_result.pass |
| revision_number | repair_count |
| should_stop | stop_reason / should_stop |

---

## 6. LangGraph 工作流设计

IRIS 的 `graph.py` 使用 `StateGraph(AgentState)` 构建工作流，大致包括：

```python
workflow = StateGraph(AgentState)
workflow.add_node("planner", plan_node)
workflow.add_node("researcher", research_node)
workflow.add_node("writer", write_node)
workflow.add_node("reviewer", review_node)
workflow.add_node("refiner", refine_node)
```

入口使用条件路由：

```python
workflow.set_conditional_entry_point(
    route_query,
    {
        "planner": "planner",
        "refiner": "refiner"
    }
)
```

主流程为：

```text
planner → researcher → writer → reviewer
```

当 reviewer 失败时，会回到 planner：

```text
reviewer FAIL → planner
reviewer PASS → END
```

并通过 `revision_number >= 3` 限制最大重试次数，防止无限循环。

### 对 DocResearch-Agent 的启发

DocResearch-Agent 可以使用类似图结构：

```text
query_planner
    ↓
hybrid_retriever
    ↓
evidence_selector
    ↓
answer_generator
    ↓
answer_judge
    ├── PASS → END
    └── FAIL → repair_router
                  ├── retrieval_miss → query_planner / hybrid_retriever
                  ├── weak_evidence → hybrid_retriever
                  ├── citation_error → evidence_selector
                  └── hallucination → answer_generator
```

相比 IRIS 的改进点是：

- IRIS 的失败处理比较粗：`FAIL → planner`；
- DocResearch-Agent 应该更细：`failure_type → repair_action`。

---

## 7. IRIS 的 RAG 检索模块

IRIS 的 `rag/engine.py` 中包含几个关键能力：

### 7.1 文档加载

使用 `PyPDFLoader` 加载 PDF：

```python
loader = PyPDFLoader(file_path)
docs = loader.load()
```

### 7.2 文本切分

使用 `RecursiveCharacterTextSplitter`：

```python
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,
    chunk_overlap=50
)
splits = text_splitter.split_documents(docs)
```

这个设置说明 IRIS 的 chunk 粒度偏小，适合问答和局部证据检索。

### 7.3 向量化与 Chroma 存储

使用 Chroma 作为本地向量数据库：

```python
Chroma.from_documents(
    documents=all_splits,
    embedding=embeddings,
    persist_directory=DB_PATH
)
```

Embedding 默认使用 DashScope：

```python
embeddings = DashScopeEmbeddings(model='text-embedding-v4')
```

同时代码中保留了 HuggingFace 本地 embedding 的备选思路。

### 7.4 两阶段检索与 Rerank

IRIS 定义了 `RerankRetriever`：

```text
第一阶段：Chroma similarity_search 召回 fetch_k 个候选
第二阶段：CrossEncoder 对 query-doc pair 打分
第三阶段：按 rerank 分数排序，取 top_k
```

默认参数：

```text
top_k = 5
fetch_k = 20
reranker = cross-encoder/ms-marco-MiniLM-L-6-v2
```

这个设计非常值得迁移。

### 7.5 对 DocResearch-Agent 的启发

IRIS 已经有：

```text
PDF → chunk → embedding → Chroma → vector recall → CrossEncoder rerank
```

DocResearch-Agent 应该在此基础上补充：

```text
BM25 keyword retrieval
Hybrid merge
metadata filter
Evidence Selector
citation verification
retrieval evaluation
```

也就是从：

```text
Vector + Rerank
```

升级为：

```text
Dense Retrieval + BM25 + Rerank + Evidence Selector + Eval
```

---

## 8. IRIS 的 Reviewer 机制

IRIS 中 Reviewer 的作用是检查 Writer 生成的报告是否合格。

主流程中：

```text
writer → reviewer
```

如果 Reviewer 返回：

```text
review_status = PASS
```

则结束。

如果返回：

```text
review_status = FAIL
```

则回到 planner，并带上 critique 作为下一轮规划和修改的参考。

### 8.1 优点

这个设计有几个好处：

1. 生成不是一次性完成，而是有审查环节；
2. 审查意见可以进入下一轮状态；
3. 通过 `revision_number` 限制循环次数；
4. 让系统具备初步的 self-correction 能力。

### 8.2 局限

但对于 DocResearch-Agent 来说，IRIS 的 Reviewer 还不够细。

IRIS 主要判断：

```text
报告质量是否通过
```

DocResearch-Agent 需要判断：

```text
答案是否回答问题
答案是否被证据支持
引用是否真实支撑结论
是否出现幻觉
是否需要重新检索
失败类型是什么
应该执行哪种修复动作
```

所以要把 Reviewer 升级成结构化 `Answer Judge`。

---

## 9. IRIS 的动态路由与停止机制

IRIS 的 Researcher 后有一个路由函数：

```python
def route_after_research(state):
    if state.get("should_stop", False):
        return END
    else:
        return "writer"
```

这说明 IRIS 不是每次都强制生成答案，而是可以根据文档相关性决定是否终止。

README 中也提到：

- 如果是纯文档模式，而上传文档与问题无关，系统会终止并警告；
- 如果是混合模式，而文档不相关，则会降级到 Web Search。

### 对 DocResearch-Agent 的启发

DocResearch-Agent 也应该具备类似控制逻辑：

```text
如果检索不到足够证据：
    不要硬编答案
    标记 retrieval_miss
    尝试 query rewrite 或扩大 top_k
    仍失败则明确告诉用户证据不足
```

这对应项目的可靠性目标：

> 不只是回答，而是知道什么时候不应该回答。

---

## 10. IRIS 的 Session Persistence 思路

IRIS 使用 SQLite checkpoint 保存会话级状态，并结合 Intent Router 区分：

```text
NEW_TOPIC：开启新研究
REFINE：基于已有报告进行局部修改
```

这个设计对于 DocResearch-Agent 第一版不是必须，但可以作为后续增强。

### 可迁移方向

后续可以加入：

```text
多轮问答记忆
同一批文档上的连续追问
保存上一次检索结果
保存 Agent trace
保存每次 Judge 结果和 Repair 动作
```

对于一周版 MVP，建议只做：

```text
trace 存储 / 日志输出
```

不必做完整 checkpoint。

---

## 11. IRIS 的 SSE 流式输出思路

IRIS 使用 SSE 将 Agent 内部状态流转和最终报告推送给前端。

这对用户体验很重要，因为 Agent 工作流可能包括多个节点，等待时间较长。如果没有流式状态，用户只会看到“卡住了”。

### 对 DocResearch-Agent 的启发

DocResearch-Agent 可以先不做复杂前端，但应该保留 trace 输出：

```text
[planner] query_type = concept
[retriever] strategy = hybrid
[evidence_selector] selected = 4 chunks
[generator] answer generated
[judge] failure_type = citation_error
[repair] action = regenerate_with_evidence_only
[end] final answer
```

第一版可以打印到终端 / 返回 JSON。

第二版再做 Streamlit 或前端页面展示。

---

## 12. IRIS 中哪些东西暂时不学？

时间紧时，不建议一开始学：

```text
Vue 3 组件结构
Tailwind 视觉样式
Siri 呼吸灯动效
复杂 Markdown / KaTeX 渲染
完整 SSE 前端处理
用户体验细节
```

这些可以最后包装时再看。

当前优先级应该是：

```text
Agent workflow > RAG > Rerank > Judge > Repair > Eval > UI
```

---

## 13. IRIS 对 DocResearch-Agent 的核心启发总结

| IRIS 经验 | 迁移到 DocResearch-Agent |
|---|---|
| 用 LangGraph 构建多节点状态机 | 用 LangGraph 构建 RAG 问答、Judge、Repair 工作流 |
| AgentState 保存中间状态 | 保存检索结果、证据、答案、引用、Judge 结果、Repair 轨迹 |
| Router 区分新任务和修改任务 | Query Planner 判断问题类型和检索策略 |
| Researcher 做动态检索 | Hybrid Retriever 做 BM25 + 向量检索 |
| Relevance Grader 判断文档相关性 | Evidence Selector / Retrieval Judge 判断证据是否可用 |
| Writer 生成报告 | Answer Generator 生成带引用答案 |
| Reviewer 审查报告 | Answer Judge 检查 faithfulness / citation / relevance |
| FAIL 后回到 Planner | failure_type 驱动精准修复 |
| SSE 展示状态流转 | trace 展示 Agent 执行路径 |
| SQLite checkpoint 保存会话 | trace store / eval log 保存实验过程 |

---

## 14. 一周内最该吸收的 IRIS 经验

如果只用 1 天学习 IRIS，按这个顺序看：

1. `README.md`：理解整体目标和架构图；
2. `backend/app/graph/state.py`：理解状态字段；
3. `backend/app/graph/graph.py`：理解节点、边、条件路由、循环；
4. `backend/app/rag/engine.py`：理解 PDF、chunk、Chroma、rerank；
5. `backend/app/api/`：粗略理解 API 如何触发 Agent，不必深挖；
6. 暂时跳过 `frontend/`。

学习输出应该是两个文件：

```text
docs/iris_learning_notes.md
docs/docresearch_mapping.md
```

这两份文档写完后，就可以开始实现自己的 DocResearch-Agent。

---

## 15. 最终判断

IRIS 对你的价值不是“拿来当成最终项目”，而是：

> 帮你快速理解一个 Agentic RAG 项目应该如何组织后端工程、状态机、检索器和审查循环。

你要从中吸收：

```text
Graph-based workflow
Shared AgentState
RAG + rerank engine
Reviewer loop
Trace / streaming 思路
```

然后把它改造成自己的方向：

```text
技术文档 QA
Hybrid Retrieval
Evidence Selector
Answer Judge
Self-Repair
Evaluation Report
```

这就是从 IRIS 学经验、但最后变成自己项目的正确方式。
