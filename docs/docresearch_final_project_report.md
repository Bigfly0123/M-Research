# DocResearch-Agent 最终项目报告

## 项目名称

**DocResearch-Agent：面向技术文档的 Agentic RAG 评测与自修复系统**

---

## 1. 项目背景

在大模型应用开发中，RAG 是最常见的落地形态之一。但普通 RAG 系统通常存在以下问题：

1. 检索结果不稳定，尤其在技术文档中遇到函数名、参数名、模块名时，向量检索可能召回不准；
2. LLM 容易根据弱证据生成看似合理但缺乏依据的答案；
3. 引用片段不一定真正支持答案结论；
4. 系统缺少评测机制，开发者只能凭感觉判断效果；
5. 答案出错后缺少自动修复机制，只能重新提问或人工调试。

因此，本项目计划实现一个面向技术文档的 Agentic RAG 系统，不只完成“检索 + 生成”，还要加入：

```text
Hybrid Retrieval
Evidence Selection
Citation-aware Answer Generation
Answer Judge
Self-Repair
Trace Logging
Evaluation Report
```

项目目标是让 RAG 系统具备更强的可靠性、可解释性和可评测性。

---

## 2. 项目定位

DocResearch-Agent 的定位不是普通知识库问答，而是：

> 面向论文、README、技术博客、项目文档、API 文档的 Agentic RAG 评测与自修复系统。

它的核心能力包括：

```text
1. 解析技术文档；
2. 建立文档索引；
3. 使用混合检索找到相关证据；
4. 基于证据生成带引用答案；
5. 使用 Answer Judge 检查答案是否可靠；
6. 根据失败类型自动修复；
7. 记录 Agent 执行 trace；
8. 通过评测集比较不同 RAG 策略效果。
```

一句话描述：

> 一个能读技术文档、找证据、生成答案、检查自己、修复错误并输出评测报告的 Agentic RAG 系统。

---

## 3. 项目可以做什么

### 3.1 技术文档问答

用户上传技术文档后，可以提问：

```text
这个项目的核心模块有哪些？
这个论文方法的主要流程是什么？
README 中的 reranker 起什么作用？
某个 API 参数应该如何配置？
这个系统有没有提到 self-repair？
```

系统输出：

```text
答案
引用来源
引用 chunk
文件路径 / 页码 / section
Agent trace
Judge 结果
是否经过 repair
```

---

### 3.2 证据可追溯回答

每个关键结论都要对应证据。

输出格式示例：

```json
{
  "answer": "该模块用于对初步召回的文档片段进行精排，从而提升最终证据质量。",
  "citations": [
    {
      "source": "rag_engine.md",
      "chunk_id": "chunk_012",
      "section": "Rerank Retriever",
      "text": "CrossEncoder rerank is used to reorder retrieved documents..."
    }
  ]
}
```

---

### 3.3 Agent 执行轨迹展示

系统记录每一步：

```text
[planner] query_type = concept
[retriever] strategy = hybrid, top_k = 5
[evidence_selector] selected_chunks = 3
[generator] answer generated with citations
[judge] pass = false, failure_type = citation_error
[repair] action = regenerate_with_evidence_only
[generator] regenerated answer
[judge] pass = true
[end] final answer
```

这能体现项目不是简单 RAG chain，而是可观测的 Agent 工作流。

---

### 3.4 自动判断答案质量

Answer Judge 检查：

```text
答案是否回答问题
答案是否基于证据
引用是否支持结论
是否出现幻觉
是否遗漏关键点
是否需要修复
```

Judge 输出示例：

```json
{
  "pass": false,
  "answer_relevance": 0.86,
  "faithfulness": 0.72,
  "citation_support": 0.58,
  "failure_type": "citation_error",
  "reason": "答案中的关键结论没有被引用片段直接支持",
  "repair_action": "regenerate_with_evidence_only"
}
```

---

### 3.5 自动修复答案

根据失败类型执行不同修复策略：

