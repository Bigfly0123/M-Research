# MultiHop-RAG 数据集处理与接入指南

> 目标：把公开 MultiHop-RAG benchmark 下载、检查、转换成 DocResearch-Agent 的统一评测格式，并接入 Eval Runner，用于评估多跳检索、证据覆盖、Hybrid Retrieval、Graph Retrieval 和 Evidence Composer 的效果。

---

## 1. 为什么要用 MultiHop-RAG

MultiHop-RAG 适合作为 DocResearch-Agent 的公开 benchmark，主要用来测试：

1. 系统能否跨多个文档找到 supporting evidence；
2. Dense Retrieval、BM25、Hybrid Retrieval 的检索差异；
3. Lightweight Graph Retrieval 是否能提升多跳证据覆盖；
4. Evidence Composer 是否会保留正确证据；
5. Agentic Repair 是否能在证据不足时触发修复。

注意：MultiHop-RAG 主要用于 **多跳检索评测**，不要一开始就把它当作完整技术文档 QA 数据集。第一阶段建议先做 `retrieval_only`，稳定后再做 `full_qa`。

---

## 2. 推荐目录结构

在项目根目录下创建：

```text
docresearch-agent/
├── data/
│   ├── raw/
│   │   └── multihop_rag/
│   │       ├── MultiHopRAG.json
│   │       └── corpus.json
│   │
│   ├── processed/
│   │   └── multihop_rag/
│   │       ├── corpus_docs.jsonl
│   │       ├── chunks.jsonl
│   │       ├── eval_dataset_v1.jsonl
│   │       ├── eval_dataset_sample_100.jsonl
│   │       ├── eval_dataset_sample_300.jsonl
│   │       └── id_maps.json
│   │
│   └── indexes/
│       └── multihop_rag/
│           ├── bm25/
│           ├── vector/
│           └── graph/
│
├── scripts/
│   ├── download_multihop_rag.py
│   ├── inspect_multihop_rag.py
│   ├── convert_multihop_rag.py
│   ├── check_multihop_conversion.py
│   ├── sample_multihop_rag.py
│   └── build_multihop_indexes.py
│
├── eval/
│   ├── run_eval.py
│   ├── metrics.py
│   ├── generate_report.py
│   └── configs/
│       ├── baseline_vector.yaml
│       ├── bm25.yaml
│       ├── hybrid.yaml
│       ├── hybrid_graph.yaml
│       └── agentic_graph_repair.yaml
│
└── reports/
    └── multihop_rag/
```

---

## 3. 第一步：下载数据

### 3.1 安装依赖

```bash
pip install datasets pandas tqdm
```

### 3.2 方法 A：使用 Hugging Face datasets 下载

`scripts/download_multihop_rag.py`：

```python
from datasets import load_dataset
from pathlib import Path
import json

OUT_DIR = Path("data/raw/multihop_rag")
OUT_DIR.mkdir(parents=True, exist_ok=True)

def main():
    ds = load_dataset("yixuantt/MultiHopRAG")
    print(ds)

    for split_name, split in ds.items():
        out_path = OUT_DIR / f"{split_name}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for row in split:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"Saved {split_name}: {len(split)} rows -> {out_path}")

if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/download_multihop_rag.py
```

### 3.3 方法 B：直接下载原始文件

如果 Hugging Face loader 不稳定，使用：

```bash
mkdir -p data/raw/multihop_rag

wget -O data/raw/multihop_rag/MultiHopRAG.json \
  https://huggingface.co/datasets/yixuantt/MultiHopRAG/raw/main/MultiHopRAG.json

wget -O data/raw/multihop_rag/corpus.json \
  https://huggingface.co/datasets/yixuantt/MultiHopRAG/raw/main/corpus.json
```

如果 `wget` 不可用，改用 `curl`：

```bash
curl -L -o data/raw/multihop_rag/MultiHopRAG.json \
  https://huggingface.co/datasets/yixuantt/MultiHopRAG/raw/main/MultiHopRAG.json

curl -L -o data/raw/multihop_rag/corpus.json \
  https://huggingface.co/datasets/yixuantt/MultiHopRAG/raw/main/corpus.json
```

---

## 4. 第二步：检查原始数据结构

