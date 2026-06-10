# DocResearch-Agent: Context-Engineered Agentic GraphRAG

> 不是普通 RAG。Context Engineering + Agentic + GraphRAG 三位一体，构建技术文档可靠问答闭环。

## Why Not Vanilla RAG?

| 问题 | Vanilla RAG | 本项目 |
|------|-------------|--------|
| 检索策略 | 固定 dense top-k | LLM 动态规划 retrieval_plan + context_budget |
| 检索路径 | 单路向量召回 | Dense + BM25 + Graph Expansion 三路融合 |
| 质量把关 | 无 | Retrieval Evaluator 判定 strong/weak/irrelevant，弱则自动补召回 |
| 证据组织 | 原文拼接 | 去重 + 角色标注 + 压缩 + budget 截断 |
| 生成校验 | 无 | 引用护栏 + 4维自省 Judge + 失败驱动修复 |
| 修复能力 | 无 | 6 种 failure_type 针对性路由修复，最多重试 N 轮 |
| 可观测性 | 无 | 全链路 Trace JSON/JSONL + eval 指标 |

## Architecture: 8-Node LangGraph Workflow

```
Question
  |
  v
Context Planner --> question_type + retrieval_plan + budget
  |
  v
Hybrid Graph Retriever --> Dense + BM25 + Graph Expansion
  |
  v
Retrieval Evaluator --> strong / weak / irrelevant / conflicting
  |
  v
Evidence Composer --> dedup + role_label + budget_control
  |
  v
Grounded Answer Generator --> cited_answer + confidence
  |
  v
Self-Reflection Judge + Citation Guardrails
  |
  v (conditional edge)
Repair Router --> 6 failure_types --> targeted repair
  |                    |
  v                    v (loop back)
END              Trace Store + Eval Runner
```

8 nodes in `app/graph.py`:
1. `context_planner` -- 问题分类 + 检索规划 + 预算分配
2. `hybrid_graph_retriever` -- 三路融合检索 + score fusion
3. `retrieval_evaluator` -- 检索质量评估，驱动补召回
4. `evidence_composer` -- 证据打包，budget 截断
5. `answer_generator` -- 带引用生成 + 规则自检
6. `citation_guardrails` -- 三层引用检查
7. `self_reflection_judge` -- 4维评分 + failure_type 驱动修复
8. `repair_router` (conditional edge) -- 6种失败类型路由

## Core Modules

| # | Module | Day | Description |
|---|--------|-----|-------------|
| 01 | Context Planner | 5 | question_type分类 + retrieval_plan + context_budget |
| 02 | Structure-aware Chunker | 2 | Markdown结构感知切块 + contextual_header |
| 03 | Tool Registry | 5 | MCP-style工具注册 + Skill Prompt Registry |
| 04 | Hybrid Graph Retriever | 3+4 | Dense+BM25+Graph三路融合 + score fusion |
| 05 | Retrieval Evaluator | 5 | 检索质量评估: evidence_quality + recommended_action |
| 06 | Evidence Composer | 5 | 去重+角色标注+压缩+budget截断 |
| 07 | Grounded Answer Generator | 6 | 带引用生成 + 规则自检 |
| 08 | Self-Reflection Judge | 6 | 4维评分 + failure_type驱动修复 |
| 09 | Citation Guardrails | 6 | 三层检查: format/alignment/support |
| 10 | Repair Router | 7 | 6种failure_type --> 针对性修复路由 |
| 11 | Trace Store | 7 | 全链路追踪 JSON/JSONL + eval指标 |

## Trace Example: TechDocQA

```
Q: LangGraph StateGraph 的作用是什么？
[1] Plan: type=concept, plan=['dense', 'bm25', 'graph_expand'], budget=3500
[2] Retrieve: status=ok, n=10, stats={'dense': 20, 'bm25': 11, 'graph_expand': 14}
    top1: langgraph_001-s01-c000 score=0.628 via=['dense', 'bm25', 'graph_expand']
[3] Eval: quality=weak, action=graph_expand
[4] Evidence: pack=10, tokens=2818
[5] Answer: confidence=high, citations=1
    "StateGraph 是 LangGraph 中的核心类..."
[6] Guardrails: pass=False (rule-based strict)
[7] Judge: rel=1.00 cit=0.10 faith=1.00 ctx=1.00
```

## Eval: MultiHopRAG Gold Recall = 1.00

```
Q: (multi-hop question about 2 TechCrunch articles)
[2] Retrieve: Gold recall = 3/3 = 1.00 (all gold chunks found!)
    stats={'dense': 20, 'bm25': 20, 'graph_expand': 20}
[4] Answer: confidence=high, citations=2
[6] Judge: rel=0.70 cit=0.29 faith=1.00
```

MultiHopRAG benchmark 上达到 gold recall 1.00，所有标注的正确 chunk 均被三路融合检索召回。

## Project Stats

