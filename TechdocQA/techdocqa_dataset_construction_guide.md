# TechDocQA 自建技术文档评测集构建指南

> 适用项目：DocResearch-Agent 2026  
> 目标：构建 30～50 条真实技术文档 QA，用于评估技术文档场景下的 Context Planner、Hybrid + Graph Retriever、Evidence Composer、Self-Reflection Judge、Corrective Repair Router 和 Trace/Eval Runner。

---

## 0. 为什么要自建 TechDocQA

公开数据集如 MultiHop-RAG、StratRAG、HotpotQA 可以测试通用多跳检索能力，但它们通常不是 Agent / RAG / LLMOps 技术文档场景。

DocResearch-Agent 的目标是面向真实技术文档，所以必须额外构建一个小型但高质量的领域评测集：

```text
TechDocQA = 真实技术文档 + 人工/半自动问题 + 标准答案 + gold evidence
```

TechDocQA 主要用于回答这些问题：

```text
1. 系统能不能读懂真实技术文档？
2. Hybrid + Graph Retrieval 能不能找到正确技术证据？
3. Evidence Composer 会不会把关键证据丢掉？
4. Grounded Answer Generator 是否基于证据回答？
5. Self-Reflection Judge / Citation Guardrails 是否能发现引用不准、证据不足、幻觉等问题？
6. Corrective Repair Router 是否能让失败答案变好？
```

注意：TechDocQA 不追求规模大，追求**高质量、可追踪、可评测**。

---

## 1. 最终产物

完成后应产出：

```text
data/raw/techdocqa/                         # 原始技术文档
data/processed/techdocqa/corpus_docs.jsonl  # 统一文档格式
data/processed/techdocqa/chunks.jsonl       # chunk 结果
data/processed/techdocqa/eval_dataset_v1.jsonl
data/processed/techdocqa/eval_dataset_sample_50.jsonl
reports/techdocqa/dataset_report.md
```

核心文件是：

```text
data/processed/techdocqa/eval_dataset_v1.jsonl
```

每行格式示例：

```json
{
  "id": "techdocqa_0001",
  "source_dataset": "TechDocQA",
  "question": "LangGraph 中 StateGraph 的作用是什么？",
  "question_type": "concept",
  "expected_answer": "StateGraph 用于定义有状态的图工作流，节点读取和更新共享状态，边决定节点之间的执行顺序，条件边可以根据状态动态路由。",
  "expected_keywords": ["StateGraph", "状态", "节点", "边", "条件路由"],
  "gold_doc_ids": ["langgraph_docs_001"],
  "gold_chunk_ids": ["langgraph_docs_001-s02-c003"],
  "gold_sources": ["data/raw/techdocqa/langgraph/stategraph.md"],
  "difficulty": "easy",
  "metadata": {
    "topic": "langgraph",
    "evidence_reason": "该 chunk 明确定义了 StateGraph 的用途和节点/边关系"
  }
}
```

---

## 2. 数据来源选择

不要使用项目设计文档作为主数据集。TechDocQA 应尽量使用真实、公开、官方或高质量开源技术资料。

推荐选择 8～12 个资料源，每个资料源抽取 1～5 篇核心文档。

### 2.1 推荐资料源

| 类别 | 推荐资料 | 用途 |
|---|---|---|
| Agent Workflow | LangGraph 官方文档 / examples | StateGraph、节点、条件边、agent workflow |
| Agent SDK | OpenAI Agents SDK 文档 | tool calling、handoff、guardrails、trace、eval |
| Context Engineering | Anthropic context engineering / multi-agent engineering blogs | context planner、上下文预算、动态上下文组织 |
| Tool Protocol | MCP specification | tool schema、server tools、资源暴露、标准化工具调用 |
| RAG 工程 | RAGFlow README / docs | document parsing、hybrid search、rerank、RAG product design |
| Graph Retrieval | LightRAG repo / paper / docs | graph-enhanced retrieval、incremental graph、dual-level retrieval |
| RAG Eval | Ragas docs | faithfulness、answer relevancy、context precision / recall |
| RAG Eval | DeepEval docs | LLM-as-a-judge、faithfulness、answer relevancy |
| 实际参考项目 | IRIS README / backend notes | Agentic workflow、review loop、RAG + reviewer 结构 |

### 2.2 建议第一版使用的 8 个文档主题

第一版不要太多，建议选这些：