| 失败类型 | 说明 | 修复动作 |
|---|---|---|
| retrieval_miss | 没检索到关键证据 | query rewrite + 重新检索 |
| weak_evidence | 证据太弱 | 增加 top_k + rerank |
| citation_error | 引用不支持答案 | 重新选择证据或重新生成 |
| hallucination | 答案包含无证据内容 | 严格基于证据重新生成 |
| incomplete_answer | 答案不完整 | 拆分问题后重答 |

一周 MVP 中只需要支持 2～3 种修复即可。

---

### 3.6 RAG 策略评测

构建小型 QA 评测集，对比不同策略：

```text
baseline vector RAG
hybrid retrieval RAG
hybrid + rerank RAG
agentic RAG
agentic RAG + repair
```

评测指标：

```text
retrieval_hit_rate
citation_accuracy
judge_pass_rate
repair_success_rate
latency
failure_distribution
```

最终输出：

```text
reports/eval_report.md
```

---

## 4. 现有基础

### 4.1 IRIS 学习项目经验

之前复现 / 学习过 IRIS 类 Agentic RAG 项目，已经具备以下基础：

```text
LangGraph 状态机思想
AgentState 共享状态设计
Planner / Researcher / Writer / Reviewer 多节点结构
RAG 文档解析与向量检索
ChromaDB 本地向量库
CrossEncoder rerank
Reviewer 自审循环
FastAPI 后端组织
SSE / trace 展示思想
```

这些经验可以迁移到 DocResearch-Agent，但项目目标会重新定义为技术文档 QA，而不是报告生成。

### 4.2 TruckDrivers Agent 项目经验

已有 TruckDrivers-Agent 项目经验，具备：

```text
Agent 决策流程设计
状态管理
候选动作生成
规则约束和安全门
失败分析
日志分析
phase-based 迭代
```

这部分经验可迁移到 DocResearch-Agent：

| TruckDrivers 经验 | DocResearch-Agent 对应能力 |
|---|---|
| Safety Gate | Answer Judge / Citation Guard |
| Candidate Layer | Retrieval Candidate Selection |
| LLM Advisor | Answer Generator / Query Planner |
| Evaluation / Simulation | RAG Eval Runner |
| Failure Analysis | Failure Attribution |
| Phase-based 重构 | 分阶段开发计划 |

### 4.3 技术博客学习机制

项目开发中会持续参考 Claude、阿里云、华为云、LangChain 等技术博客中关于 Agent / RAG / Eval / LLMOps 的实践。

注意：第一阶段不是做博客爬虫，而是把博客作为技术吸收来源。

流程：

```text
阅读技术博客
    ↓
提炼可落地技术点
    ↓
写入 docs/tech_notes
    ↓
转化为项目 issue
    ↓
实现功能或实验
    ↓
写入 eval_report / README
```

---

## 5. 总体技术路线

### 5.1 系统总流程

```text
Document Upload / Load
        ↓
Document Parser
        ↓
Chunking + Metadata
        ↓
Dense Index + BM25 Index
        ↓
Hybrid Retriever
        ↓
Reranker
        ↓
Evidence Selector
        ↓
Answer Generator
        ↓
Answer Judge
        ├── PASS → Final Answer
        └── FAIL → Repair Router
                        ↓
                 Retry / Regenerate
                        ↓
                 Final Answer
        ↓
Trace Store + Eval Report
```

---

## 6. 核心模块设计

### 6.1 Document Loader

支持文档类型：

```text
MVP：Markdown / TXT / PDF
增强：DOCX / GitHub README / 技术博客文章
```

输出统一结构：

```json
{
  "doc_id": "doc_001",
  "source": "docs/langgraph_notes.md",
  "section": "Agent Workflow",
  "page": null,
  "text": "..."
}
```

---

### 6.2 Chunker

将文档切成 chunk，并保留 metadata：

```json
{
  "chunk_id": "chunk_001",
  "doc_id": "doc_001",
  "source": "docs/langgraph_notes.md",
  "section": "Agent Workflow",
  "page": null,
  "text": "LangGraph uses graph-based workflows..."
}
```

建议初始参数：

```text
chunk_size = 500~800 characters
chunk_overlap = 50~100 characters
```

---

### 6.3 Dense Retriever

