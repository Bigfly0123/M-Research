# DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统

## 0. 文档定位

这份文档是新版 `DocResearch-Agent` 的最终项目设计报告。它不再把项目定位为一个普通的 RAG 问答系统，也不再停留在从 IRIS 学习出来的 `Planner → Retriever → Writer → Reviewer` 结构，而是将项目升级为一个围绕 **上下文规划、图增强检索、证据组合、自动评测、可追踪修复** 的小型高级 Agentic RAG 工程系统。

新版项目的核心目标是：

> 构建一个面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统。系统不仅能回答技术文档问题，还能规划上下文、融合多种检索方式、构建轻量图增强索引、组合证据、检查引用可靠性、自动修复失败答案，并通过 trace 与 eval report 形成可复现的改进闭环。

因此，本项目不是：

```text
上传文档 → 向量检索 → LLM 回答
```

而是：

```text
问题理解
  ↓
Context Planner 上下文规划
  ↓
Tool Registry 调用检索工具
  ↓
Hybrid + Lightweight Graph Retrieval
  ↓
Retrieval Evaluator 检索质量评估
  ↓
Evidence Composer 证据组合与压缩
  ↓
Grounded Answer Generator 带引用生成
  ↓
Self-Reflection Judge + Citation Guardrails
  ↓
Guarded Repair Router 针对性修复
  ↓
Trace Store + Eval Runner 评测闭环
```

---

## 1. 为什么要重做这个项目定位

最初的 DocResearch-Agent 设计更像一个中高级 RAG 项目，核心功能包括文档解析、混合检索、Judge、自修复和评测。这个方向本身可行，但问题是：如果实现得比较简单，它很容易变成一个普通知识库问答 demo。

普通 RAG 项目的典型形态是：

```text
PDF / Markdown
  ↓
chunk
  ↓
embedding
  ↓
vector search
  ↓
LLM answer
```

这类项目现在已经非常常见，简历上容易显得一般。哪怕加入 BM25、rerank、简单 Judge，如果没有更清楚的系统设计目标，也容易变成“堆模块”。

新版 DocResearch-Agent 要解决的问题不是“能不能回答”，而是：

1. **上下文是否规划合理？**  
   不同问题是否应该使用不同检索策略、不同上下文预算、不同证据组织方式？

2. **检索是否真的找到了支撑答案的证据？**  
   不是 top-k 相似就一定有用，需要评估 evidence quality。

3. **技术文档中的概念关系是否被利用？**  
   仅靠向量相似度可能找不到多跳概念链，因此需要轻量图增强检索。

4. **给 LLM 的 context 是否经过组合、去重和压缩？**  
   不应该把所有 chunk 粗暴塞进 prompt，而应该构造 evidence pack。

5. **答案是否被引用真正支撑？**  
   需要 citation support、faithfulness、context sufficiency 等检查。

6. **失败后能否针对性修复？**  
   不应该只做 retry，而应该根据 failure type 路由到不同修复动作。

7. **整个过程是否可追踪、可评测、可复现？**  
   每次回答都应该记录 context plan、检索路径、证据组合、Judge 结果、repair action、latency、token cost。

新版项目的高级感来自这些系统能力，而不是来自“功能很多”。

---

## 2. 最终项目名称与定位

### 2.1 推荐项目名称

```text
DocResearch-Agent 2026
```

### 2.2 完整标题

```text
DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统
```

### 2.3 简历中可简化为

```text
DocResearch-Agent：技术文档 Agentic RAG 可靠性系统
```

### 2.4 一句话介绍

> 一个面向技术文档的 Context-Engineered Agentic GraphRAG 系统，围绕上下文规划、混合图增强检索、证据组合、引用校验、自动修复和 trace-based evaluation 构建可靠问答闭环。

### 2.5 项目关键词

```text
Context Engineering
Agentic RAG
Lightweight GraphRAG
Hybrid Retrieval
Evidence Composition
Self-Reflection Judge
Citation Guardrails
Guarded Repair
Trace-based Evaluation
Tool Registry
Skill-style Prompt Modules
```

---

## 3. 与 IRIS 的关系：学习经验，而不是复刻项目

IRIS 对本项目有参考价值，但新版 DocResearch-Agent 不应该被设计成 IRIS 的改名版。

IRIS 的核心价值在于：

1. 使用 LangGraph / StateGraph 组织多节点 Agent workflow；
2. 通过共享 state 在节点之间传递任务状态；
3. 具有 Planner、Researcher、Writer、Reviewer 等节点分工；
4. Reviewer 失败后可以回到 Planner，形成初步自我修正循环；
5. 有 RAG engine、FastAPI 后端和前端流式展示的工程结构。

但 IRIS 的主要目标偏向：

```text
自动调研 → 生成长报告 → Reviewer 审查 → Refiner 修改
```

新版 DocResearch-Agent 的目标是：