```text
1. LangGraph: StateGraph / conditional edges / agentic RAG
2. OpenAI Agents SDK: tools / guardrails / traces / evals
3. MCP: server tools specification
4. Anthropic: effective context engineering for agents
5. RAGFlow: document understanding + hybrid search + rerank
6. LightRAG: graph-enhanced retrieval 思路
7. Ragas: RAG metrics
8. DeepEval: faithfulness / answer relevancy / contextual metrics
```

---

## 3. 推荐目录结构

在项目中创建：

```text
docresearch-agent/
├── data/
│   ├── raw/
│   │   └── techdocqa/
│   │       ├── langgraph/
│   │       ├── openai_agents/
│   │       ├── mcp/
│   │       ├── anthropic_context/
│   │       ├── ragflow/
│   │       ├── lightrag/
│   │       ├── ragas/
│   │       └── deepeval/
│   │
│   └── processed/
│       └── techdocqa/
│           ├── corpus_docs.jsonl
│           ├── chunks.jsonl
│           ├── eval_dataset_v1.jsonl
│           ├── eval_dataset_sample_50.jsonl
│           └── qa_draft_for_review.jsonl
│
├── scripts/
│   ├── collect_tech_docs.py
│   ├── inspect_tech_docs.py
│   ├── build_techdocqa_corpus.py
│   ├── chunk_techdocqa_docs.py
│   ├── generate_techdocqa_qa_draft.py
│   ├── review_techdocqa_dataset.py
│   └── sample_techdocqa.py
│
└── reports/
    └── techdocqa/
        └── dataset_report.md
```

---

## 4. Step 1：收集真实技术文档

### 4.1 收集方式

可以用三种方式：

```text
A. 手动下载 Markdown / HTML / README
B. git clone 官方开源 repo 后提取 docs / README
C. 使用 URL 列表 + trafilatura/readability 抽取正文
```

第一版建议优先使用：

```text
手动保存 + git clone
```

不要一开始做复杂爬虫。稳定性更重要。

### 4.2 文档保存规范

每篇文档保存为 `.md` 或 `.txt`，文件开头加 metadata：

```markdown
---
title: LangGraph StateGraph Documentation
source_url: https://...
source_type: official_docs
topic: langgraph
collected_at: 2026-05-18
---

正文内容...
```

如果是 HTML 抽取，也先转成 Markdown 或纯文本。

### 4.3 原始文档示例目录

```text
data/raw/techdocqa/langgraph/stategraph.md
data/raw/techdocqa/langgraph/agentic_rag.md
data/raw/techdocqa/openai_agents/tools.md
data/raw/techdocqa/openai_agents/guardrails.md
data/raw/techdocqa/openai_agents/traces_evals.md
data/raw/techdocqa/mcp/tools_spec.md
data/raw/techdocqa/anthropic_context/context_engineering.md
data/raw/techdocqa/ragflow/readme.md
data/raw/techdocqa/lightrag/readme_or_paper_notes.md
data/raw/techdocqa/ragas/metrics.md
data/raw/techdocqa/deepeval/rag_metrics.md
```

---

## 5. Step 2：转换为统一 corpus_docs.jsonl

实现脚本：

```text
scripts/build_techdocqa_corpus.py
```

目标输出：

```text
data/processed/techdocqa/corpus_docs.jsonl
```

每篇文档一行：

```json
{
  "doc_id": "langgraph_001",
  "source_dataset": "TechDocQA",
  "title": "LangGraph StateGraph Documentation",
  "source_path": "data/raw/techdocqa/langgraph/stategraph.md",
  "source_url": "https://...",
  "topic": "langgraph",
  "text": "...",
  "metadata": {
    "source_type": "official_docs",
    "collected_at": "2026-05-18"
  }
}
```

### 5.1 doc_id 命名规则

推荐格式：

```text
{topic}_{index:03d}
```

示例：

```text
langgraph_001
openai_agents_001
mcp_001
ragas_001
```

---

## 6. Step 3：Structure-aware Chunking

实现脚本：

```text
scripts/chunk_techdocqa_docs.py
```

目标输出：

```text
data/processed/techdocqa/chunks.jsonl
```

每个 chunk 格式：

