"""
Tool Registry: MCP-style 工具注册与调用中心。
"""

from typing import Any, Callable, Optional
from pydantic import BaseModel
import time


class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict = {}
    output_schema: dict = {}


class ToolResult(BaseModel):
    tool_name: str
    ok: bool = True
    output: dict = {}
    error: Optional[str] = None
    latency_ms: int = 0


class BaseTool:
    spec: ToolSpec

    def run(self, **kwargs) -> dict:
        raise NotImplementedError

    def __call__(self, **kwargs) -> ToolResult:
        start = time.time()
        try:
            output = self.run(**kwargs)
            latency = int((time.time() - start) * 1000)
            return ToolResult(tool_name=self.spec.name, ok=True, output=output, latency_ms=latency)
        except Exception as e:
            latency = int((time.time() - start) * 1000)
            return ToolResult(tool_name=self.spec.name, ok=False, error=str(e), latency_ms=latency)


class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        self._tools[tool.spec.name] = tool

    def get(self, name: str) -> Optional[BaseTool]:
        return self._tools.get(name)

    def call(self, name: str, **kwargs) -> ToolResult:
        tool = self.get(name)
        if tool is None:
            return ToolResult(tool_name=name, ok=False, error=f"Tool '{name}' not found")
        return tool(**kwargs)

    def list_tools(self) -> list[ToolSpec]:
        return [t.spec for t in self._tools.values()]

    def has(self, name: str) -> bool:
        return name in self._tools


registry = ToolRegistry()