```text
技术文档问答 → 上下文规划 → 图增强检索 → 证据组合 → 引用校验 → 自动修复 → 可评测闭环
```

因此，两者的差异是根本性的：

| 维度 | IRIS 学习项目 | DocResearch-Agent 2026 |
|---|---|---|
| 核心目标 | 自动调研与报告生成 | 技术文档可靠问答与诊断 |
| 工作流重点 | Planner / Researcher / Writer / Reviewer | Context Planner / Graph Retriever / Evidence Composer / Judge / Repair |
| 输出形式 | 长报告 | 带引用答案、trace、eval report |
| RAG 重点 | 检索资料辅助写作 | 上下文工程、图增强检索、证据质量控制 |
| 自修复 | Reviewer fail 后回退 | failure-type based guarded repair |
| 评测 | 非核心 | 核心模块 |
| 高级点 | Agentic workflow | Context Engineering + GraphRAG Lite + Trace/Eval Loop |

所以本项目可以从 IRIS 学习工程组织经验，但最终要重构成一个新的高级 RAG 可靠性系统。

---

## 4. 新版总体架构

新版架构如下：

```text
User Question
   ↓
Context Planner
   - 判断问题类型
   - 规划检索策略
   - 设置 context budget
   - 判断是否需要代码块 / 表格 / 图增强 / 最近笔记
   - 标记风险级别
   ↓
Tool Registry
   ├── Dense Search Tool
   ├── BM25 Search Tool
   ├── Graph Expansion Tool
   ├── Citation Check Tool
   └── Eval Tool
   ↓
Hybrid + Lightweight Graph Retriever
   - dense retrieval
   - BM25 retrieval
   - term graph expansion
   - section-aware retrieval
   ↓
Retrieval Evaluator
   - strong evidence
   - weak evidence
   - irrelevant evidence
   - conflicting evidence
   ↓
Evidence Composer
   - 去重
   - 排序
   - 压缩
   - citation id 绑定
   - context budget 控制
   ↓
Grounded Answer Generator
   - 基于 evidence pack 生成答案
   - 每个关键结论必须带引用
   - 不允许无证据强答
   ↓
Self-Reflection Judge + Citation Guardrails
   - answer relevance
   - citation support
   - faithfulness
   - context sufficiency
   - guardrail pass / fail
   ↓
Guarded Repair Router
   - query rewrite
   - graph expand
   - evidence recompose
   - regenerate with evidence only
   - ask for insufficient evidence fallback
   ↓
Trace Store + Eval Runner
   - trace.jsonl
   - eval_dataset.jsonl
   - eval_report.md
```

这套架构的核心不是多加几个 Agent 节点，而是把 RAG 过程拆成可规划、可检查、可修复、可评测的工程闭环。

---

## 5. 核心设计思想：从 RAG 到 Context Engineering

### 5.1 普通 RAG 的问题

普通 RAG 常见问题包括：

1. chunk 被切开后失去上下文；
2. top-k 检索结果不一定能支持答案；
3. 检索结果重复、噪声大；
4. 多跳概念问题容易漏证据；
5. LLM 可能无证据发挥；
6. 引用看似存在，但并不支持结论；
7. 失败后无法判断是 retrieval 问题还是 generation 问题；
8. 没有 trace，无法调试和复现。

### 5.2 新版项目的核心转变

新版项目不把 RAG 当作一个简单模块，而把它看作 Agent 的上下文基础设施。

项目重点从：

```text
retrieve chunks
```

升级为：

```text
plan context → retrieve evidence → compose context → verify answer → repair failure → evaluate trace
```

也就是说，本项目关注的是 **Context Engineering**：

1. 该给模型什么上下文？
2. 不该给模型什么上下文？
3. 上下文来自哪些工具？
4. 上下文是否足够？
5. 上下文是否有噪声？
6. 上下文是否支撑最终答案？
7. 修复时应该改检索、改证据，还是改生成？

---

## 6. 核心模块设计

## 6.1 Context Planner

### 模块定位

Context Planner 是新版系统的第一个核心模块。它不是简单的 Query Planner，而是负责为每个问题制定上下文策略。

### 输入

```json
{
  "question": "为什么 Answer Judge 会影响 Repair Router 的行为？",
  "available_sources": ["local_docs", "tech_notes"],
  "history": []
}
```

### 输出

```json
{
  "query_type": "multi_hop_concept",
  "retrieval_plan": ["dense", "bm25", "graph_expand"],
  "context_budget": 3500,
  "need_code_blocks": false,
  "need_tables": false,
  "need_section_path": true,
  "risk_level": "citation_sensitive",
  "expected_evidence": [
    "definition of Answer Judge",
    "failure_type schema",
    "Repair Router action mapping"
  ]
}
```

### 支持的问题类型

```text
fact_lookup          事实查找
concept_explanation  概念解释
multi_hop_concept    多跳概念关系
comparison           多文档/多方法对比
code_understanding   代码理解
troubleshooting      问题诊断
summary              技术总结
```