```json
{
  "chunk_id": "langgraph_001-s02-c003",
  "doc_id": "langgraph_001",
  "source_dataset": "TechDocQA",
  "title": "LangGraph StateGraph Documentation",
  "section": "StateGraph",
  "section_path": ["LangGraph", "StateGraph"],
  "element_type": "text",
  "text": "...",
  "contextual_header": "This chunk comes from LangGraph documentation, section StateGraph. It explains how StateGraph defines stateful workflows.",
  "index_text": "This chunk comes from...\nOriginal chunk: ...",
  "metadata": {
    "source_path": "data/raw/techdocqa/langgraph/stategraph.md",
    "source_url": "https://...",
    "chunk_index": 3,
    "token_count": 320
  }
}
```

### 6.1 为什么要 structure-aware chunking

普通 chunking 只按长度切文本，会丢失技术文档结构：

```text
标题
章节路径
代码块
表格
术语定义
API 参数说明
```

DocResearch-Agent 要体现 Context Engineering，所以 chunk 阶段要保留：

```text
section
section_path
element_type
source_url
contextual_header
```

### 6.2 element_type 建议

第一版支持：

```text
text
code_block
table
heading
list
```

如果实现成本高，至少支持：

```text
text
code_block
```

### 6.3 chunk_id 命名规则

```text
{doc_id}-s{section_index:02d}-c{chunk_index:03d}
```

示例：

```text
langgraph_001-s02-c003
```

这个 ID 后面要写入 eval dataset 的 `gold_chunk_ids`。

---

## 7. Step 4：设计问题类型分布

TechDocQA 建议构建 30～50 条。

推荐分布：

| question_type | 数量 | 用途 |
|---|---:|---|
| fact | 8 | 测基础检索 |
| concept | 10 | 测概念理解 |
| comparison | 6 | 测证据组织和对比 |
| multi_hop | 8 | 测 graph retrieval / 多模块关联 |
| implementation | 8 | 测代码/实现细节检索 |
| troubleshooting | 5 | 测 repair / failure reasoning |

总数可调整到 40～50 条。

---

## 8. Step 5：人工 + LLM 半自动生成 QA 草稿

不要全部让 LLM 自动生成，也不要全部手写。

推荐流程：

```text
1. 从 chunks.jsonl 中挑选高质量 chunk
2. 每个 chunk 让 LLM 生成 1～2 个 QA 草稿
3. 人工检查问题是否真实、有价值、不太简单
4. 人工确认 expected_answer 和 gold_chunk_ids
5. 保存为 eval_dataset_v1.jsonl
```

### 8.1 生成 QA 草稿脚本

实现：

```text
scripts/generate_techdocqa_qa_draft.py
```

输入：

```text
data/processed/techdocqa/chunks.jsonl
```

输出：

```text
data/processed/techdocqa/qa_draft_for_review.jsonl
```

每行：

```json
{
  "draft_id": "draft_0001",
  "source_chunk_id": "langgraph_001-s02-c003",
  "source_doc_id": "langgraph_001",
  "question": "StateGraph 在 LangGraph 中的作用是什么？",
  "question_type": "concept",
  "expected_answer": "...",
  "expected_keywords": ["StateGraph", "状态", "节点", "边"],
  "suggested_gold_chunk_ids": ["langgraph_001-s02-c003"],
  "review_status": "pending"
}
```

### 8.2 QA 生成 Prompt 模板

可以使用如下 prompt：

```text
你正在帮助构建一个技术文档 RAG 评测集。请基于下面的技术文档片段生成高质量 QA。

要求：
1. 问题必须能被该片段直接或主要支持。
2. 问题不要太简单，不要只是问“本文说了什么”。
3. 输出 2 个问题：一个 concept 类型，一个 implementation 或 troubleshooting 类型。
4. 每个问题给出标准答案、关键词、需要引用的证据 chunk_id。
5. 不要引入片段外的信息。

文档信息：
- doc_id: {doc_id}
- chunk_id: {chunk_id}
- title: {title}
- section: {section}

片段内容：
{chunk_text}

输出 JSON 数组：
[
  {
    "question": "...",
    "question_type": "concept|implementation|troubleshooting|fact|comparison|multi_hop",
    "expected_answer": "...",
    "expected_keywords": ["..."],
    "gold_chunk_ids": ["{chunk_id}"],
    "difficulty": "easy|medium|hard"
  }
]
```

---

## 9. Step 6：人工审核 QA 草稿

必须人工审核，否则数据集容易质量差。

审核重点：

