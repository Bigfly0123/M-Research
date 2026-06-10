# 03｜Tool Registry 设计指导

> 项目定位：**DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统**。
> 目标不是普通 RAG 问答，而是围绕上下文规划、图增强检索、证据组合、自动评测、可追踪修复构建一个小而硬的高级项目。

## 1. 模块作用
Tool Registry 把 dense search、BM25 search、graph expansion、citation check、eval run 等能力封装成统一工具，避免 Agent 节点里到处硬编码函数调用。它是 MCP-style tool abstraction 的轻量版本。

## 2. 必须理解的知识点
- **Tool**：有 name、description、input_schema、output_schema 的可调用能力。
- **Registry**：统一注册和调用工具。
- **MCP 启发**：MCP tools 用 schema 描述外部能力；我们不实现完整 MCP server，但采用 schema-first 设计。
- **Tool vs Skill**：Tool 是执行能力；Skill 是 prompt/rubric/instruction。

## 3. 技术参考
- [MCP Tools Spec](https://modelcontextprotocol.io/specification/2025-11-25/server/tools)
- [OpenAI Agents SDK](https://developers.openai.com/api/docs/guides/agents)

## 4. 第一版工具清单
| 工具 | 作用 |
|---|---|
| dense_search | 向量检索 |
| bm25_search | 关键词检索 |
| graph_expand | term graph 扩展 |
| rerank | 候选 chunk 重排，可选 |
| citation_check | 引用合法性检查 |
| eval_run | 执行评测 |

## 5. 接口设计
```python
class ToolSpec(BaseModel):
    name: str
    description: str
    input_schema: dict
    output_schema: dict

class ToolResult(BaseModel):
    tool_name: str
    ok: bool
    output: dict
    error: str | None = None
    latency_ms: int = 0
```

## 6. 实施步骤
1. 定义 BaseTool。
2. 定义 ToolRegistry。
3. 把 dense_search / bm25_search / graph_expand 封装成工具。
4. Hybrid Retriever 通过 registry.call 调用。
5. 每次工具调用写入 trace。

## 7. 验收标准
- 每个工具有 schema。
- 工具调用失败不会导致系统崩溃。
- trace 记录 tool_name、input summary、output_count、latency。
- 新增工具不需要大改主流程。

## 8. 常见坑
- 一个工具做太多事情。
- 没有 schema，后续难以接 MCP。
- 工具异常直接抛出，破坏 Agent workflow。
- 不记录耗时，eval 无法分析性能。
