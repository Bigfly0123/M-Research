---
title: RAGFlow README
source_url: https://raw.githubusercontent.com/infiniflow/ragflow/main/README.md
source_type: readme
topic: ragflow
collected_at: 2026-05-18
---

# RAGFlow

RAGFlow is a leading open-source Retrieval-Augmented Generation (RAG) engine that fuses cutting-edge RAG with Agent capabilities to create a superior context layer for LLMs. It offers a streamlined RAG workflow adaptable to enterprises of any scale. Powered by a converged context engine and pre-built agent templates, RAGFlow enables developers to transform complex data into high-fidelity, production-ready AI systems with exceptional efficiency and precision.

## Latest Updates

- 2026-04-24: Supports DeepSeek v4.
- 2026-03-24: RAGFlow Skill on OpenClaw — Provides an official skill for accessing RAGFlow datasets via OpenClaw.
- 2025-12-26: Supports 'Memory' for AI agent.
- 2025-11-19: Supports Gemini 3 Pro.
- 2025-11-12: Supports data synchronization from Confluence, S3, Notion, Discord, Google Drive.
- 2025-10-23: Supports MinerU & Docling as document parsing methods.
- 2025-10-15: Supports orchestrable ingestion pipeline.
- 2025-08-08: Supports OpenAI's latest GPT-5 series models.
- 2025-08-01: Supports agentic workflow and MCP.
- 2025-05-23: Adds a Python/JavaScript code executor component to Agent.
- 2025-05-05: Supports cross-language query.
- 2025-03-19: Supports using a multi-modal model to make sense of images within PDF or DOCX files.

## Key Features

### "Quality in, quality out"

- Deep document understanding-based knowledge extraction from unstructured data with complicated formats.
- Finds "needle in a data haystack" of literally unlimited tokens.

### Template-based chunking

- Intelligent and explainable.
- Plenty of template options to choose from.

### Grounded citations with reduced hallucinations

- Visualization of text chunking to allow human intervention.
- Quick view of the key references and traceable citations to support grounded answers.

### Compatibility with heterogeneous data sources

- Supports Word, slides, excel, txt, images, scanned copies, structured data, web pages, and more.

### Automated and effortless RAG workflow

- Streamlined RAG orchestration catered to both personal and large businesses.
- Configurable LLMs as well as embedding models.
- Multiple recall paired with fused re-ranking.
- Intuitive APIs for seamless integration with business.

## System Architecture

RAGFlow follows a modular architecture with the following core components:

- **DeepDoc**: Document understanding and parsing engine that handles complex document formats.
- **Task Executor**: Distributed task processing for document ingestion and chunking.
- **API Server**: RESTful API for integration with external systems.
- **Web UI**: Browser-based interface for knowledge base management.
- **Agent Framework**: Built-in agent capabilities with workflow support.

The system relies on the following infrastructure services:

- **Elasticsearch / Infinity**: Full-text search and vector storage engine.
- **MinIO**: Object storage for document files.
- **Redis**: Caching and message broker.
- **MySQL**: Metadata and configuration storage.

## Self-Hosting

### Prerequisites

- CPU >= 4 cores
- RAM >= 16 GB
- Disk >= 50 GB
- Docker >= 24.0.0 & Docker Compose >= v2.26.1
- gVisor: Required only if you intend to use the code executor (sandbox) feature.

### Start up the server

1. Ensure `vm.max_map_count` >= 262144:

```bash
$ sysctl vm.max_map_count
# If not, reset it:
$ sudo sysctl -w vm.max_map_count=262144
```

2. Clone the repo:

```bash
$ git clone https://github.com/infiniflow/ragflow.git
```

3. Start up the server using the pre-built Docker images:

```bash
$ cd ragflow/docker

# Use CPU for DeepDoc tasks:
$ docker compose -f docker-compose.yml up -d

# To use GPU to accelerate DeepDoc tasks:
# sed -i '1i DEVICE=gpu' .env
# docker compose -f docker-compose.yml up -d
```

4. Check the server status:

```bash
$ docker logs -f docker-ragflow-cpu-1
```

5. In your web browser, enter the IP address of your server and log in to RAGFlow.

6. In `service_conf.yaml.template`, select the desired LLM factory in `user_default_llm` and update the `API_KEY` field.

## Configurations

Key configuration files:

- **.env**: Keeps fundamental setups like `SVR_HTTP_PORT`, `MYSQL_PASSWORD`, and `MINIO_PASSWORD`.
- **service_conf.yaml.template**: Configures back-end services. Environment variables are automatically populated when the Docker container starts.
- **docker-compose.yml**: The system relies on this to start up.

To update the default HTTP serving port (80), go to `docker-compose.yml` and change `80:80` to `<YOUR_SERVING_PORT>:80`.

### Switch doc engine from Elasticsearch to Infinity

RAGFlow uses Elasticsearch by default for storing full text and vectors. To switch to Infinity:

1. Stop all running containers:
```bash
$ docker compose -f docker/docker-compose.yml down -v
```

2. Set `DOC_ENGINE` in **docker/.env** to `infinity`.

3. Start the containers:
```bash
$ docker compose -f docker-compose.yml up -d
```

## Build a Docker image

This image is approximately 2 GB in size and relies on external LLM and embedding services.

```bash
git clone https://github.com/infiniflow/ragflow.git
cd ragflow/
docker build --platform linux/amd64 -f Dockerfile -t infiniflow/ragflow:nightly .
```

## Launch Service from Source for Development

1. Install `uv` and `pre-commit`:
```bash
pipx install uv pre-commit
```

2. Clone the source code and install Python dependencies:
```bash
git clone https://github.com/infiniflow/ragflow.git
cd ragflow/
uv sync --python 3.12
uv run python3 download_deps.py
pre-commit install
```

3. Launch the dependent services (MinIO, Elasticsearch, Redis, MySQL) using Docker Compose:
```bash
docker compose -f docker/docker-compose-base.yml up -d
```

4. Add the following line to `/etc/hosts`:
```
127.0.0.1       es01 infinity mysql minio redis sandbox-executor-manager
```

5. Launch backend service:
```bash
source .venv/bin/activate
export PYTHONPATH=$(pwd)
bash docker/launch_backend_service.sh
```

6. Install frontend dependencies and launch:
```bash
cd web
npm install
npm run dev
```

## Documentation

- [Quickstart](https://ragflow.io/docs/dev/)
- [Configuration](https://ragflow.io/docs/dev/configurations)
- [Release notes](https://ragflow.io/docs/dev/release_notes)
- [User guides](https://ragflow.io/docs/category/user-guides)
- [Developer guides](https://ragflow.io/docs/category/developer-guides)
- [References](https://ragflow.io/docs/dev/category/references)
- [FAQs](https://ragflow.io/docs/dev/faq)

## Roadmap

See the [RAGFlow Roadmap 2026](https://github.com/infiniflow/ragflow/issues/12241)

## Community

- [Discord](https://discord.gg/NjYzJD3GM3)
- [X](https://x.com/infiniflowai)
- [GitHub Discussions](https://github.com/orgs/infiniflow/discussions)

## Contributing

RAGFlow flourishes via open-source collaboration. Review the [Contribution Guidelines](https://ragflow.io/docs/dev/contributing) first.
