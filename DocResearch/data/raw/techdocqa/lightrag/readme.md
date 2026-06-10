---
title: LightRAG README
source_url: https://raw.githubusercontent.com/HKUDS/LightRAG/main/README.md
source_type: readme
topic: lightrag
collected_at: 2026-05-18
---

# LightRAG: Simple and Fast Retrieval-Augmented Generation

LightRAG is a simple and fast RAG framework that incorporates graph-based text indexing and dual-level retrieval to achieve superior performance over existing RAG systems. It is developed by the HKU Data Science group.

## News

- 2026.03: Integrated **OpenSearch** as a unified storage backend, providing comprehensive support for all four LightRAG storage.
- 2026.03: Introduced a setup wizard. Support for local deployment of embedding, reranking, and storage backends via Docker.
- 2025.11: Integrated **RAGAS for Evaluation** and **Langfuse for Tracing**.
- 2025.10: Eliminated processing bottlenecks to support **Large-Scale Datasets Efficiently**.
- 2025.09: Enhances knowledge graph extraction accuracy for **Open-Sourced LLMs** such as Qwen3-30B-A3B.
- 2025.08: **Reranker** is now supported, significantly boosting performance for mixed queries.
- 2025.08: Added **Document Deletion** with automatic KG regeneration.
- 2025.06: Released [RAG-Anything](https://github.com/HKUDS/RAG-Anything) — an **All-in-One Multimodal RAG** system.
- 2025.06: Supports comprehensive multimodal data handling through RAG-Anything integration.
- 2025.03: Supports citation functionality for proper source attribution.
- 2025.02: Supports MongoDB as an all-in-one storage solution.
- 2025.01: Released [MiniRAG](https://github.com/HKUDS/MiniRAG) making RAG simpler with small models.
- 2025.01: Supports PostgreSQL as an all-in-one storage solution.
- 2024.11: LightRAG WebUI — interface for insert, query, and visualize knowledge.
- 2024.11: Supports Neo4J for graph database storage.

## Installation

### Install LightRAG Server

```bash
# Install from PyPI using uv (recommended)
uv tool install "lightrag-hku[api]"

# Build front-end artifacts
cd lightrag_webui
bun install --frozen-lockfile
bun run build
cd ..

# Setup env file
cp env.example .env  # Update with your LLM and embedding configurations
lightrag-server
```

### Install from Source

```bash
git clone https://github.com/HKUDS/LightRAG.git
cd LightRAG
make dev
source .venv/bin/activate
```

### Install LightRAG Core

```bash
uv pip install lightrag-hku
# Or: pip install lightrag-hku
```

### Docker Compose

```bash
git clone https://github.com/HKUDS/LightRAG.git
cd LightRAG
cp env.example .env  # Update with your LLM and embedding configurations
docker compose up
```

## LLM and Technology Stack Requirements

LightRAG's demands on LLMs are significantly higher than traditional RAG due to entity-relationship extraction tasks:

- **LLM Selection**:
  - Recommended: at least 32 billion parameters.
  - Context length: at least 32KB, 64KB recommended.
  - Not recommended: reasoning models during document indexing stage.
  - Query stage: use models with stronger capabilities than indexing stage.

- **Embedding Model**:
  - High-performance model essential. Recommended: `BAAI/bge-m3`, `text-embedding-3-large`.
  - Must be determined before document indexing; same model used during query.
  - Changing embedding models requires deleting existing vector tables and recreating.

- **Reranker Model**:
  - Significantly enhances retrieval performance.
  - When enabled, recommended to set "mix mode" as default query mode.
  - Recommended: `BAAI/bge-reranker-v2-m3` or Jina models.

## Quick Start

```bash
cd LightRAG
export OPENAI_API_KEY="sk-...your_openai_key..."
curl https://raw.githubusercontent.com/gusye1234/nano-graphrag/main/tests/mock_data.txt > ./book.txt
python examples/lightrag_openai_demo.py
```

## How LightRAG Works

LightRAG uses a **dual-level retrieval** paradigm with knowledge graph-based indexing:

### Indexing Phase

1. **Entity-Relationship Extraction**: The LLM extracts entities and relationships from document chunks.
2. **Knowledge Graph Construction**: Entities and relationships are stored in a graph structure.
3. **Dual-Level Indexing**:
   - **Low-level**: Individual entities and their direct relationships (key-value pairs).
   - **High-level**: Communities of related entities and their collective summaries.
4. **Vector Indexing**: Entity and relationship descriptions are embedded and stored in a vector database.

### Query Phase

LightRAG supports four query modes:

- **Naive**: Simple vector similarity search (baseline).
- **Local**: Low-level retrieval focused on specific entities and their direct relationships.
- **Global**: High-level retrieval focused on community summaries and themes.
- **Hybrid**: Combines local and global retrieval for comprehensive results.
- **Mix** (recommended with reranker): Combines all modes with reranking for best results.

## Core API

```python
from lightrag import LightRAG, QueryParam

# Initialize
rag = LightRAG(
    working_dir="./workspace",
    llm_model_func=your_llm_func,
    embedding_func=your_embedding_func,
)

# Insert documents
rag.insert("Your document text here...")

# Query
result = rag.query("Your question here", mode="hybrid")

# With specific parameters
result = rag.query(
    "Your question here",
    param=QueryParam(mode="mix", only_need_context=False)
)
```

## Storage Backends

LightRAG supports multiple storage backends for its four storage types (KV, vector, graph, doc):

- **NanoVectorDB** (default): Built-in lightweight vector database.
- **Neo4J**: Graph database for knowledge graph storage.
- **PostgreSQL**: All-in-one storage solution.
- **MongoDB**: All-in-one storage solution.
- **OpenSearch**: Unified storage backend for all four storage types.

## Performance

LightRAG consistently outperforms NaiveRAG, RQ-RAG, HyDE, and GraphRAG across agriculture, computer science, legal, and mixed domains:

| System | Agriculture | CS | Legal | Mix |
|--------|-------------|-----|-------|-----|
| NaiveRAG | 32.4% | 38.8% | 15.2% | 40.0% |
| **LightRAG** | **67.6%** | **61.2%** | **84.8%** | **60.0%** |
| GraphRAG | 45.2% | 48.0% | 47.2% | 50.4% |
| **LightRAG** | **54.8%** | **52.0%** | **52.8%** | 49.6% |

## Advanced Features

- **Token Usage Tracking**: Monitor LLM and embedding token consumption.
- **Knowledge Graph Data Export**: Export graph data for analysis and visualization.
- **LLM Cache Management**: Cache LLM responses to reduce costs and latency.
- **Langfuse Observability**: Integration with Langfuse for tracing and debugging.
- **RAGAS-based Evaluation**: Evaluate RAG quality using RAGAS metrics.
- **Multimodal Document Processing**: Process PDFs, images, tables, and formulas via RAG-Anything integration.
- **Citation Functionality**: Proper source attribution and document traceability.
- **Document Deletion**: Remove documents with automatic knowledge graph regeneration.

## Related Projects

- **[RAG-Anything](https://github.com/HKUDS/RAG-Anything)**: All-in-One Multimodal RAG system.
- **[VideoRAG](https://github.com/HKUDS/VideoRAG)**: RAG for extremely long-context videos.
- **[MiniRAG](https://github.com/HKUDS/MiniRAG)**: Making RAG simpler with small models.

## Citation

```bibtex
@article{guo2024lightrag,
  title={LightRAG: Simple and Fast Retrieval-Augmented Generation},
  author={Zirui Guo and Lianghao Xia and Yanhua Yu and Tu Ao and Chao Huang},
  year={2024},
  eprint={2410.05779},
  archivePrefix={arXiv},
  primaryClass={cs.IR}
}
```