### 高级感来源

普通 RAG 直接检索，Context Planner 先判断问题需要怎样的上下文。这体现的是 2026 之后 Agent 系统中的 context architecture 思想。

---

## 6.2 Structure-aware Document Ingestion

### 模块定位

文档解析不能只是按固定长度切文本。技术文档中有标题、代码块、表格、公式、列表、API 参数、配置项等结构。新版项目需要保留这些结构信息。

### 第一版支持

```text
Markdown heading
Markdown code block
Markdown table
PDF page text
DOCX paragraph 可选
```

### Chunk metadata

```json
{
  "chunk_id": "D1-C012",
  "doc_id": "langgraph_notes",
  "source": "docs/langgraph_notes.md",
  "section_path": "Agent Workflow / Conditional Edges",
  "element_type": "text",
  "page": null,
  "tokens": 312,
  "text": "..."
}
```

### 可选 Contextual Header

每个 chunk 可以附加轻量上下文头：

```text
[Document: LangGraph Notes]
[Section: Agent Workflow / Conditional Edges]
[Element: text]
[Chunk Summary: explains how conditional edges route state based on judge result]
```

这样可以减少 chunk 被切开后上下文丢失的问题。

---

## 6.3 Hybrid + Lightweight Graph Retriever

### 模块定位

检索层是项目高级感的第二个核心。新版检索不只做向量搜索，而是：

```text
Dense Retrieval + BM25 Retrieval + Lightweight Graph Expansion + optional Rerank
```

### 为什么需要多路检索

技术文档问题经常包含：

```text
函数名
类名
参数名
模块名
配置项
缩写
概念链
错误类型
```

向量检索适合语义相似，BM25 适合精确术语，图增强检索适合概念关联和多跳关系。

### 检索流程

```text
question
  ↓
Context Planner 给出 retrieval_plan
  ↓
Dense Search top-k
  ↓
BM25 Search top-k
  ↓
Term Extraction
  ↓
Graph Expansion 找相关术语和 chunk
  ↓
Merge + Deduplicate
  ↓
Score Fusion / Rerank
  ↓
Candidate Evidence
```

### Score fusion 示例

```text
final_score = 0.45 * dense_score
            + 0.30 * bm25_score
            + 0.20 * graph_score
            + 0.05 * metadata_score
```

### Lightweight Graph Index

不做复杂知识图谱，只做轻量级 term graph：

```text
term → chunks
chunk → terms
term → related_terms
section → chunks
```

示例：

```json
{
  "term": "Answer Judge",
  "related_terms": ["failure_type", "citation_support", "Repair Router"],
  "chunks": ["D1-C014", "D1-C019", "D2-C006"]
}
```

### Graph expansion 示例

如果问题是：

```text
为什么 Answer Judge 会影响 Repair Router？
```

系统先找到：

```text
Answer Judge
```

然后图扩展到：

```text
failure_type
repair_action
citation_error
weak_evidence
Repair Router
```

再召回这些术语对应的 chunks。

这就是轻量 GraphRAG / memory-style retrieval 的落地形式。

---

## 6.4 Tool Registry

### 模块定位

新版项目不应该把检索、图扩展、引用检查等能力硬编码到一个长函数里，而应该做一个轻量 Tool Registry。

这不是完整 MCP server，但借鉴 MCP-style tool abstraction 思想。

### Tool 示例

```json
{
  "name": "graph_expand",
  "description": "Expand related technical terms using lightweight term graph.",
  "input_schema": {
    "terms": "list[str]",
    "max_hops": "int"
  },
  "output_schema": {
    "expanded_terms": "list[str]",
    "related_chunks": "list[str]"
  }
}
```

### 第一版工具列表

```text
dense_search
bm25_search
graph_expand
citation_check
eval_run
```

### 价值

1. 降低 workflow 和工具实现耦合；
2. 方便后续替换检索策略；
3. README 和面试中更容易讲出工程设计；
4. 后续如果要接 MCP server，可以自然扩展。

---

## 6.5 Retrieval Evaluator

### 模块定位

检索结果不一定可靠。Retrieval Evaluator 在生成答案之前评估证据质量，避免“检索错了还继续生成”。

### 输入

```json
{
  "question": "...",
  "candidate_chunks": ["D1-C012", "D1-C014", "D2-C006"]
}
```

### 输出

```json
{
  "evidence_quality": "weak",
  "confidence": 0.62,
  "reason": "检索结果包含 Answer Judge 的定义，但缺少 Repair Router 的动作映射。",
  "recommended_action": "graph_expand",
  "missing_evidence": [
    "Repair Router action mapping",
    "failure_type to repair_action schema"
  ]
}
```

### evidence_quality 分类

```text
strong       证据足够，可以生成答案
weak         有部分证据，但不足以支持完整答案
irrelevant   检索结果与问题关系弱
conflicting  检索结果之间存在冲突
```