不要下载后直接写转换逻辑。必须先 inspect，因为字段名可能不是固定的。

`scripts/inspect_multihop_rag.py`：

```python
import json
from pathlib import Path
from collections import Counter

RAW_DIR = Path("data/raw/multihop_rag")

def load_json_any(path: Path):
    text = path.read_text(encoding="utf-8")
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        rows = []
        for line in text.splitlines():
            line = line.strip()
            if line:
                rows.append(json.loads(line))
        return rows

def preview_obj(name, obj, n=3):
    print("\n" + "=" * 80)
    print(f"[{name}] type={type(obj)}")

    if isinstance(obj, list):
        print(f"len={len(obj)}")
        for i, row in enumerate(obj[:n]):
            print(f"\n--- sample {i} ---")
            print(json.dumps(row, ensure_ascii=False, indent=2)[:3000])
    elif isinstance(obj, dict):
        print(f"keys={list(obj.keys())[:30]}")
        for i, (k, v) in enumerate(list(obj.items())[:n]):
            print(f"\n--- item {i}, key={k} ---")
            print(json.dumps(v, ensure_ascii=False, indent=2)[:3000])

def key_stats(obj):
    if isinstance(obj, list) and obj and isinstance(obj[0], dict):
        counter = Counter()
        for row in obj:
            for k in row.keys():
                counter[k] += 1
        print("\nKey frequency:")
        for k, c in counter.most_common():
            print(k, c)

def main():
    for filename in ["MultiHopRAG.json", "corpus.json", "train.jsonl", "validation.jsonl", "test.jsonl"]:
        path = RAW_DIR / filename
        if not path.exists():
            continue
        obj = load_json_any(path)
        preview_obj(filename, obj)
        key_stats(obj)

if __name__ == "__main__":
    main()
```

运行：

```bash
python scripts/inspect_multihop_rag.py
```

需要确认：

```text
MultiHopRAG.json:
- question / query 字段叫什么
- answer 字段叫什么
- evidence / supporting evidence 字段叫什么
- evidence 中是否包含 title / doc_id / text

corpus.json:
- 文档 id 字段叫什么
- title 字段叫什么
- body / text 字段叫什么
- metadata 字段有哪些
```

---

## 5. 第三步：转换成统一格式

### 5.1 Corpus 格式

输出：`data/processed/multihop_rag/corpus_docs.jsonl`

```json
{
  "doc_id": "mh_doc_000001",
  "source_dataset": "MultiHop-RAG",
  "title": "...",
  "text": "...",
  "metadata": {
    "original_id": "..."
  }
}
```

### 5.2 Chunk 格式

输出：`data/processed/multihop_rag/chunks.jsonl`

```json
{
  "chunk_id": "mh_doc_000001-c000",
  "doc_id": "mh_doc_000001",
  "source_dataset": "MultiHop-RAG",
  "title": "...",
  "section": "",
  "text": "...",
  "metadata": {
    "chunk_index": 0,
    "original_id": "..."
  }
}
```

第一版建议：**一个 document 作为一个 chunk**。如果后面文档过长，再按 512 tokens 或 800 characters 切分。

### 5.3 Eval Dataset 格式

输出：`data/processed/multihop_rag/eval_dataset_v1.jsonl`

```json
{
  "id": "mh_q_000001",
  "source_dataset": "MultiHop-RAG",
  "question": "...",
  "question_type": "multi_hop",
  "expected_answer": "...",
  "gold_doc_ids": ["mh_doc_000123", "mh_doc_000456"],
  "gold_chunk_ids": ["mh_doc_000123-c000", "mh_doc_000456-c000"],
  "gold_evidence_texts": ["...", "..."],
  "difficulty": "medium",
  "metadata": {
    "original_index": 0,
    "num_gold_docs": 2
  }
}
```

### 5.4 转换脚本要求

实现：`scripts/convert_multihop_rag.py`

核心要求：

1. 不要假设字段名固定，要根据 inspect 的结果适配；
2. 建立 `original_id -> doc_id` 映射；
3. 建立 `title -> doc_id` 映射；
4. 从 evidence 中尽量找出 gold docs；
5. 如果 evidence 只有文本，则尝试用文本片段反查 corpus；
6. 最终保存 `corpus_docs.jsonl`、`chunks.jsonl`、`eval_dataset_v1.jsonl`、`id_maps.json`。

