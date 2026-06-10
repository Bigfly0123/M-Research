"""
Step3: Structure-aware Chunking — 读取 corpus_docs.jsonl，按 Markdown ## 标题分 section，
每个 section 内按 512 token 切 chunk，输出 chunks.jsonl。
"""
import json
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed" / "techdocqa"
CORPUS_PATH = PROCESSED_DIR / "corpus_docs.jsonl"
CHUNKS_PATH = PROCESSED_DIR / "chunks.jsonl"

CHUNK_TOKEN_LIMIT = 512
APPROX_CHARS_PER_TOKEN = 4


def estimate_tokens(text: str) -> int:
    return max(1, len(text) // APPROX_CHARS_PER_TOKEN)


def detect_element_type(text: str) -> str:
    if re.search(r"```\w*", text) or re.search(r"`\S+`", text):
        return "code"
    if "|" in text and re.search(r"\|.*\|.*\|", text):
        return "table"
    return "text"


def split_sections(text: str):
    """按 ## 标题切分 section，返回 [(section_title, section_text), ...]"""
    lines = text.split("\n")
    sections = []
    current_title = "(header)"
    current_lines = []

    for line in lines:
        if re.match(r"^##\s+", line):
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = re.sub(r"^##\s+", "", line).strip()
            current_lines = [line]
        else:
            current_lines.append(line)

    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))

    return sections


def chunk_section(section_text: str, token_limit: int):
    """在 section 内按 token limit 切 chunk，返回 [chunk_text, ...]"""
    tokens = estimate_tokens(section_text)
    if tokens <= token_limit:
        return [section_text]

    char_limit = token_limit * APPROX_CHARS_PER_TOKEN
    chunks = []
    remaining = section_text
    while remaining:
        if len(remaining) <= char_limit:
            chunks.append(remaining)
            break
        cut = remaining[:char_limit]
        last_nl = cut.rfind("\n")
        if last_nl > char_limit // 2:
            chunks.append(remaining[:last_nl])
            remaining = remaining[last_nl:].lstrip("\n")
        else:
            chunks.append(cut)
            remaining = remaining[char_limit:]
    return chunks


def build_section_path(doc_title: str, section_title: str) -> list:
    path = [doc_title]
    if section_title and section_title != "(header)":
        path.append(section_title)
    return path


def build_contextual_header(doc_title: str, section_title: str) -> str:
    if section_title and section_title != "(header)":
        return f"This chunk comes from {doc_title} Documentation, section {section_title}."
    return f"This chunk comes from {doc_title} Documentation."


def main():
    print("=" * 80)
    print("Step3: Structure-aware Chunking")

    docs = []
    with CORPUS_PATH.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                docs.append(json.loads(line))
    print(f"加载 {len(docs)} 篇文档")

    all_chunks = []
    for doc in docs:
        doc_id = doc["doc_id"]
        title = doc["title"]
        text = doc["text"]

        sections = split_sections(text)
        doc_chunks = []

        for sec_idx, (sec_title, sec_text) in enumerate(sections):
            if not sec_text.strip():
                continue
            sec_chunks = chunk_section(sec_text, CHUNK_TOKEN_LIMIT)
            for chunk_idx, chunk_text in enumerate(sec_chunks):
                chunk_id = f"{doc_id}-s{sec_idx + 1:02d}-c{chunk_idx:03d}"
                element_type = detect_element_type(chunk_text)
                section_path = build_section_path(title, sec_title)
                contextual_header = build_contextual_header(title, sec_title)
                token_count = estimate_tokens(chunk_text)

                chunk = {
                    "chunk_id": chunk_id,
                    "doc_id": doc_id,
                    "source_dataset": "TechDocQA",
                    "title": title,
                    "section": sec_title,
                    "section_path": section_path,
                    "element_type": element_type,
                    "text": chunk_text.strip(),
                    "contextual_header": contextual_header,
                    "index_text": contextual_header + " Original: " + chunk_text.strip(),
                    "metadata": {
                        "source_path": doc.get("source_path", ""),
                        "source_url": doc.get("source_url", ""),
                        "chunk_index": chunk_idx,
                        "token_count": token_count,
                    },
                }
                doc_chunks.append(chunk)

        all_chunks.extend(doc_chunks)
        print(f"  {doc_id}: {len(sections)} sections -> {len(doc_chunks)} chunks")

    with CHUNKS_PATH.open("w", encoding="utf-8") as f:
        for chunk in all_chunks:
            f.write(json.dumps(chunk, ensure_ascii=False) + "\n")
    print(f"\n写入 {len(all_chunks)} 条 -> {CHUNKS_PATH}")
    print("Step3 完成。")


if __name__ == "__main__":
    main()