### 修复建议

```text
weak → graph_expand / increase_top_k
irrelevant → rewrite_query / fallback_bm25
conflicting → evidence_recompose / ask_uncertainty
```

---

## 6.6 Evidence Composer

### 模块定位

Evidence Composer 是新版架构中非常重要的 context engineering 模块。它不是简单选择 top-k，而是把候选 chunk 组织成一个高质量 evidence pack。

### 主要职责

```text
1. 去重
2. 删除弱相关 chunk
3. 按 source / section 组织证据
4. 给每个证据绑定 citation_id
5. 对长 chunk 做压缩
6. 控制 context budget
7. 标注每个证据的 supporting role
```

### 输出示例

```json
{
  "context_pack": [
    {
      "citation_id": "D1-C014",
      "source": "docs/agent_workflow.md",
      "section": "Self-Reflection Judge",
      "supporting_role": "defines judge output schema",
      "compressed_text": "Answer Judge outputs failure_type and repair_action based on citation support and faithfulness."
    },
    {
      "citation_id": "D1-C021",
      "source": "docs/repair_router.md",
      "section": "Repair Actions",
      "supporting_role": "maps failure_type to repair action",
      "compressed_text": "citation_error triggers regenerate_with_evidence_only; weak_evidence triggers graph_expand."
    }
  ],
  "dropped_chunks": [
    {
      "chunk_id": "D1-C030",
      "reason": "duplicate evidence"
    }
  ],
  "context_tokens": 1280
}
```

### 高级感来源

普通 RAG 是“把检索结果塞给模型”。Evidence Composer 是“构造可控、可引用、可评测的上下文包”。

---

## 6.7 Grounded Answer Generator

### 模块定位

Answer Generator 只基于 Evidence Composer 输出的 context pack 作答。

### 生成约束

```text
1. 每个关键结论必须带 citation_id
2. 不允许使用 context pack 外的信息强答
3. 如果证据不足，要明确说明不足
4. 对多跳问题，要分步骤解释证据链
5. 对 comparison 问题，要按来源分组
```

### 输出示例

```json
{
  "answer": "Answer Judge 会影响 Repair Router，因为 Judge 会输出 failure_type 和 repair_action。Repair Router 根据这些字段决定是重新检索、图扩展，还是基于证据重新生成答案。[D1-C014][D1-C021]",
  "citations": ["D1-C014", "D1-C021"],
  "confidence": 0.82
}
```

---

## 6.8 Self-Reflection Judge + Citation Guardrails

### 模块定位

Judge 是系统可靠性的核心。它不是简单判断“答案好不好”，而是从多个维度检查答案是否可信。

### Judge 输出

```json
{
  "answer_relevance": 0.88,
  "citation_support": 0.76,
  "faithfulness": 0.82,
  "context_sufficiency": 0.70,
  "guardrail_pass": false,
  "failure_type": "weak_evidence",
  "reason": "答案解释了 Judge 与 Repair Router 的关系，但引用证据中缺少完整的 repair action 映射。",
  "repair_action": "graph_expand"
}
```

### 检查维度

| 维度 | 含义 |
|---|---|
| answer_relevance | 是否回答了用户问题 |
| citation_support | 引用是否真正支持结论 |
| faithfulness | 是否忠于证据，没有无依据发挥 |
| context_sufficiency | 当前证据是否足够完整 |
| guardrail_pass | 是否通过系统保护规则 |

### Citation Guardrails

第一版实现 3 条规则：

```text
1. 没有 citation 的关键结论不允许通过
2. citation 不包含相关证据时不允许通过
3. context_sufficiency 低于阈值时触发 repair
```

### failure_type

```text
retrieval_miss     没有检索到关键证据
weak_evidence      证据不完整或不够强
citation_error     引用不支持结论
hallucination      答案包含证据外内容
context_noise      上下文噪声太多
incomplete_answer  回答不完整
```

---

## 6.9 Guarded Repair Router

### 模块定位

Repair Router 根据 Judge 的 failure_type 做针对性修复，而不是简单 retry。

### 修复策略

| failure_type | repair_action | 说明 |
|---|---|---|
| retrieval_miss | rewrite_query | 重写问题后重新检索 |
| weak_evidence | graph_expand | 用 term graph 扩展相关概念 |
| citation_error | regenerate_with_evidence_only | 严格基于 evidence pack 重新生成 |
| hallucination | regenerate_with_strict_grounding | 删除无证据内容后重写 |
| context_noise | evidence_recompose | 重新组合、压缩和去噪 context |
| incomplete_answer | decompose_question | 拆成子问题分别检索 |

### 最大修复次数

第一版建议最多修复 1 次。第二版可以增加到 2 次。

原因：

1. 控制 token 成本；
2. 避免循环修复；
3. 便于评测 repair success rate。

---

## 6.10 Trace Store

### 模块定位