```text
1. 问题是否真的来自真实技术文档？
2. 标准答案是否被 gold chunk 支持？
3. 问题是否过于简单？
4. 是否存在无依据推断？
5. gold_chunk_ids 是否准确？
6. question_type 是否正确？
7. expected_keywords 是否能用于简单评分？
```

### 9.1 保留标准

保留的问题应该满足：

```text
问题明确
答案可由文档证据支持
gold evidence 可追踪
难度有区分
能测试系统某个模块
```

### 9.2 删除标准

删除这些问题：

```text
答案需要外部知识才能完成
问题太宽泛
问题只是在复述标题
gold evidence 不明确
expected_answer 过长且难评分
LLM 编造了文档没有的信息
```

---

## 10. Step 7：构建正式 eval_dataset_v1.jsonl

最终格式：

```json
{
  "id": "techdocqa_0001",
  "source_dataset": "TechDocQA",
  "question": "为什么 Evidence Composer 比简单 Evidence Selector 更适合 Context Engineering？",
  "question_type": "concept",
  "expected_answer": "Evidence Composer 不只是选择相关 chunk，还会去重、压缩、按章节组织证据、保留 citation id，并控制上下文预算，因此更符合 Context Engineering 中对上下文质量和结构的要求。",
  "expected_keywords": ["去重", "压缩", "章节组织", "citation id", "上下文预算"],
  "gold_doc_ids": ["docresearch_reference_006"],
  "gold_chunk_ids": ["docresearch_reference_006-s03-c002"],
  "gold_sources": ["data/raw/techdocqa/ragas/metrics.md"],
  "difficulty": "medium",
  "metadata": {
    "topic": "context_engineering",
    "created_by": "llm_draft_human_reviewed",
    "reviewer_note": "答案必须提到 Evidence Composer 的组织和压缩功能"
  }
}
```

### 10.1 字段要求

| 字段 | 是否必填 | 说明 |
|---|---|---|
| id | 必填 | 唯一问题 ID |
| source_dataset | 必填 | 固定 TechDocQA |
| question | 必填 | 用户问题 |
| question_type | 必填 | fact/concept/comparison/multi_hop/implementation/troubleshooting |
| expected_answer | 必填 | 标准答案 |
| expected_keywords | 强烈建议 | 用于自动粗评分 |
| gold_doc_ids | 必填 | 标准文档 |
| gold_chunk_ids | 必填 | 标准证据 chunk |
| gold_sources | 建议 | 原始文件路径/URL |
| difficulty | 必填 | easy/medium/hard |
| metadata | 可选 | topic、review note 等 |

---

## 11. Step 8：质量检查脚本

实现：

```text
scripts/review_techdocqa_dataset.py
```

检查内容：

```text
1. 总问题数
2. question_type 分布
3. difficulty 分布
4. expected_answer 非空率
5. expected_keywords 非空率
6. gold_doc_ids 非空率
7. gold_chunk_ids 非空率
8. gold_chunk_ids 是否存在于 chunks.jsonl
9. 每个问题对应的 gold chunk 文本预览
10. 是否有重复问题
```

验收标准：

```text
问题数量：30～50
expected_answer 非空率：100%
gold_chunk_ids 非空率：100%
gold_chunk_ids 存在率：100%
重复问题：0
question_type 至少覆盖 5 类
multi_hop 至少 5 条
troubleshooting 至少 3 条
```

---

## 12. Step 9：抽样文件

实现：

```text
scripts/sample_techdocqa.py
```

输出：

```text
data/processed/techdocqa/eval_dataset_sample_30.jsonl
data/processed/techdocqa/eval_dataset_sample_50.jsonl
```

第一版如果总数只有 40 条，可以 sample_30 用于快速调试，全量 v1 用于正式报告。

---

## 13. Step 10：接入 Eval Runner

### 13.1 配置文件

新增：

```text
eval/configs/techdocqa_baseline_vector.yaml
eval/configs/techdocqa_hybrid.yaml
eval/configs/techdocqa_hybrid_graph.yaml
eval/configs/techdocqa_agentic_graph_repair.yaml
```

示例：

```yaml
name: techdocqa_agentic_graph_repair
dataset: techdocqa
corpus_path: data/processed/techdocqa/chunks.jsonl
index_dir: data/indexes/techdocqa
retriever:
  use_dense: true
  use_bm25: true
  use_graph: true
  top_k: 10
pipeline:
  use_context_planner: true
  use_retrieval_evaluator: true
  use_evidence_composer: true
  use_grounded_generator: true
  use_self_reflection_judge: true
  use_citation_guardrails: true
  use_repair: true
mode: full_qa
```

