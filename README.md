# DocResearch-Agent 2026

> Context-Engineered Agentic GraphRAG for reliable technical document QA.

DocResearch-Agent is a full-pipeline Agentic RAG system that goes beyond naive retrieve-then-generate. It implements an 8-node LangGraph workflow with adaptive retrieval, evidence composition, citation guardrails, self-reflection judging, and corrective repair — forming a closed loop from query understanding to grounded, cited, verified answers.

---

## Why Not Ordinary RAG?

Standard RAG pipelines suffer from:

- **Fixed top-k retrieval** — no adaptation to query difficulty or domain
- **No retrieval planning** — no query analysis before fetching documents
- **No evidence verification** — citations may not actually support claims
- **No repair loop** — bad answers pass through without correction

DocResearch-Agent addresses all four with a modular agentic architecture.

---

## System Architecture

```
Question
  │
  ▼
Context Planner          ← Query analysis, retrieval strategy planning
  │
  ▼
Adaptive Hybrid Retriever ← Dense + BM25 with dynamic weight fusion
  │
  ▼
Selective Graph Expansion ← Lightweight graph expansion (only when needed)
  │
  ▼
Retrieval Evaluator      ← Evidence quality assessment
  │
  ▼
Evidence Composer         ← Dedup, ranking, evidence tier classification
  │
  ▼
Grounded Answer Generator ← LLM answer with inline citations
  │
  ▼
Citation Guardrails       ← Citation existence / alignment / support checks
  │
  ▼
Self-Reflection Judge     ← PASS / SOFT_WARN / HARD_FAIL three-tier decision
  │
  ▼
Repair Router (conditional) ← Only HARD_FAIL triggers targeted repair
  │
  ▼
Final Answer + Citations
```

### Key Design Decisions

| Component | Approach |
|---|---|
| Retrieval | Adaptive hybrid: dense/bm25 weights chosen per-query based on confidence signals |
| Graph | Selective expansion: only triggered when retrieval coverage is insufficient |
| Evidence | Three-tier classification: primary / supporting / context-only |
| Judge | Three-tier decision: PASS / SOFT_WARN / HARD_FAIL (only HARD_FAIL triggers repair) |
| Repair | Failure-type-aware routing with early stop |

---

## Current Results

### Level 1: Retrieval Eval (4 datasets × 6 strategies)

**MultiHop-RAG** (100 samples, multi-hop news QA):

| Strategy | Recall@10 |
|---|---:|
| BM25 only | 0.748 |
| Dense only | 0.793 |
| Hybrid | **0.803** |
| Hybrid + Graph | **0.813** |
| Adaptive Hybrid | 0.802 |

> Key finding: Reranker (ms-marco-MiniLM) caused hybrid degradation (0.656 → 0.803 after fix).

**Adaptive Hybrid** across all datasets:

| Dataset | adaptive_hybrid r@10 | BM25 baseline |
|---|---:|---:|
| MultiHop-RAG | 0.802 | 0.748 |
| TechDocQA | 1.000 | 1.000 |
| GaRAGe | 0.980 | 0.980 |
| StratRAG | 0.875 | 0.815 |

### Level 2: Full QA Eval

**TechDocQA** (42 samples):

| Metric | Value |
|---|---:|
| has_answer_rate | 1.000 |
| citation_precision | **0.952** |
| faithfulness | **0.988** |
| guardrail_pass_rate | 0.952 |
| has_primary_cited_rate | 0.738 |
| avg_repair_count | 0.12 |
| avg_latency | 16.4s |

**GaRAGe** (50 samples):

| Metric | Value |
|---|---:|
| citation_precision | **0.980** |
| faithfulness | **0.970** |
| guardrail_pass_rate | 0.980 |
| has_primary_cited_rate | 0.980 |
| avg_repair_count | 0.06 |
| avg_latency | 11.6s |

> Phase 3 calibration reduced unnecessary repairs by **96.5%** while maintaining answer quality.

### Phase 4: Robustness Eval (20 samples)

| Test Type | Correct Rate | Key Finding |
|---|---:|---|
| Out-of-domain | 80% | System detects most OOD queries via Judge |
| Insufficient evidence | 80% | HARD_FAIL/SOFT_WARN when docs lack answer |
| Citation integrity | 80% | Normal queries maintain valid citations |
| Ambiguous questions | 40% | Known limitation (no active clarification) |

### Human Audit (26 samples, Phase 5 Verified)

| Metric | Value |
|---|---:|
| Hallucination rate | **7.7%** (only 2/26 samples) |
| Avg citation support | **1.769 / 2** |
| Avg correctness | 1.423 / 2 |
| Perfect sample rate | 42.3% |
| Truncation rate | **0%** (after Phase 5 fix) |

> Human audit confirms low hallucination and strong citation support. Automatic metrics are reliable.

> See [Demo Cases](DocResearch/reports/demo_cases.md) for 5 representative examples.
> See [Final Report](DocResearch/reports/final_project_report.md) for complete project summary.

---

## Project Structure