使用 embedding + Chroma 检索语义相关片段。

适合：

```text
概念解释
方法总结
语义相近问题
```

---

### 6.4 BM25 Retriever

使用关键词检索。

适合：

```text
函数名
类名
参数名
模块名
错误码
专有术语
```

技术文档中 BM25 很重要，因为很多问题依赖精确词匹配。

---

### 6.5 Hybrid Retriever

融合 Dense 和 BM25：

```text
dense_results = vector_search(query, top_k=20)
bm25_results = bm25_search(query, top_k=20)
merged = merge_and_deduplicate(dense_results, bm25_results)
reranked = rerank(query, merged)
return top_k
```

第一版可以用简单合并策略：

```text
去重后按来源分数排序
```

第二版再做加权融合：

```text
final_score = alpha * dense_score + beta * bm25_score + gamma * rerank_score
```

---

### 6.6 Reranker

借鉴 IRIS 的 CrossEncoder rerank 经验：

```text
先召回 fetch_k 个候选
再用 CrossEncoder 对 query-doc pair 打分
最后取 top_k
```

MVP 中如果时间不够，可以先实现接口，第二周补完整 rerank。

---

### 6.7 Evidence Selector

从 top-k chunk 中选择真正能支持答案的证据。

输出示例：

```json
{
  "selected_evidence": [
    {
      "chunk_id": "chunk_012",
      "reason": "该片段直接解释了 reranker 的作用"
    }
  ]
}
```

第一版可以由 LLM 判断；时间紧时也可以先使用 top-3 作为 evidence。

---

### 6.8 Answer Generator

基于 selected evidence 生成答案。

规则：

```text
必须基于证据回答
每个关键结论尽量带引用
证据不足时明确说明
不允许编造文档中没有的信息
```

Prompt 要求：

```text
你只能使用提供的 evidence 回答问题。
如果 evidence 不足，请说明无法确定。
答案中需要引用 chunk_id。
```

---

### 6.9 Answer Judge

Judge 输出结构化 JSON：

```json
{
  "pass": true,
  "answer_relevance": 0.9,
  "faithfulness": 0.85,
  "citation_support": 0.8,
  "failure_type": null,
  "reason": "答案基本被证据支持",
  "repair_action": null
}
```

判断维度：

```text
answer_relevance
faithfulness
citation_support
completeness
hallucination_risk
```

---

### 6.10 Repair Router

根据 Judge 的失败类型路由到不同修复动作。

MVP 支持：

```text
citation_error → regenerate_with_evidence_only
weak_evidence → increase_top_k
incomplete_answer → rewrite_query
```

增强版支持：

```text
retrieval_miss
hallucination
off_topic
```

限制：

```text
max_repair_count = 1 或 2
```

防止无限循环和 token 成本过高。

---

### 6.11 Trace Logger

记录每个节点输入输出：

```json
{
  "node": "answer_judge",
  "input_summary": "answer + 3 citations",
  "output": {
    "pass": false,
    "failure_type": "citation_error"
  },
  "latency_ms": 1230
}
```

用于：

```text
debug
前端展示
eval report
面试讲解
```

---

### 6.12 Eval Runner

评测数据格式：

```json
{
  "question": "What is the role of the reranker?",
  "reference_answer": "The reranker reorders initially retrieved chunks based on query-document relevance.",
  "reference_keywords": ["rerank", "reorder", "retrieved chunks"],
  "reference_doc": "rag_engine.md",
  "question_type": "concept"
}
```

评测策略：

```text
baseline_vector
hybrid
hybrid_with_judge
agentic_repair
```

输出报告：

```text
reports/eval_report.md
```

---

## 7. 推荐技术栈

### 7.1 MVP 技术栈

| 模块 | 技术 |
|---|---|
| 语言 | Python 3.10+ |
| Agent 工作流 | LangGraph |
| 后端 | FastAPI 或命令行入口 |
| 文档解析 | pathlib / markdown / PyPDFLoader |
| 文本切分 | RecursiveCharacterTextSplitter 或自定义 chunker |
| 向量库 | ChromaDB |
| Embedding | sentence-transformers / DashScope / OpenAI embedding |
| BM25 | rank-bm25 |
| Rerank | sentence-transformers CrossEncoder |
| LLM | OpenAI / DeepSeek / Qwen API |
| 配置 | pydantic / dotenv |
| 评测 | 自定义 eval runner，后续可接 DeepEval / Ragas |
| 展示 | 第一版终端 / FastAPI Swagger；第二版 Streamlit |