---

## 6. 第四步：质量检查

实现：`scripts/check_multihop_conversion.py`

必须输出：

```text
docs 数量
chunks 数量
eval rows 数量
question 非空数量
answer 非空数量
gold_doc_ids 非空数量
gold_chunk_ids 非空数量
gold docs 数量分布
前 3 条样本预览
```

验收标准：

```text
1. question 基本全部非空；
2. expected_answer 基本全部非空；
3. gold_doc_ids 或 gold_chunk_ids 不能大量为空；
4. 如果 gold 映射失败，需要回到 inspect 输出，修正 evidence 字段映射；
5. 不能跳过质量检查。
```

运行：

```bash
python scripts/check_multihop_conversion.py
```

---

## 7. 第五步：抽样

不要一开始全量跑，先抽样 100 条和 300 条。

实现：`scripts/sample_multihop_rag.py`

抽样规则：

```text
1. random seed = 42；
2. 优先选择 question、expected_answer、gold_chunk_ids 都非空的样本；
3. 输出 sample_100 和 sample_300。
```

输出：

```text
data/processed/multihop_rag/eval_dataset_sample_100.jsonl
data/processed/multihop_rag/eval_dataset_sample_300.jsonl
```

运行：

```bash
python scripts/sample_multihop_rag.py
```

---

## 8. 第六步：建立索引

输入：

```text
data/processed/multihop_rag/chunks.jsonl
```

需要建立三个索引。

### 8.1 Vector Index

建议使用 Chroma / FAISS。

推荐依赖：

```bash
pip install chromadb sentence-transformers
```

推荐 embedding：

```text
BAAI/bge-small-en-v1.5
```

输出：

```text
data/indexes/multihop_rag/vector/
```

### 8.2 BM25 Index

推荐依赖：

```bash
pip install rank-bm25
```

输出：

```text
data/indexes/multihop_rag/bm25/
```

### 8.3 Lightweight Graph Index

第一版不要做完整 GraphRAG，只做：

```text
1. 提取 term / keywords；
2. 建立 term -> chunk；
3. 建立 chunk -> term；
4. 建立 term co-occurrence graph；
5. query 时进行一跳 graph expansion。
```

推荐依赖：

```bash
pip install scikit-learn networkx
```

输出：

```text
data/indexes/multihop_rag/graph/
```

---

## 9. 第七步：Eval Runner 配置

至少准备四个配置。

### 9.1 baseline_vector.yaml

```yaml
name: baseline_vector
dataset: multihop_rag
retriever:
  use_dense: true
  use_bm25: false
  use_graph: false
  top_k: 10
pipeline:
  use_context_planner: false
  use_retrieval_evaluator: false
  use_evidence_composer: false
  use_judge: false
  use_repair: false
mode: retrieval_only
```

### 9.2 hybrid.yaml

```yaml
name: hybrid
dataset: multihop_rag
retriever:
  use_dense: true
  use_bm25: true
  use_graph: false
  top_k: 10
pipeline:
  use_context_planner: false
  use_retrieval_evaluator: false
  use_evidence_composer: true
  use_judge: false
  use_repair: false
mode: retrieval_only
```

### 9.3 hybrid_graph.yaml

```yaml
name: hybrid_graph
dataset: multihop_rag
retriever:
  use_dense: true
  use_bm25: true
  use_graph: true
  graph_hops: 1
  top_k: 10
pipeline:
  use_context_planner: true
  use_retrieval_evaluator: false
  use_evidence_composer: true
  use_judge: false
  use_repair: false
mode: retrieval_only
```

### 9.4 agentic_graph_repair.yaml

```yaml
name: agentic_graph_repair
dataset: multihop_rag
retriever:
  use_dense: true
  use_bm25: true
  use_graph: true
  graph_hops: 1
  top_k: 10
pipeline:
  use_context_planner: true
  use_retrieval_evaluator: true
  use_evidence_composer: true
  use_judge: true
  use_repair: true
mode: full_qa
```

建议第一阶段先跑前三个 `retrieval_only`。`agentic_graph_repair` 等系统稳定后再跑。

---

## 10. 第八步：指标实现

