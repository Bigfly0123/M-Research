"""
用 FAISS 后端重建所有数据集索引。
"""

import json
import sys
import os
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ["DENSE_BACKEND"] = "faiss"

import platform as _p

_c = _p.platform()
_p.platform = lambda *a, **kw: _c

from app.retrieval.hybrid_retriever import HybridGraphRetriever

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_jsonl(path: Path):
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def rebuild(dataset_name: str, chunks_path: str, index_dir: str):
    print(f"\n{'=' * 60}\n重建 {dataset_name} 索引 (FAISS)")
    chunks = load_jsonl(PROJECT_ROOT / chunks_path)
    # 确保 source_path
    for c in chunks:
        if "source_path" not in c or not c["source_path"]:
            c["source_path"] = c.get("doc_id", "")
    print(f"  {len(chunks)} chunks")

    t0 = time.time()
    retriever = HybridGraphRetriever()
    retriever.build_index(chunks, index_dir=str(PROJECT_ROOT / index_dir))
    print(f"  完成: {time.time() - t0:.1f}s")


def main():
    rebuild(
        "MultiHop-RAG",
        "data/processed/multihop_rag/chunks.jsonl",
        "data/indexes/multihop_rag",
    )
    rebuild(
        "TechDocQA", "data/processed/techdocqa/chunks.jsonl", "data/indexes/techdocqa"
    )


if __name__ == "__main__":
    main()