Trace Store 记录每次问答的完整执行过程，是项目不像玩具的关键。

### trace.jsonl 示例

```json
{
  "question_id": "q_001",
  "question": "为什么 Answer Judge 会影响 Repair Router？",
  "context_plan": {
    "query_type": "multi_hop_concept",
    "retrieval_plan": ["dense", "bm25", "graph_expand"],
    "context_budget": 3500
  },
  "retrieval": {
    "dense_chunks": ["D1-C014", "D2-C003"],
    "bm25_chunks": ["D1-C021"],
    "graph_terms": ["failure_type", "repair_action", "citation_error"],
    "final_chunks": ["D1-C014", "D1-C021"]
  },
  "retrieval_evaluator": {
    "evidence_quality": "weak",
    "recommended_action": "graph_expand"
  },
  "evidence_pack": ["D1-C014", "D1-C021"],
  "judge_result": {
    "citation_support": 0.76,
    "faithfulness": 0.82,
    "failure_type": "weak_evidence",
    "repair_action": "graph_expand"
  },
  "repair": {
    "triggered": true,
    "action": "graph_expand",
    "repair_count": 1
  },
  "final_status": "pass",
  "latency_ms": 4200,
  "context_tokens": 1820,
  "output_tokens": 430
}
```

### 价值

1. 面试时可以展示系统如何工作；
2. 评测时可以分析失败原因；
3. 后续可以基于 trace 做优化；
4. 能支撑 README 中的实验报告。

---

## 6.11 Eval Runner

### 模块定位

Eval Runner 是项目从 demo 变成工程系统的关键。它不是事后包装，而是项目核心模块。

### eval_dataset.jsonl

```json
{
  "id": "q_001",
  "question": "为什么 Answer Judge 会影响 Repair Router？",
  "question_type": "multi_hop_concept",
  "expected_keywords": ["failure_type", "repair_action", "citation_support"],
  "reference_chunks": ["D1-C014", "D1-C021"]
}
```

### 对比策略

```text
baseline_vector_rag
hybrid_rag
hybrid_graph_rag
agentic_graph_rag_with_repair
```

### 指标

| 指标 | 含义 |
|---|---|
| retrieval_hit_rate | 是否检索到参考 chunk 或关键证据 |
| citation_support_rate | 引用是否支持答案 |
| judge_pass_rate | Judge 最终通过率 |
| repair_success_rate | 修复后是否通过 |
| avg_latency_ms | 平均延迟 |
| avg_context_tokens | 平均上下文 token |
| failure_distribution | 失败类型分布 |

### eval_report.md 应包含

```text
1. 实验设置
2. 数据集说明
3. 各策略指标表
4. 修复前后对比
5. 失败案例分析
6. token / latency trade-off
7. 下一步优化方向
```

---

## 6.12 Skill-style Prompt Registry

### 模块定位

prompt 不应该散落在代码里。新版项目引入 skill-style prompt registry，把不同 Agent 节点的 instructions、schema、rubric 独立管理。

### 目录结构

```text
skills/
├── context_planner/
│   ├── instructions.md
│   └── output_schema.json
├── retrieval_evaluator/
│   ├── instructions.md
│   └── rubric.yaml
├── evidence_composer/
│   ├── instructions.md
│   └── output_schema.json
├── answer_generator/
│   ├── instructions.md
│   └── citation_rules.md
├── self_reflection_judge/
│   ├── instructions.md
│   ├── failure_types.yaml
│   └── rubric.yaml
└── eval_report_writer/
    ├── instructions.md
    └── report_template.md
```

### 价值

1. prompt 可版本管理；
2. 节点职责更清楚；
3. 方便后续替换模型；
4. 更符合 Agent Skills / tool modularity 的工程趋势；
5. README 展示时更有专业感。

---

## 7. 推荐项目目录结构

```text
docresearch-agent/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── state.py
│   ├── graph.py
│   │
│   ├── ingestion/
│   │   ├── loaders.py
│   │   ├── structure_parser.py
│   │   ├── chunker.py
│   │   └── metadata.py
│   │
│   ├── context/
│   │   ├── context_planner.py
│   │   └── context_budget.py
│   │
│   ├── retrieval/
│   │   ├── dense_retriever.py
│   │   ├── bm25_retriever.py
│   │   ├── graph_index.py
│   │   ├── graph_retriever.py
│   │   ├── hybrid_retriever.py
│   │   └── retrieval_evaluator.py
│   │
│   ├── evidence/
│   │   ├── evidence_composer.py
│   │   └── citation_manager.py
│   │
│   ├── generation/
│   │   └── answer_generator.py
│   │
│   ├── judge/
│   │   ├── self_reflection_judge.py
│   │   └── guardrails.py
│   │
│   ├── repair/
│   │   └── repair_router.py
│   │
│   ├── tools/
│   │   ├── registry.py
│   │   ├── dense_search_tool.py
│   │   ├── bm25_search_tool.py
│   │   ├── graph_expand_tool.py
│   │   └── citation_check_tool.py
│   │
│   └── trace/
│       ├── trace_store.py
│       └── trace_schema.py
│
├── skills/
│   ├── context_planner/
│   ├── retrieval_evaluator/
│   ├── evidence_composer/
│   ├── answer_generator/
│   ├── self_reflection_judge/
│   └── eval_report_writer/
│
├── eval/
│   ├── eval_dataset.jsonl
│   ├── eval_runner.py
│   ├── metrics.py
│   └── compare_strategies.py
│
├── reports/
│   └── eval_report.md
│
├── docs/
│   ├── iris_learning_notes.md
│   ├── from_iris_to_docresearch.md
│   ├── design_decisions.md
│   ├── context_engineering_design.md
│   ├── graph_retrieval_design.md
│   └── eval_design.md
│
├── data/
│   ├── raw_docs/
│   ├── processed_chunks/
│   └── indexes/
│
├── frontend/
│   └── streamlit_app.py
│
├── README.md
├── requirements.txt
└── project_plan.md
```