在 `eval/metrics.py` 中实现以下指标。

### 10.1 gold_doc_recall@k

衡量 top-k 检索结果覆盖了多少 gold documents。

```python
def gold_doc_recall_at_k(retrieved_doc_ids, gold_doc_ids, k):
    topk = set(retrieved_doc_ids[:k])
    gold = set(gold_doc_ids)
    if not gold:
        return None
    return len(topk & gold) / len(gold)
```

### 10.2 all_gold_docs_hit@k

判断是否所有 gold documents 都进入 top-k。

```python
def all_gold_docs_hit_at_k(retrieved_doc_ids, gold_doc_ids, k):
    topk = set(retrieved_doc_ids[:k])
    gold = set(gold_doc_ids)
    if not gold:
        return None
    return int(gold.issubset(topk))
```

### 10.3 gold_chunk_recall@k

判断 top-k chunk 是否覆盖 gold chunks。

```python
def gold_chunk_recall_at_k(retrieved_chunk_ids, gold_chunk_ids, k):
    topk = set(retrieved_chunk_ids[:k])
    gold = set(gold_chunk_ids)
    if not gold:
        return None
    return len(topk & gold) / len(gold)
```

### 10.4 selected_evidence_recall

判断 Evidence Composer 是否保留了正确证据。

```python
def selected_evidence_recall(selected_chunk_ids, gold_chunk_ids):
    selected = set(selected_chunk_ids)
    gold = set(gold_chunk_ids)
    if not gold:
        return None
    return len(selected & gold) / len(gold)
```

### 10.5 其他指标

可选：

```text
avg_latency_ms
answer_keyword_coverage
judge_pass_rate
repair_success_rate
context_tokens
```

---

## 11. 第九步：Eval Runner 输出格式

`system.run(question)` 必须返回统一 trace：

```json
{
  "retrieved_doc_ids": ["mh_doc_000001", "mh_doc_000123"],
  "retrieved_chunk_ids": ["mh_doc_000001-c000", "mh_doc_000123-c000"],
  "selected_chunk_ids": ["mh_doc_000123-c000"],
  "answer": "...",
  "judge_result": {},
  "repair_action": null,
  "latency_ms": 1200
}
```

Eval Runner 每条结果保存为：

```json
{
  "question_id": "mh_q_000001",
  "source_dataset": "MultiHop-RAG",
  "question": "...",
  "expected_answer": "...",
  "gold_doc_ids": ["..."],
  "gold_chunk_ids": ["..."],
  "trace": {},
  "metrics": {
    "gold_doc_recall@10": 0.5,
    "all_gold_docs_hit@10": 0,
    "gold_chunk_recall@10": 0.5,
    "selected_evidence_recall": 0.5
  }
}
```

输出路径：

```text
reports/multihop_rag/baseline_vector_results.jsonl
reports/multihop_rag/hybrid_results.jsonl
reports/multihop_rag/hybrid_graph_results.jsonl
reports/multihop_rag/agentic_graph_repair_results.jsonl
```

---

## 12. 第十步：生成评测报告

实现：`eval/generate_report.py`

输出：

```text
reports/multihop_rag/eval_report.md
```

报告结构：

```markdown
# MultiHop-RAG Evaluation Report

## 1. Dataset

- Dataset: MultiHop-RAG
- Sample size: 100
- Task: multi-hop retrieval and QA
- Corpus: MultiHop-RAG corpus

## 2. Compared Configs

| Config | Dense | BM25 | Graph | Repair |
|---|---|---|---|---|
| baseline_vector | yes | no | no | no |
| hybrid | yes | yes | no | no |
| hybrid_graph | yes | yes | yes | no |
| agentic_graph_repair | yes | yes | yes | yes |

## 3. Metrics

- Gold Doc Recall@10
- All Gold Docs Hit@10
- Gold Chunk Recall@10
- Selected Evidence Recall
- Avg Latency

## 4. Results

| Config | Gold Doc Recall@10 | All Gold Docs Hit@10 | Gold Chunk Recall@10 | Selected Evidence Recall | Avg Latency |
|---|---:|---:|---:|---:|---:|
| baseline_vector | ... | ... | ... | ... | ... |
| hybrid | ... | ... | ... | ... | ... |
| hybrid_graph | ... | ... | ... | ... | ... |
| agentic_graph_repair | ... | ... | ... | ... | ... |

## 5. Findings

1. ...
2. ...
3. ...

## 6. Failure Cases

...

## 7. Conclusion

...
```