### 13.2 运行命令

```bash
python eval/run_eval.py \
  --dataset data/processed/techdocqa/eval_dataset_sample_50.jsonl \
  --config eval/configs/techdocqa_agentic_graph_repair.yaml \
  --output reports/techdocqa/agentic_graph_repair_results.jsonl
```

对比配置：

```bash
python eval/run_eval.py --dataset data/processed/techdocqa/eval_dataset_sample_50.jsonl --config eval/configs/techdocqa_baseline_vector.yaml --output reports/techdocqa/baseline_vector_results.jsonl
python eval/run_eval.py --dataset data/processed/techdocqa/eval_dataset_sample_50.jsonl --config eval/configs/techdocqa_hybrid.yaml --output reports/techdocqa/hybrid_results.jsonl
python eval/run_eval.py --dataset data/processed/techdocqa/eval_dataset_sample_50.jsonl --config eval/configs/techdocqa_hybrid_graph.yaml --output reports/techdocqa/hybrid_graph_results.jsonl
python eval/run_eval.py --dataset data/processed/techdocqa/eval_dataset_sample_50.jsonl --config eval/configs/techdocqa_agentic_graph_repair.yaml --output reports/techdocqa/agentic_graph_repair_results.jsonl
```

---

## 14. TechDocQA 评测指标

TechDocQA 应该同时评估 retrieval、evidence、answer、judge、repair。

### 14.1 Retrieval 指标

```text
retrieval_hit_rate@k
selected_evidence_hit_rate
gold_doc_recall@k
gold_chunk_recall@k
```

### 14.2 Answer 指标

```text
keyword_coverage
answer_relevance
faithfulness
citation_support
```

### 14.3 Agent 指标

```text
judge_pass_rate
repair_trigger_rate
repair_success_rate
avg_repair_count
failure_type_distribution
```

### 14.4 成本指标

```text
avg_latency_ms
avg_context_tokens
avg_model_calls
```

---

## 15. 报告文件 dataset_report.md

实现：

```text
reports/techdocqa/dataset_report.md
```

建议结构：

```markdown
# TechDocQA Dataset Report

## 1. Dataset Purpose
说明为什么要自建 TechDocQA。

## 2. Document Sources
列出文档来源、主题、类型、URL/路径。

## 3. Dataset Schema
解释 eval_dataset_v1.jsonl 每个字段。

## 4. Question Distribution
| Type | Count |
|---|---:|
| fact | ... |
| concept | ... |
| multi_hop | ... |

## 5. Difficulty Distribution
| Difficulty | Count |

## 6. Gold Evidence Annotation
说明 gold_chunk_ids 怎么标注。

## 7. Quality Control
说明人工审核规则。

## 8. Example Samples
展示 3～5 条样本。

## 9. Limitations
说明数据集小、以 Agent/RAG 技术文档为主，不代表所有技术文档。
```

---

## 16. 推荐 Day8-Day9 执行计划

### Day8：构建数据集

```text
1. 收集 8～12 篇真实技术文档
2. 保存到 data/raw/techdocqa/
3. 转换 corpus_docs.jsonl
4. 运行 structure-aware chunking
5. 生成 qa_draft_for_review.jsonl
6. 人工审核并整理 30～50 条
7. 输出 eval_dataset_v1.jsonl
```

### Day9：接入评测

```text
1. 运行 review_techdocqa_dataset.py
2. 建立 techdocqa 索引
3. 配置 baseline / hybrid / hybrid_graph / agentic_graph_repair
4. 跑 eval runner
5. 输出 reports/techdocqa/eval_report.md
6. 总结哪些模块真的带来提升
```

---

## 17. Agent 执行任务说明

下面这段可以直接交给你的 agent。

### 任务目标

请为 DocResearch-Agent 构建一个名为 TechDocQA 的小型真实技术文档评测集。不要使用项目设计 md 作为主数据，必须基于真实公开技术文档或官方/开源项目文档构建。目标规模为 30～50 条 QA，每条问题必须包含标准答案、expected_keywords、gold_doc_ids、gold_chunk_ids。

### 执行步骤

1. 创建目录：

```text
data/raw/techdocqa/
data/processed/techdocqa/
data/indexes/techdocqa/
reports/techdocqa/
```

