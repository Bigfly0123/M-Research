"""
Tool Registry 单元测试: 注册、调用、list_tools、trace。
"""

import sys
import os
from unittest.mock import MagicMock

import types

def _make_mock_package(name):
    parts = name.split('.')
    for i in range(len(parts)):
        subname = '.'.join(parts[:i+1])
        if subname not in sys.modules:
            sys.modules[subname] = MagicMock()

for pkg in [
    "langchain_community.vectorstores",
    "langchain_community.document_loaders",
    "langchain_huggingface",
    "langchain_openai",
    "langgraph.graph",
    "rank_bm25",
    "sentence_transformers",
    "sentence_transformers.cross_encoder",
]:
    _make_mock_package(pkg)

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.tools.registry import ToolSpec, ToolResult, BaseTool, ToolRegistry


class DummyTool(BaseTool):
    spec = ToolSpec(name="dummy", description="A test tool", input_schema={"x": "int"}, output_schema={"result": "int"})

    def run(self, x: int = 0, **kwargs) -> dict:
        return {"result": x * 2}


class ErrorTool(BaseTool):
    spec = ToolSpec(name="error_tool", description="Always fails", input_schema={}, output_schema={})

    def run(self, **kwargs) -> dict:
        raise ValueError("intentional error")


def test_tool_spec_schema():
    spec = ToolSpec(name="test", description="desc")
    assert spec.name == "test"
    d = spec.model_dump()
    assert "input_schema" in d


def test_tool_result_schema():
    r = ToolResult(tool_name="test", ok=True, output={"a": 1}, latency_ms=10)
    assert r.ok is True
    assert r.latency_ms == 10


def test_base_tool_call():
    tool = DummyTool()
    result = tool(x=5)
    assert result.ok is True
    assert result.output["result"] == 10
    assert result.latency_ms >= 0


def test_base_tool_error():
    tool = ErrorTool()
    result = tool()
    assert result.ok is False
    assert result.error is not None


def test_registry_register_and_call():
    reg = ToolRegistry()
    reg.register(DummyTool())
    assert reg.has("dummy")
    result = reg.call("dummy", x=3)
    assert result.ok is True
    assert result.output["result"] == 6


def test_registry_call_unknown():
    reg = ToolRegistry()
    result = reg.call("nonexistent")
    assert result.ok is False
    assert "not found" in result.error


def test_registry_list_tools():
    reg = ToolRegistry()
    reg.register(DummyTool())
    reg.register(ErrorTool())
    specs = reg.list_tools()
    assert len(specs) == 2
    names = {s.name for s in specs}
    assert "dummy" in names
    assert "error_tool" in names


def test_registry_get():
    reg = ToolRegistry()
    reg.register(DummyTool())
    tool = reg.get("dummy")
    assert tool is not None
    assert reg.get("nonexistent") is None


def test_tool_spec_mcp_style():
    """验证 ToolSpec 遵循 MCP-style: name + description + input_schema + output_schema。"""
    spec = ToolSpec(
        name="dense_search",
        description="Semantic similarity search",
        input_schema={"query": "str", "top_k": "int"},
        output_schema={"chunks": "list[dict]"},
    )
    assert spec.name == "dense_search"
    assert len(spec.input_schema) > 0
    assert len(spec.output_schema) > 0


def run_all_tests():
    tests = [
        test_tool_spec_schema,
        test_tool_result_schema,
        test_base_tool_call,
        test_base_tool_error,
        test_registry_register_and_call,
        test_registry_call_unknown,
        test_registry_list_tools,
        test_registry_get,
        test_tool_spec_mcp_style,
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
    print("Running Tool Registry tests...")
    run_all_tests()
