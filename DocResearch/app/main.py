"""
FastAPI 入口: DocResearch-Agent 2026 后端服务。

提供 POST /upload, POST /chat, GET / 三个 API。
"""

import os
import json
import time
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

from app.graph import create_graph, retriever
from app.ingestion.chunker import StructureAwareChunker, ChunkerConfig
from app.state import AgentState
from app.config import config

app = FastAPI(title=config.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    question: str
    thread_id: str = "default"


@app.post("/upload")
async def upload_files(files: List[UploadFile] = File(...)):
    """上传文档，解析切块，构建 Dense + BM25 + Graph 三路索引。"""
    saved = []
    for f in files:
        path = os.path.join(config.RAW_DOCS_DIR, f.filename)
        os.makedirs(config.RAW_DOCS_DIR, exist_ok=True)
        with open(path, "wb") as buf:
            buf.write(await f.read())
        saved.append(path)

    chunker = StructureAwareChunker(ChunkerConfig())
    result = chunker.run(saved)
    if result.status == "fail" or not result.chunks:
        raise HTTPException(status_code=400, detail=f"No valid documents loaded: {result.trace}")

    chunk_dicts = [c.model_dump() for c in result.chunks]
    retriever.build_index(chunk_dicts, index_dir=config.INDEX_DIR)

    return {
        "status": result.status,
        "chunks": result.total_chunks,
        "total_tokens": result.total_tokens,
        "sources": result.sources,
        "element_types": result.trace.get("element_types", {}),
    }


@app.post("/chat")
async def chat(request: ChatRequest):
    """SSE 流式问答: 完整工作流闭环。"""
    async def event_generator():
        graph = create_graph()

        initial: AgentState = {
            "question": request.question,
            "context_plan": {},
            "query_type": "",
            "retrieval_plan": [],
            "context_budget": config.DEFAULT_CONTEXT_BUDGET,
            "rewrite_query": "",
            "retrieved_chunks": [],
            "retrieval_sources": [],
            "retrieval_eval": {},
            "context_pack": [],
            "dropped_chunks": [],
            "total_context_tokens": 0,
            "answer": "",
            "used_citations": [],
            "unsupported_claims": [],
            "answer_confidence": "",
            "guardrail_result": {},
            "guardrail_pass": True,
            "judge_result": {},
            "failure_type": "",
            "repair_action": "",
            "repair_count": 0,
            "max_repair_count": config.MAX_REPAIR_COUNT,
            "repair_history": [],
            "trace": [],
            "latency_ms": 0.0,
            "context_tokens": 0.0,
            "total_tokens": 0.0,
        }

        async for event in graph.astream(initial):
            for node_name, state_update in event.items():
                data = json.dumps({"step": node_name, "data": state_update}, ensure_ascii=False)
                yield f"data: {data}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/")
def health():
    return {"status": "running", "project": config.PROJECT_NAME}