- **11** core modules, each follows Module design pattern
- **140+** unit tests, all PASS
- **2** eval datasets: MultiHop-RAG (2556) + TechDocQA (42)
- **8** eval configs (2 datasets x 4 strategies)
- **8** engineering Skills (instructions/rubric/schema)
- Dual Embedding: DashScope API (default) + HuggingFace Local

## Relationship with IRIS

DocResearch 从 IRIS 学习了 LangGraph 工作流编排经验，但做了根本性重构：
- IRIS 做自动调研报告（多源搜集 + 长文生成）
- DocResearch 做技术文档可靠问答（引用校验 + 自省修复 + trace eval）
- 学习 workflow 编排模式，不复刻业务逻辑

## Quick Start

### 前置条件

- Python 3.10+
- Conda (推荐) 或 venv
- 百炼 DashScope API Key (用于 Embedding 和 LLM 调用)

### Step 1: 创建环境并安装依赖

```bash
# 用 Conda (推荐)
conda create -n docresearch python=3.10 -y
conda activate docresearch
pip install -r requirements.txt

# 或用 venv
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### Step 2: 配置 API Key

```bash
cp .env.example .env
```

编辑 `.env`，填入你的百炼 API Key:

```
OPENAI_API_KEY=sk-xxxxxxxx
DASHSCOPE_API_KEY=sk-xxxxxxxx
EMBEDDING_MODE=api
EMBEDDING_MODEL=text-embedding-v3
FAST_MODEL=qwen-max
SMART_MODEL=deepseek-r1
```

> `EMBEDDING_MODE=api` 表示调用百炼 DashScope API 做 Embedding (不需要本地 GPU)。
> 设为 `local` 则使用本地 HuggingFace 模型 (需下载模型文件)。

### Step 3: 构建索引

```bash
# 方式 A: 用已有 TechDocQA 数据集 (42 条真实技术文档 QA)
python -c "
import json, sys; sys.path.insert(0, '.')
from app.retrieval.hybrid_retriever import HybridGraphRetriever
chunks = [json.loads(l) for l in open('data/processed/techdocqa/chunks.jsonl', encoding='utf-8')]
HybridGraphRetriever().build_index(chunks, index_dir='data/indexes/techdocqa')
print(f'Built index from {len(chunks)} chunks')
"

# 方式 B: 用 MultiHopRAG 数据集 (2556 条公开 benchmark)
python -c "
import json, sys; sys.path.insert(0, '.')
from app.retrieval.hybrid_retriever import HybridGraphRetriever
chunks = [json.loads(l) for l in open('data/processed/multihop_rag/chunks.jsonl', encoding='utf-8')]
for c in chunks:
    if len(c.get('text','')) > 6000: c['text'] = c['text'][:6000]
HybridGraphRetriever().build_index(chunks, index_dir='data/indexes/multihop_rag')
print(f'Built index from {len(chunks)} chunks')
"
```

> 建索引需要调用 DashScope Embedding API，609 chunks 约 1 分钟。

### Step 4: 启动并使用

```bash
# 方式 A: Streamlit 演示页 (推荐, 一键启动)
streamlit run frontend/streamlit_app.py
# 浏览器打开 http://localhost:8501
# 侧边栏选索引目录 → 输问题 → 查看完整 pipeline 结果

# 方式 B: FastAPI 后端
uvicorn app.main:app --host 0.0.0.0 --port 8000
# POST /upload 上传文档, POST /chat 问答

# 方式 C: Python 直接调用
python -c "
from app.retrieval.hybrid_retriever import HybridGraphRetriever
r = HybridGraphRetriever()
r.load_index('data/indexes/techdocqa')
result = r.retrieve('StateGraph 的作用是什么?')
for c in result.chunks[:3]:
    print(f'{c.chunk_id} score={c.final_score:.3f}: {c.text[:80]}')
"
```

### 跑评测

```bash
# 对 TechDocQA 跑 retrieval-only 评测
python eval/run_eval.py \
  --dataset data/processed/techdocqa/eval_dataset_v1.jsonl \
  --config eval/configs/techdocqa_hybrid_graph.yaml \
  --output reports/techdocqa/hybrid_graph_results.jsonl

# 生成对比报告
python eval/generate_report.py \
  --inputs reports/techdocqa/*.jsonl \
  --output reports/techdocqa/eval_report.md
```

## Highlights

1. **Context Engineering 先于 Retrieval** -- LLM 动态规划检索策略和预算，告别固定 top-k
2. **Agentic Self-Repair Loop** -- Judge 判定 failure_type 后自动路由修复，最多重试 N 轮
3. **GraphRAG Structure Awareness** -- 利用文档结构图做 chunk 间关系扩展召回
4. **三路融合 + Score Fusion** -- Dense/BM25/Graph 各路互补，reciprocal rank fusion 合并
5. **Citation Guardrails 三层校验** -- format/alignment/support 逐层拦截幻觉
6. **Trace-based Evaluation** -- 每条问答完整 trace，支持 MultiHopRAG/TechDocQA 双数据集评测
7. **双模式 Embedding** -- DashScope API (云端) 或 HuggingFace Local (离线)，一行配置切换