---

## 13. 最终运行命令

完整流程：

```bash
python scripts/download_multihop_rag.py
python scripts/inspect_multihop_rag.py
python scripts/convert_multihop_rag.py
python scripts/check_multihop_conversion.py
python scripts/sample_multihop_rag.py
python scripts/build_multihop_indexes.py

python eval/run_eval.py \
  --dataset data/processed/multihop_rag/eval_dataset_sample_100.jsonl \
  --config eval/configs/baseline_vector.yaml \
  --output reports/multihop_rag/baseline_vector_results.jsonl

python eval/run_eval.py \
  --dataset data/processed/multihop_rag/eval_dataset_sample_100.jsonl \
  --config eval/configs/hybrid.yaml \
  --output reports/multihop_rag/hybrid_results.jsonl

python eval/run_eval.py \
  --dataset data/processed/multihop_rag/eval_dataset_sample_100.jsonl \
  --config eval/configs/hybrid_graph.yaml \
  --output reports/multihop_rag/hybrid_graph_results.jsonl

python eval/generate_report.py \
  --inputs reports/multihop_rag/*.jsonl \
  --output reports/multihop_rag/eval_report.md
```

等 retrieval-only 跑通后，再运行 full QA：

```bash
python eval/run_eval.py \
  --dataset data/processed/multihop_rag/eval_dataset_sample_100.jsonl \
  --config eval/configs/agentic_graph_repair.yaml \
  --output reports/multihop_rag/agentic_graph_repair_results.jsonl
```

---

## 14. 验收清单

最终必须产出：

```text
data/processed/multihop_rag/corpus_docs.jsonl
data/processed/multihop_rag/chunks.jsonl
data/processed/multihop_rag/eval_dataset_v1.jsonl
data/processed/multihop_rag/eval_dataset_sample_100.jsonl
data/processed/multihop_rag/id_maps.json
reports/multihop_rag/baseline_vector_results.jsonl
reports/multihop_rag/hybrid_results.jsonl
reports/multihop_rag/hybrid_graph_results.jsonl
reports/multihop_rag/eval_report.md
```

验收标准：

```text
1. sample_100 中 question、expected_answer、gold_doc_ids/gold_chunk_ids 基本非空；
2. baseline_vector、hybrid、hybrid_graph 至少三个配置能跑通；
3. eval_report.md 中有结果表；
4. 能看到 Hybrid 是否优于 baseline；
5. 能看到 Graph Retrieval 是否提高多跳 gold evidence 覆盖；
6. 能记录失败案例；
7. 不要求第一版 full QA 完美，先保证 retrieval-only 可信。
```

---

## 15. 注意事项

1. 不要直接全量跑，先 sample 100；
2. 不要直接跑 full QA，先跑 retrieval-only；
3. 不要硬编码字段名，必须先 inspect；
4. 不要把 MultiHop-RAG 说成技术文档数据集，它是公开多跳 RAG benchmark；
5. 不要用它替代自建 TechDocQA，它只能补充公开评测可信度；
6. 最重要的是 gold_doc_ids / gold_chunk_ids 映射质量；
7. 如果 gold 映射失败，先修转换脚本，不要继续跑 eval。

---

## 16. 在 README / 报告中可以这样描述

```text
为了避免只在自建文档上进行自洽评测，本项目接入 MultiHop-RAG 作为公开多跳检索 benchmark。
MultiHop-RAG 中每个问题需要跨多个文档寻找 supporting evidence，因此适合评估系统在多跳证据发现、跨文档检索和 evidence composition 上的能力。

本项目将原始 MultiHop-RAG 转换为统一 Eval Schema：
question / expected_answer / gold_doc_ids / gold_chunk_ids / gold_evidence_texts。
评测时对比 baseline vector retrieval、BM25、hybrid retrieval 和 hybrid + graph retrieval，
主要指标包括 gold_doc_recall@10、all_gold_docs_hit@10、gold_chunk_recall@10 和 selected_evidence_recall。
```