如果时间紧，可以把目录简化，但 README 里仍然要体现这些模块的设计。

---

## 8. 两周实施计划

## 第 1 周：完成高级核心闭环

### Day 1：IRIS 经验迁移 + 新项目骨架

目标：明确不是复刻 IRIS，而是升级成 Context-Engineered Agentic GraphRAG。

任务：

```text
1. 新建 DocResearch-Agent 仓库
2. 建立 app/state.py、app/graph.py
3. 建立 skills/ 目录
4. 写 docs/from_iris_to_docresearch.md
5. 写 README 初版，明确新版定位
```

产出：

```text
项目骨架
新版项目定位文档
IRIS 到 DocResearch 的映射文档
```

---

### Day 2：Structure-aware Ingestion

目标：文档解析不要做成简单纯文本切块。

任务：

```text
1. 支持 Markdown 加载
2. 支持 PDF 文本加载
3. 解析 heading / code block / table 简化版
4. 生成 chunk metadata
5. 可选生成 contextual header
```

产出：

```text
chunks.jsonl
每个 chunk 包含 source、section_path、element_type、text
```

---

### Day 3：Dense + BM25 Hybrid Retrieval

目标：完成基础多路检索。

任务：

```text
1. 实现 dense retriever
2. 实现 BM25 retriever
3. 实现 merge + deduplicate
4. 实现 score fusion
5. 返回 candidate evidence
```

产出：

```text
HybridRetriever 可运行
```

---

### Day 4：Lightweight Graph Retriever

目标：让项目脱离普通 RAG，加入轻量图增强检索。

任务：

```text
1. 从 chunk 抽取 technical terms
2. 建立 term → chunk 索引
3. 建立 term co-occurrence graph
4. 实现 graph_expand(query_terms)
5. 将 graph results 与 dense/BM25 合并
```

产出：

```text
LightweightGraphIndex
GraphExpansionTool
```

---

### Day 5：Context Planner + Evidence Composer

目标：完成 context engineering 主线。

任务：

```text
1. Context Planner 输出 JSON plan
2. 根据 query_type 选择 retrieval_plan
3. Evidence Composer 去重、压缩、排序
4. 给证据绑定 citation_id
5. 控制 context budget
```

产出：

```text
context_plan.json
evidence_pack.json
```

---

### Day 6：Self-Reflection Judge + Guardrails

目标：实现可靠性检查。

任务：

```text
1. 生成 grounded answer
2. 实现 Judge 输出 relevance / citation_support / faithfulness / context_sufficiency
3. 实现 citation guardrails
4. 设计 failure_type
5. 输出 repair_action
```

产出：

```text
judge_result.json
```

---

### Day 7：Repair Router + Trace Store

目标：形成完整闭环。

任务：

```text
1. 实现 repair router
2. 支持 graph_expand / rewrite_query / regenerate 三类修复
3. 最多修复一次
4. 写 trace.jsonl
5. 跑通完整 LangGraph workflow
```

产出：

```text
完整 agentic graph workflow
trace.jsonl
```

---

## 第 2 周：评测、展示、包装

### Day 8：构建 Eval Dataset

目标：用 30～50 条问题支撑项目评测。

问题类型：

```text
fact_lookup
concept_explanation
multi_hop_concept
comparison
code_understanding
troubleshooting
```

产出：

```text
eval/eval_dataset.jsonl
```

---

### Day 9：Eval Runner

目标：对比不同系统策略。

策略：

```text
baseline_vector_rag
hybrid_rag
hybrid_graph_rag
agentic_graph_rag_with_repair
```

产出：

```text
eval_results.json
```

---

### Day 10：Eval Report

目标：输出可放 README 的实验报告。

报告内容：

```text
1. 实验设置
2. 指标定义
3. 对比结果表
4. 修复前后案例
5. 失败类型分布
6. latency / context token 分析
7. 下一步优化
```