2. 收集 8～12 篇真实技术文档，优先选择：

```text
LangGraph docs
OpenAI Agents SDK docs
MCP tools spec
Anthropic context engineering blog
RAGFlow README/docs
LightRAG README/paper notes
Ragas metrics docs
DeepEval RAG metrics docs
```

3. 将每篇文档保存为 md/txt，并在文件头部记录 title、source_url、topic、source_type。

4. 实现 `scripts/build_techdocqa_corpus.py`，输出：

```text
data/processed/techdocqa/corpus_docs.jsonl
```

5. 实现 `scripts/chunk_techdocqa_docs.py`，进行 structure-aware chunking，输出：

```text
data/processed/techdocqa/chunks.jsonl
```

每个 chunk 必须包含：

```text
chunk_id
doc_id
title
section
section_path
element_type
text
contextual_header
index_text
source_url/source_path
```

6. 实现 `scripts/generate_techdocqa_qa_draft.py`，基于高质量 chunk 生成 QA 草稿：

```text
data/processed/techdocqa/qa_draft_for_review.jsonl
```

7. 人工审核 QA 草稿，保留 30～50 条高质量问题，覆盖：

```text
fact
concept
comparison
multi_hop
implementation
troubleshooting
```

8. 输出正式数据集：

```text
data/processed/techdocqa/eval_dataset_v1.jsonl
```

9. 实现 `scripts/review_techdocqa_dataset.py`，检查：

```text
总数
问题类型分布
难度分布
expected_answer 非空率
gold_chunk_ids 非空率
gold_chunk_ids 是否存在于 chunks.jsonl
重复问题
样本预览
```

10. 建立 techdocqa 的 vector / BM25 / graph index。

11. 接入 Eval Runner，至少支持这些配置：

```text
techdocqa_baseline_vector
techdocqa_hybrid
techdocqa_hybrid_graph
techdocqa_agentic_graph_repair
```

12. 输出报告：

```text
reports/techdocqa/dataset_report.md
reports/techdocqa/eval_report.md
```

### 验收标准

```text
1. eval_dataset_v1.jsonl 至少 30 条，最好 40～50 条；
2. 每条必须有 question、expected_answer、gold_chunk_ids；
3. gold_chunk_ids 必须能在 chunks.jsonl 找到；
4. question_type 至少覆盖 5 类；
5. multi_hop 至少 5 条；
6. troubleshooting 至少 3 条；
7. reports/techdocqa/dataset_report.md 必须说明数据来源和标注方法；
8. reports/techdocqa/eval_report.md 必须能对比 baseline、hybrid、hybrid_graph、agentic_graph_repair。
```

---

## 18. 注意事项

1. 不要用项目设计 md 作为主数据集。
2. 不要全部自动生成 QA，必须人工审核。
3. 不要让 expected_answer 包含 gold chunk 之外的信息。
4. 不要只做 fact 问题，要包含 multi_hop、comparison、implementation、troubleshooting。
5. 不要只评估答案，要评估检索和证据选择。
6. 不要追求数量，30～50 条高质量样本比 500 条低质量自动样本更有价值。
7. 每个 gold_chunk_id 必须真实存在。
8. TechDocQA 是领域评测集，不是公开大 benchmark，应在报告中诚实说明规模和边界。

---

## 19. 最终 README 中可以这样描述

```text
为验证系统在真实技术文档场景下的表现，本项目自建 TechDocQA 小型评测集。
该数据集基于 LangGraph、OpenAI Agents SDK、MCP、RAGFlow、LightRAG、Ragas、DeepEval 等真实技术文档构建，包含 fact、concept、comparison、multi-hop、implementation 和 troubleshooting 六类问题。
每条样本均标注 expected answer、expected keywords 和 gold evidence chunks，用于评估 retrieval hit rate、selected evidence hit rate、citation support、faithfulness、repair success rate 等指标。
```

---

## 20. 最终建议

TechDocQA 的价值不在规模，而在它能真实验证 DocResearch-Agent 的目标场景。

建议最终采用三类评测：

```text
1. MultiHop-RAG：公开多跳检索 benchmark
2. StratRAG / GaRAGe：可选公开检索/grounding benchmark
3. TechDocQA：真实技术文档领域评测集
```

其中 TechDocQA 是最能体现项目定位的部分，必须认真构建。
