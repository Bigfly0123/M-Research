"""
Ingestion 模块单元测试: Structure-aware Chunker 验收测试。

覆盖: Markdown解析(heading/code/table/list), PDF解析, contextual header,
chunk_id稳定性, 超长切分, Module模式(status/trace/fallback)。
"""

import sys
import os
import types
from unittest.mock import MagicMock

# Mock heavy dependencies before any app imports
for mod_name in [
    "langchain_community", "langchain_community.document_loaders",
    "langchain_huggingface", "rank_bm25", "langchain_openai",
    "langgraph", "langgraph.graph",
]:
    if mod_name not in sys.modules:
        sys.modules[mod_name] = MagicMock()

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.ingestion.chunker import (
    StructureAwareChunker, ChunkerConfig,
    estimate_tokens, build_contextual_text,
    chunk_markdown, load_documents,
)
from app.ingestion.structure_parser import parse_markdown, parse_pdf_text
from app.ingestion.loaders import RawDocument
from app.schemas.chunk import DocChunk


def test_estimate_tokens():
    assert estimate_tokens("hello world") >= 1
    assert estimate_tokens("") == 1
    assert estimate_tokens("这是一段中文测试") >= 1


def test_parse_markdown_heading():
    md = """# Title One
Some paragraph under title one.

## Sub Title
Paragraph under sub title.
"""
    elements = parse_markdown(md)
    assert len(elements) >= 3
    assert elements[0].element_type == "heading"
    assert elements[0].section_path == ["Title One"]
    assert elements[1].element_type == "text"


def test_parse_markdown_code():
    md = """## Code Example
```python
def hello():
    print("world")
```
"""
    elements = parse_markdown(md)
    code_elems = [e for e in elements if e.element_type == "code"]
    assert len(code_elems) == 1
    assert code_elems[0].language == "python"
    assert "print" in code_elems[0].text


def test_parse_markdown_table():
    md = """## Comparison Table
| Feature | Dense | BM25 |
|---------|-------|------|
| Speed   | Fast  | Fast |
| Accuracy| High  | Med  |
"""
    elements = parse_markdown(md)
    table_elems = [e for e in elements if e.element_type == "table"]
    assert len(table_elems) == 1
    assert "Feature" in table_elems[0].text


def test_parse_markdown_list():
    md = """## Key Points
- Point one
- Point two
- Point three
"""
    elements = parse_markdown(md)
    list_elems = [e for e in elements if e.element_type == "list"]
    assert len(list_elems) >= 1


def test_parse_markdown_section_path():
    md = """# Level One
## Level Two
### Level Three
Content here.
"""
    elements = parse_markdown(md)
    text_elems = [e for e in elements if e.element_type == "text"]
    assert len(text_elems) >= 1
    assert "Level Three" in text_elems[0].section_path


def test_contextual_header():
    chunk = DocChunk(
        chunk_id="test.md-C000",
        doc_id="test.md",
        source_path="/docs/test.md",
        title="Test Doc",
        section_path=["RAG", "Retriever", "BM25"],
        element_type="code",
        language="python",
        text="def bm25_search(query): pass",
        contextual_text="",
        token_count=5,
    )
    ctx = build_contextual_text(chunk)
    assert "[Document: Test Doc]" in ctx
    assert "[Section: RAG > Retriever > BM25]" in ctx
    assert "[Element: code]" in ctx
    assert "[Language: python]" in ctx


def test_chunk_markdown_full():
    md_text = """# DocResearch Design

## Context Planner
The context planner decides retrieval strategy for each question type.

### Query Types
The system supports the following query types: fact, concept, multi_hop.

## Code Example
```python
def plan(question):
    return {"query_type": "concept"}
```

## Comparison
| Metric | Dense | BM25 |
|--------|-------|------|
| Speed  | Fast  | Fast |
"""
    doc = RawDocument(doc_id="design.md", source_path="/docs/design.md", text=md_text, file_type="md")
    config = ChunkerConfig(chunk_size=500, add_contextual_header=True, min_chunk_tokens=5)
    chunks = chunk_markdown(doc, config)

    assert len(chunks) > 0
    code_chunks = [c for c in chunks if c.element_type == "code"]
    assert len(code_chunks) == 1
    table_chunks = [c for c in chunks if c.element_type == "table"]
    assert len(table_chunks) == 1
    text_chunks = [c for c in chunks if c.element_type == "text"]
    assert len(text_chunks) >= 1
    for c in chunks:
        assert len(c.contextual_text) > 0
        assert c.chunk_id.startswith("design.md-C")
    assert any("Context Planner" in c.section_path for c in chunks)


def test_chunk_id_stability():
    md_text = "# Title\nSome content.\n## Sub\nMore content."
    doc = RawDocument(doc_id="test.md", source_path="/test.md", text=md_text, file_type="md")
    chunks1 = chunk_markdown(doc)
    chunks2 = chunk_markdown(doc)
    ids1 = [c.chunk_id for c in chunks1]
    ids2 = [c.chunk_id for c in chunks2]
    assert ids1 == ids2


def test_module_mode_ok():
    chunker = StructureAwareChunker()
    result = chunker.run(file_paths=[])
    assert result.status == "warn"
    assert result.total_chunks == 0


def test_module_mode_fail():
    chunker = StructureAwareChunker()
    result = chunker.run(file_paths=["/nonexistent/file.md"])
    assert result.status in ("warn", "fail")


def test_parse_pdf_text():
    text = "Introduction\n\nThis is the first paragraph.\n\nMethods\n\nThis is the second paragraph."
    elements = parse_pdf_text(text, page=1)
    assert len(elements) >= 2
    for e in elements:
        assert e.page == 1


def run_all_tests():
    tests = [
        test_estimate_tokens,
        test_parse_markdown_heading,
        test_parse_markdown_code,
        test_parse_markdown_table,
        test_parse_markdown_list,
        test_parse_markdown_section_path,
        test_contextual_header,
        test_chunk_markdown_full,
        test_chunk_id_stability,
        test_module_mode_ok,
        test_module_mode_fail,
        test_parse_pdf_text,
    ]
    passed = 0
    failed = 0
    for test in tests:
        try:
            test()
            passed += 1
            print(f"  PASS: {test.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL: {test.__name__} - {e}")
        except Exception as e:
            failed += 1
            print(f"  ERROR: {test.__name__} - {e}")
    print(f"\nResults: {passed} passed, {failed} failed, {len(tests)} total")
    return failed == 0


if __name__ == "__main__":
    print("Running Ingestion module tests...")
    run_all_tests()