### 7.2 不建议 MVP 引入

```text
复杂 Vue 前端
多用户权限
数据库多租户
异步任务队列
自动爬虫
完整 LLMOps 平台
```

---

## 8. 项目目录设计

一周 MVP 建议简单一些：

```text
DocResearch-Agent/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── state.py
│   ├── graph.py
│   ├── loaders.py
│   ├── chunker.py
│   ├── retriever.py
│   ├── generator.py
│   ├── judge.py
│   ├── repair.py
│   └── trace.py
│
├── eval/
│   ├── eval_dataset.jsonl
│   ├── eval_runner.py
│   └── metrics.py
│
├── data/
│   ├── raw_docs/
│   └── index/
│
├── docs/
│   ├── iris_learning_notes.md
│   ├── docresearch_mapping.md
│   ├── design_decisions.md
│   └── tech_notes/
│
├── reports/
│   └── eval_report.md
│
├── README.md
├── requirements.txt
└── .env.example
```

如果第二周继续做，再拆分为：

```text
app/rag/
app/graph/
app/api/
app/evaluation/
app/storage/
```

---

## 9. 一周实施计划

### Day 1：IRIS 学习与迁移设计

任务：

```text
阅读 IRIS README
阅读 graph.py / state.py / rag/engine.py
写 iris_learning_notes.md
写 docresearch_mapping.md
确定 MVP 范围
```

产出：

```text
docs/iris_learning_notes.md
docs/docresearch_mapping.md
README 初版
```

---

### Day 2：项目骨架与基础文档加载

任务：

```text
新建 DocResearch-Agent 仓库
建立 app/ docs/ eval/ data/ reports/ 目录
实现 Markdown / TXT loader
实现简单 chunker
准备 3~5 个测试文档
```

产出：

```text
load_docs()
split_chunks()
metadata structure
```

---

### Day 3：基础 RAG 闭环

任务：

```text
接入 embedding
建立 Chroma index
实现 vector retrieval
实现 answer generation
返回 citation chunk
```

产出：

```text
用户问题 → 检索 → 回答 + 引用
```

---

### Day 4：Hybrid Retrieval

任务：

```text
实现 BM25 index
实现 vector + BM25 merge
实现去重
输出 retrieval trace
```

产出：

```text
HybridRetriever
retrieval_type 标记
baseline vs hybrid 简单对比
```

---

### Day 5：LangGraph Agent Workflow

任务：

```text
定义 AgentState
实现 Query Planner
实现 Retriever Node
实现 Generator Node
实现 Judge Node 框架
连成 LangGraph
```

产出：

```text
planner → retriever → generator → judge → END
```

---

### Day 6：Answer Judge + Self-Repair

任务：

```text
Judge 输出结构化 JSON
实现 failure_type
实现 Repair Router
支持最多一次 repair
记录修复前后 trace
```

产出：

```text
planner → retriever → generator → judge → repair → generator → END
```

---

### Day 7：Eval Report + README 包装

任务：

```text
构建 20 条 QA 评测集
实现 eval_runner
对比 baseline / hybrid / agentic repair
输出 eval_report.md
完善 README
写简历 bullet
```

产出：

```text
reports/eval_report.md
README.md
项目 demo
简历描述
```

---

## 10. 两周增强计划

如果有第二周，建议做：

### 10.1 Reranker 完整化

```text
接入 CrossEncoder rerank
对比 hybrid vs hybrid + rerank
记录 latency trade-off
```

### 10.2 Evidence Selector 独立节点

```text
从 retrieved_chunks 中选择 selected_evidence
输出选择理由
提高 citation support
```

### 10.3 Streamlit 展示

页面包含：

