---
language:
- en
license: apache-2.0
size_categories:
- 1K<n<10K
task_categories:
- question-answering
- text-retrieval
tags:
- rag
- retrieval-augmented-generation
- multi-hop-reasoning
- hotpotqa
- information-retrieval
- question-answering
- evaluation
---

# StratRAG

**StratRAG** is a retrieval evaluation dataset for benchmarking Retrieval-Augmented Generation (RAG) systems on multi-hop reasoning tasks. It was introduced in the paper [StratRAG: A Multi-Hop Retrieval Evaluation Dataset for Retrieval-Augmented Generation Systems](https://huggingface.co/papers/2604.22757).

It is derived from [HotpotQA](https://hotpotqa.github.io/) (distractor setting) and structured specifically for evaluating retrieval strategies — including sparse (BM25), dense, and hybrid approaches — in realistic, noisy document pool conditions.

---

## Why StratRAG?

Most RAG benchmarks either evaluate end-to-end generation quality or assume clean, small document sets. StratRAG addresses a gap: **retrieval evaluation under multi-hop, distractor-heavy conditions**, where:

- Each question requires reasoning across **2 gold documents**
- The retriever must find those 2 docs inside a pool of **15 candidates** (13 distractors)
- Questions span 3 types: **bridge**, **comparison**, and **yes-no**

This makes it suitable for measuring Recall@k, MRR, NDCG, and faithfulness of retrieved context before any generation step.

---

## Dataset Structure

### Splits

| Split      | Rows |
|------------|------|
| train      | 2000 |
| validation | 200  |

### Schema
```python
{
  "id":               str,          # e.g. "train_000042"
  "query":            str,          # the multi-hop question
  "reference_answer": str,          # ground-truth answer string
  "doc_pool": [                     # always exactly 15 documents
    {
      "doc_id": str,                # globally unique doc identifier
      "text":   str,                # title + paragraph body
      "source": str,                # paragraph title (from HotpotQA)
    }
  ],
  "gold_doc_indices": [int],        # indices into doc_pool (always [0, 1])
                                    # gold docs are always placed first
  "metadata": {
    "split":         str,           # "train" or "val"
    "question_type": str,           # "bridge" | "comparison" | "yes-no"
  },
  "created_at": str,                # ISO-8601 UTC timestamp
  "provenance": {
    "base": str,                    # "hotpot_qa(distractor)"
    "seed": int,                    # 42
  }
}
```

### Key design decisions

- **Gold docs are always at indices 0 and 1** in `doc_pool`. This makes it trivial to compute oracle retrieval metrics and verify your retriever's upper bound.
- **13 distractor documents** per row are drawn from HotpotQA's built-in distractor paragraphs — these are topically related and intentionally difficult to distinguish from gold docs.
- **Empty-text paragraphs are filtered out** — HotpotQA contains some paragraphs with no sentence content; these are excluded from distractor slots to ensure all 15 docs have real text.

---

## Usage
```python
from datasets import load_dataset

ds = load_dataset("Aryanp088/StratRAG")

# Inspect a single training example
row = ds["train"][0]
print("Query:", row["query"])
print("Answer:", row["reference_answer"])
print("Question type:", row["metadata"]["question_type"])
print("Gold doc indices:", row["gold_doc_indices"])
print("Number of docs in pool:", len(row["doc_pool"]))

# Access gold documents directly
for idx in row["gold_doc_indices"]:
    print(f"
Gold doc [{idx}]:", row["doc_pool"][idx]["text"][:200])
```

---

## Evaluation Example
```python
from datasets import load_dataset

ds = load_dataset("Aryanp088/StratRAG", split="validation")

def recall_at_k(row, k=2):
    """
    Simulate a retriever that returns the first k docs (random baseline).
    Replace retrieved_indices with your retriever's output.
    """
    retrieved_indices = list(range(k))   # replace with your retriever
    gold = set(row["gold_doc_indices"])
    hits = len(gold & set(retrieved_indices))
    return hits / len(gold)

scores = [recall_at_k(row, k=2) for row in ds]
print(f"Random Recall@2: {sum(scores)/len(scores):.3f}")  # ~0.133 (2/15)
```

To benchmark a real retriever (e.g. BM25):
```python
from rank_bm25 import BM25Okapi

def bm25_recall_at_k(row, k=2):
    docs    = [doc["text"].split() for doc in row["doc_pool"]]
    query   = row["query"].split()
    bm25    = BM25Okapi(docs)
    scores  = bm25.get_scores(query)
    top_k   = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    gold    = set(row["gold_doc_indices"])
    return len(gold & set(top_k)) / len(gold)

scores = [bm25_recall_at_k(row, k=2) for row in ds]
print(f"BM25 Recall@2: {sum(scores)/len(scores):.3f}")
```

---

## Question Type Distribution

| Type       | Train | Validation |
|------------|-------|------------|
| bridge     | 1775  | 171        |
| yes-no     | 113   | 12         |
| comparison | 112   | 17         |

---

## Provenance & Reproducibility

All rows are derived from HotpotQA (distractor configuration) with `seed=42`.
```python
from datasets import load_dataset
hotpot = load_dataset("hotpot_qa", "distractor")
```

---

## Benchmark Results

Evaluated on the validation split (n=200) using three retrieval strategies.

### Overall Results

| Retriever | Recall@1 | Recall@2 | Recall@5 | MRR    | NDCG@5 |
|-----------|----------|----------|----------|--------|--------|
| Random    | 0.0525   | 0.1425   | 0.3300   | 0.3190 | 0.2336 |
| BM25      | 0.3950   | 0.6000   | 0.8150   | 0.8732 | 0.7624 |
| Dense (MiniLM-L6-v2) | 0.4175 | 0.6500 | 0.8600 | 0.9035 | 0.8087 |
| **Hybrid (BM25 + Dense)** | **0.4400** | **0.6975** | **0.9050** | **0.9310** | **0.8543** |

> Hybrid retriever uses equal-weight (α=0.5) min-max normalized score fusion.

### Hybrid Retriever — By Question Type

| Question Type | n   | Recall@2 | MRR    | NDCG@5 |
|---------------|-----|----------|--------|--------|
| bridge        | 171 | 0.6696   | 0.9281 | 0.8418 |
| comparison    | 17  | 0.8824   | 0.9706 | 0.9473 |
| yes-no        | 12  | 0.8333   | 0.9167 | 0.9007 |

**Key findings:**
- Hybrid retrieval consistently outperforms sparse and dense individually across all metrics
- Dense retrieval outperforms BM25 on all metrics, highlighting the importance of semantic matching for multi-hop questions
- Bridge questions are the hardest retrieval type (Recall@2 = 0.67), as they require cross-document reasoning without strong lexical overlap
- Comparison and yes-no questions benefit more from BM25's keyword matching (higher Recall@2)
- Recall@5 of 0.905 for Hybrid shows that 90% of the time, both gold documents appear in the top 5 — a strong upper bound for downstream generation

---

## Limitations

- **English only** — inherited from HotpotQA
- **Wikipedia-domain** — all documents are Wikipedia paragraphs; may not generalize to other domains without adaptation
- **2,200 total rows** — suitable for retriever evaluation and fine-tuning signal, not large-scale pretraining
- **Gold position is fixed** — gold docs are always at indices 0 and 1. Shuffle `doc_pool` before training retrievers to avoid position bias
```python
import random
random.shuffle(row["doc_pool"])   # shuffle before use in training
```

---

## Citation

If you use StratRAG in your work, please cite:
```bibtex
@dataset{patodiya2026stratrag,
  author    = {Patodiya, Aryan},
  title     = {StratRAG: A Multi-Hop Retrieval Evaluation Dataset for RAG Systems},
  year      = {2026},
  publisher = {Hugging Face},
  url       = {https://huggingface.co/datasets/Aryanp088/StratRAG}
}
```

---

## Author

**Aryan Patodiya** — ML Systems Engineer  
MS Computer Science @ California State University, Fresno  
[Portfolio](https://aryanp-portfolio.netlify.app) · [GitHub](https://github.com/aryanpatodiya08) · aryanpatodiya018@gmail.com