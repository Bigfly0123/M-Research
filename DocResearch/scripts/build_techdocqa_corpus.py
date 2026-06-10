"""
Step2: 读取 data/raw/techdocqa/ 下所有 .md 文件，转换为 corpus_docs.jsonl。
"""
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw" / "techdocqa"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "techdocqa"

DOC_ID_MAP = {
    "langgraph/stategraph.md": "langgraph_001",
    "langgraph/agentic_rag.md": "langgraph_002",
    "openai_agents/tools_guardrails.md": "openai_agents_001",
    "mcp/tools_spec.md": "mcp_001",
    "anthropic_context/context_engineering.md": "anthropic_context_001",
    "ragflow/readme.md": "ragflow_001",
    "lightrag/readme.md": "lightrag_001",
    "ragas/metrics.md": "ragas_001",
    "deepeval/metrics_intro.md": "deepeval_001",
}


def parse_frontmatter(text: str):
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.DOTALL)
    if not m:
        return {}, text
    fm_text = m.group(1)
    body = text[m.end():]
    fm = {}
    for line in fm_text.splitlines():
        line = line.strip()
        if ":" in line:
            key, val = line.split(":", 1)
            fm[key.strip()] = val.strip().strip('"').strip("'")
    return fm, body


def main():
    print("=" * 80)
    print("Step2: 构建 TechDocQA corpus_docs.jsonl")

    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

    md_files = sorted(RAW_DIR.rglob("*.md"))
    print(f"找到 {len(md_files)} 个 .md 文件")

    corpus_docs = []
    for md_path in md_files:
        rel_path = md_path.relative_to(RAW_DIR).as_posix()
        doc_id = DOC_ID_MAP.get(rel_path)
        if not doc_id:
            print(f"  警告: 无 doc_id 映射，跳过 {rel_path}")
            continue

        text_raw = md_path.read_text(encoding="utf-8")
        fm, body = parse_frontmatter(text_raw)

        corpus_doc = {
            "doc_id": doc_id,
            "source_dataset": "TechDocQA",
            "title": fm.get("title", ""),
            "source_path": rel_path,
            "source_url": fm.get("source_url", ""),
            "topic": fm.get("topic", ""),
            "text": body.strip(),
            "metadata": {
                "source_type": fm.get("source_type", ""),
                "collected_at": fm.get("collected_at", ""),
            },
        }
        corpus_docs.append(corpus_doc)
        print(f"  {doc_id} <- {rel_path} (title={corpus_doc['title'][:50]})")

    out_path = PROCESSED_DIR / "corpus_docs.jsonl"
    with out_path.open("w", encoding="utf-8") as f:
        for doc in corpus_docs:
            f.write(json.dumps(doc, ensure_ascii=False) + "\n")
    print(f"\n写入 {len(corpus_docs)} 条 -> {out_path}")
    print("Step2 完成。")


if __name__ == "__main__":
    main()