```text
文档上传
问题输入
答案展示
引用展示
trace 展示
Judge 分数
Repair 动作
```

### 10.4 技术博客吸收文档

新增：

```text
docs/tech_notes/
```

记录：

```text
Claude / 阿里云 / 华为云 / LangChain 博客中的 Agent / RAG 技术点
如何转化为项目 issue
是否实现
实验效果
```

### 10.5 评测集扩展

```text
20 条 → 50 条
增加 question_type
增加 failure case 分析
```

---

## 11. 核心实验设计

### 实验 1：Vector vs Hybrid

目标：验证 BM25 是否提升技术术语检索。

对比：

```text
vector only
BM25 only
hybrid
```

指标：

```text
retrieval_hit_rate
answer_keyword_coverage
latency
```

---

### 实验 2：Hybrid vs Hybrid + Rerank

目标：验证 rerank 是否提升证据排序质量。

指标：

```text
top1_relevance
top3_relevance
citation_accuracy
latency
```

---

### 实验 3：No Judge vs Judge

目标：验证 Answer Judge 是否能识别低质量答案。

指标：

```text
judge_detection_rate
false_positive_cases
false_negative_cases
```

---

### 实验 4：No Repair vs Self-Repair

目标：验证 repair 是否提升最终答案质量。

指标：

```text
repair_success_rate
final_judge_pass_rate
extra_latency
extra_token_cost
```

---

## 12. README 展示重点

最终 README 应包含：

```text
1. 项目简介
2. 为什么普通 RAG 不够
3. 系统架构图
4. Agent 工作流
5. 核心模块
6. 安装运行方式
7. 示例输入输出
8. Trace 示例
9. 评测结果
10. 从 IRIS 学到的工程经验如何转化为本项目设计
11. 后续计划
```

```text
本项目在学习早期 Agentic RAG 工程结构的基础上，重新面向技术文档 QA 场景设计，重点实现 Hybrid Retrieval、Answer Judge、Self-Repair 和 Evaluation Report。
```

---

## 15. MVP 验收标准


```text
[ ] 能加载 Markdown / TXT / PDF 中至少两类文档
[ ] 能切 chunk 并保存 metadata
[ ] 能建立向量索引
[ ] 能执行 BM25 检索
[ ] 能执行 hybrid retrieval
[ ] 能生成带引用答案
[ ] 能通过 LangGraph 串起 planner / retriever / generator / judge
[ ] Judge 能输出 pass / failure_type / repair_action
[ ] 至少支持一次 repair
[ ] 能输出 trace
[ ] 有 20 条 QA 评测集
[ ] 有 eval_report.md
[ ] README 能清楚说明项目亮点
```

两周增强标准：

```text
[ ] 接入 CrossEncoder reranker
[ ] Evidence Selector 独立成节点
[ ] Streamlit demo 可用
[ ] 评测集扩展到 50 条
[ ] README 有架构图和实验表格
[ ] docs/tech_notes 有至少 3 篇技术博客学习记录
```

---

## 16. 风险与取舍

### 风险 1：时间太紧，模块太多

解决：

```text
先实现最小闭环，后续增强 rerank / dashboard。
```

### 风险 2：Judge 不稳定

解决：

```text
第一版用规则 + LLM 混合判断；
不要追求完美评分，只要能输出结构化失败类型。
```

### 风险 3：前端拖慢进度

解决：

```text
先用命令行 / FastAPI Swagger；
最后再用 Streamlit 做展示。
```

### 风险 4：项目像普通 RAG

解决：

```text
必须保留三大亮点：
Hybrid Retrieval
Answer Judge
Self-Repair + Eval Report
```

---

## 17. 最终总结

DocResearch-Agent 的最终价值在于：

```text
它不是一个普通文档问答 demo，
而是一个带有 Agent 工作流、证据选择、答案审查、失败归因、自动修复和评测报告的 RAG 工程项目。
```

项目最核心的三个亮点是：

```text
1. Hybrid Retrieval：提高技术文档检索稳定性；
2. Answer Judge：判断答案是否可信；
3. Self-Repair + Eval：让系统能发现问题、修复问题，并用评测证明改进。
```