产出：

```text
reports/eval_report.md
```

---

### Day 11：Skill Registry 整理

目标：把 prompt 和 rubrics 工程化。

任务：

```text
1. 整理 context_planner instructions
2. 整理 retrieval_evaluator rubric
3. 整理 self_reflection_judge rubric
4. 整理 citation rules
5. README 中说明 skill-style prompt registry
```

产出：

```text
skills/ 完整目录
```

---

### Day 12：Streamlit 展示页

目标：不要做复杂 Vue，用 Streamlit 快速展示。

页面展示：

```text
1. 上传文档
2. 输入问题
3. 显示 final answer
4. 显示 citations
5. 显示 context plan
6. 显示 graph expansion terms
7. 显示 judge result
8. 显示 repair action
```

产出：

```text
frontend/streamlit_app.py
```

---

### Day 13：README 高级包装

README 必须强调：

```text
1. 为什么不是普通 RAG
2. Context-Engineered Agentic GraphRAG 架构
3. 核心模块图
4. Trace 示例
5. Eval 结果
6. 与 IRIS 的关系：学习 workflow，不复刻业务
7. 运行方式
8. 项目亮点
```

产出：

```text
README.md 完整版
```

---

### Day 14：简历 bullet + 面试讲稿

产出：

```text
docs/resume_bullets.md
docs/interview_story.md
```

---

## 9. 两周内必须完成和可以放弃的内容

### 必须完成

```text
1. Context Planner
2. Structure-aware chunking
3. Dense + BM25 hybrid retrieval
4. Lightweight term graph retrieval
5. Evidence Composer
6. Self-Reflection Judge
7. Citation Guardrails
8. Repair Router
9. Trace Store
10. Eval Runner + eval_report.md
```

### 可以选做

```text
1. CrossEncoder reranker
2. Streamlit dashboard
3. PDF 表格解析
4. 技术博客学习笔记
5. 更完整的 skill registry
```

### 不建议两周内做

```text
1. 完整 MCP server
2. 完整 GraphRAG / Neo4j 知识图谱
3. 完整多模态 RAG
4. 自动抓取技术博客
5. 企业权限系统
6. 多用户系统
7. 复杂 Vue 前端
8. 微调 retriever / reranker
```

---

## 10. 实验设计

### 实验 1：检索策略对比

对比：

```text
vector only
BM25 only
hybrid
hybrid + graph expansion
```

指标：

```text
retrieval_hit_rate
context_sufficiency
avg_context_tokens
latency
```

---

### 实验 2：Graph Expansion 是否有用

目标：验证 lightweight graph retrieval 对多跳技术问题是否有帮助。

问题类型：

```text
multi_hop_concept
comparison
troubleshooting
```

对比：

```text
hybrid without graph
hybrid with graph
```

观察：

```text
是否召回更多相关概念链
是否提高 citation support
是否增加上下文噪声
```

---

### 实验 3：Evidence Composer 是否降低噪声

对比：

```text
raw top-k chunks
composed evidence pack
```

指标：

```text
citation_support_rate
faithfulness
avg_context_tokens
judge_pass_rate
```

---

### 实验 4：Repair 是否真的有效

对比：

```text
agentic_graph_rag_without_repair
agentic_graph_rag_with_repair
```

指标：

```text
repair_success_rate
judge_pass_rate
latency increase
context token increase
```

---

## 11. README 中应该如何体现高级感

README 不要写成：

```text
本项目实现了一个基于 RAG 的技术文档问答系统。
```

应该写成：

```text
DocResearch-Agent is a context-engineered agentic GraphRAG reliability system for technical documents. It focuses on context planning, hybrid graph-augmented retrieval, evidence composition, citation guardrails, self-reflection judging, guarded repair, and trace-based evaluation.
```

中文版：

```text
DocResearch-Agent 是一个面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统。项目重点不是普通问答，而是围绕上下文规划、图增强检索、证据组合、引用校验、自动修复和 trace-based evaluation 构建可靠问答闭环。
```

README 必须展示：

1. 架构图；
2. Context Plan 示例；
3. Graph Expansion 示例；
4. Evidence Pack 示例；
5. Judge Result 示例；
6. Trace 示例；
7. Eval Report 摘要表；
8. Failure Case 分析。

---

## 12. 简历写法

### 项目名称

```text
DocResearch-Agent：技术文档 Agentic RAG 可靠性系统
```

### Bullet 1

> 设计并实现 DocResearch-Agent，一个面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统。基于 LangGraph 构建 Context Planner、Hybrid + Graph Retriever、Evidence Composer、Self-Reflection Judge 与 Guarded Repair Router，实现从上下文规划、证据检索、引用生成、质量评测到自动修复的闭环。

### Bullet 2

> 实现 Dense Retrieval + BM25 + lightweight term graph expansion 的混合检索框架，通过 term → chunk、term → related term、section → chunk 等轻量图索引增强多跳技术问题和概念关联问题的证据覆盖率。