```
DocResearch-Agent/
├── DocResearch/              ← Main project: Agentic GraphRAG system
│   ├── app/                  ← Core system (LangGraph workflow)
│   │   ├── context/          ← Context Planner
│   │   ├── retrieval/        ← Hybrid Retriever + Adaptive Hybrid + Graph
│   │   ├── evidence/         ← Evidence Composer + Citation Manager
│   │   ├── generation/       ← Grounded Answer Generator
│   │   ├── judge/            ← Self-Reflection Judge + Citation Guardrails
│   │   ├── repair/           ← Corrective Repair Router
│   │   ├── graph.py          ← LangGraph workflow orchestration
│   │   ├── state.py          ← AgentState definition
│   │   └── config.py         ← System configuration
│   ├── eval/                 ← Evaluation framework
│   │   ├── level1_eval.py    ← Level 1: Retrieval eval
│   │   └── level2_fullqa_eval.py ← Level 2: Full QA eval
│   ├── data/                 ← Datasets, indexes, processed data
│   ├── reports/              ← Evaluation reports
│   └── scripts/              ← Data processing and analysis scripts
├── MultiHopRAG/             ← Dataset: Multi-hop news QA
├── StratRAG/                ← Dataset: Strategy analysis documents
├── TechdocQA/               ← Dataset: Technical document QA
├── GaRAGe/                  ← Dataset: Grounding-aware RAG evaluation
├── backend/                 ← IRIS backend (historical reference)
├── frontend/                ← IRIS Frontend (historical reference)
└── docs/                    ← Project documentation and module guides
```

---

## How to Run

### 1. Environment Setup

```bash
conda create -n iris-test python=3.10
conda activate iris-test
cd DocResearch
pip install -r requirements.txt
```

### 2. Build Indexes

```bash
# Build FAISS + BM25 indexes for each dataset
python scripts/rebuild_faiss_indexes.py
```

### 3. Level 1: Retrieval Eval

```bash
# Single dataset + strategy
python eval/level1_eval.py --dataset multihop_rag --strategy adaptive_hybrid

# All datasets, all strategies
python eval/level1_eval.py --dataset all --strategy all
```

### 4. Level 2: Full QA Eval

```bash
# TechDocQA Full QA
python eval/level2_fullqa_eval.py --dataset techdocqa --strategy hybrid

# GaRAGe Full QA
python eval/level2_fullqa_eval.py --dataset garage --strategy hybrid
```

### 5. Quick Test

```bash
# Quick single-sample test
python scripts/test_fullqa.py
```

---

## Reports

| Report | Description |
|---|---|
| [Final Project Report](DocResearch/reports/final_project_report.md) | **Complete project summary** (recommended starting point) |
| [Final Eval Summary](DocResearch/reports/final_eval_summary.md) | All evaluation results across Phase 1–5 |
| [Demo Cases](DocResearch/reports/demo_cases.md) | 5 representative examples showcasing system capabilities |
| [Phase 3 Reliability Report](DocResearch/reports/docresearch_phase3_reliability_report.md) | Judge/Repair calibration details |
| [Phase 4 Human Audit Report](DocResearch/reports/phase4_human_audit_report.md) | Human audit of 26 samples with detailed results |
| [Phase 4 Robustness Report](DocResearch/reports/phase4_robustness_report.md) | Out-of-domain, evidence insufficiency, ambiguity tests |
| [Resume Description](DocResearch/reports/resume_project_description.md) | CN/EN project description for resume |
| [12 Module Guides](docs/docresearch_12_module_guides/) | Architecture documentation for each module |

---

## Tech Stack

- **Agent Framework**: LangGraph (LangChain ecosystem)
- **Dense Retrieval**: FAISS + sentence-transformers
- **BM25 Retrieval**: rank-bm25
- **Graph Expansion**: Custom lightweight graph index
- **LLM**: OpenAI API (GPT-4o-mini)
- **Evaluation**: Custom metrics (recall@k, citation_precision, faithfulness)
- **Data**: MultiHop-RAG, StratRAG, TechDocQA, GaRAGe

---

## Development Phases

1. **Phase 1**: Core retrieval pipeline (dense + BM25 + hybrid + graph), initial evaluation
2. **Phase 2**: Reranker root-cause fix, adaptive hybrid, selective graph, Level 1/2 eval
3. **Phase 3**: Judge/Repair calibration, evidence tier classification, Full QA stabilization
4. **Phase 4**: Robustness eval, primary_evidence_coverage, human audit, demo cases, final report
5. **Phase 5**: Truncation fix, human audit integration, demo polish, release preparation

---

## Limitations

- **Ambiguous questions**: No active clarification mechanism (40% correct). Future work.
- **Citation coverage**: LLM tends to cite only 1-2 chunks per answer (0.15-0.16 raw coverage).
- **Open-domain retrieval**: GaRAGe safe refusals (30%) when evidence is not in the index.
- **Domain boundary**: OOD queries with vocabulary overlap may escape detection (20% failure rate).