### Bullet 3

> 设计 Evidence Composer 对检索结果进行去重、压缩、排序、citation id 绑定和 context budget 控制，将原始 top-k chunks 转换为可引用、可检查、可复现的 evidence pack。

### Bullet 4

> 构建 Self-Reflection Judge 与 Citation Guardrails，从 answer relevance、citation support、faithfulness、context sufficiency 四个维度评估答案可靠性，并基于 retrieval_miss、weak_evidence、citation_error、context_noise 等失败类型触发针对性修复。

### Bullet 5

> 构建 trace-based evaluation pipeline，对比 baseline RAG、hybrid RAG、hybrid graph RAG 和 agentic repair RAG 在 retrieval hit rate、citation support rate、judge pass rate、repair success rate、latency 与 context tokens 等指标上的表现，并输出 eval_report.md 进行失败案例分析。

---

## 13. 面试讲述逻辑

可以这样讲：

> 我最初参考过一个小型 Agentic RAG 学习项目 IRIS，从里面学习了 LangGraph 状态机、多节点 workflow、Reviewer 自审循环和 RAG 工程结构。但我没有继续做报告生成方向，而是重新定义了一个技术文档可靠问答场景。

> 我发现普通 RAG 的问题不是不能回答，而是上下文不可控、证据质量不可知、引用不一定支持结论、失败后不知道该修哪里。因此我把项目升级成一个 Context-Engineered Agentic GraphRAG 系统。

> 系统第一步不是直接检索，而是由 Context Planner 判断问题类型、选择 dense / BM25 / graph expansion 等检索策略，并设置 context budget。之后 Hybrid + Graph Retriever 通过向量、关键词和轻量 term graph 召回证据，Evidence Composer 再将候选 chunk 组织成可引用的 evidence pack。

> 生成答案后，Self-Reflection Judge 会检查 answer relevance、citation support、faithfulness 和 context sufficiency。如果发现 weak_evidence、citation_error 或 context_noise，Repair Router 会触发 query rewrite、graph expansion、evidence recompose 或基于证据重新生成。

> 最后，系统会把每次执行过程写入 trace.jsonl，并通过 eval runner 对比 baseline RAG、hybrid RAG、graph RAG 和 agentic repair RAG 的效果。这样项目不是一个普通 demo，而是一个围绕 RAG 可靠性构建的工程闭环。

---

## 14. 项目风险与控制

### 风险 1：模块太多，两周做不完

控制方法：

```text
先实现轻量版，不追求完整生产级。
Graph retrieval 用 Python dict / NetworkX。
Tool registry 用简单类注册。
Skill registry 用 markdown/yaml。
前端用 Streamlit。
```

### 风险 2：图增强检索效果不明显

控制方法：

```text
重点选择 multi-hop concept 和 comparison 问题做 eval。
不要声称图检索所有问题都提升，只说明它对概念关联问题有帮助。
```

### 风险 3：Judge 不稳定

控制方法：

```text
Judge 输出固定 JSON schema。
使用规则 + LLM 结合。
关键 guardrails 用规则实现，例如 citation 是否为空、citation_id 是否存在。
```

### 风险 4：高级概念变成空话

控制方法：

每个高级概念都必须有代码产物：

| 概念 | 代码产物 |
|---|---|
| Context Engineering | context_planner.py / evidence_composer.py |
| GraphRAG Lite | graph_index.py / graph_retriever.py |
| Tool Abstraction | tools/registry.py |
| Skill Modules | skills/ 目录 |
| Trace-based Eval | trace_store.py / eval_runner.py |
| Guardrails | guardrails.py |

---

## 15. 最终判断

新版 DocResearch-Agent 不应该再被描述成“技术文档 RAG 问答系统”，而应该明确定位为：

> **面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统。**

它的高级感来自：

```text
Context Planner：先规划上下文，而不是直接检索
Hybrid + Graph Retriever：向量、关键词、轻量图增强融合
Evidence Composer：把原始 chunk 变成 evidence pack
Self-Reflection Judge：结构化评估答案可靠性
Citation Guardrails：引用必须真实支撑结论
Guarded Repair Router：按失败类型针对性修复
Trace-based Eval Loop：全过程可追踪、可评测、可复现
Skill-style Prompt Registry：prompt 和 rubrics 模块化管理
```

这个版本既吸收了 IRIS 的 Agent workflow 经验，又明显超出了 IRIS 的报告生成范式；既结合了 2025/2026 之后 Agent/RAG 工程中的 context engineering、graph retrieval、guardrails、tool abstraction 和 eval loop 思路，又能在两周内用轻量工程实现落地。

最终目标不是做一个大而全系统，而是做一个：

> **小而硬、架构清楚、技术先进、可运行、可评测、能写进简历、面试讲得清楚的高级 Agentic RAG 项目。**
