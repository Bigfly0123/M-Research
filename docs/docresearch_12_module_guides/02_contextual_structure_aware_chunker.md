# 02｜Contextual / Structure-aware Chunker 设计指导

> 项目定位：**DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统**。
> 目标不是普通 RAG 问答，而是围绕上下文规划、图增强检索、证据组合、自动评测、可追踪修复构建一个小而硬的高级项目。

## 1. 模块作用
这个模块负责把 PDF / Markdown / 技术文档拆成可检索、可引用、可追踪的结构化 chunk。高级点在于：不是按固定长度粗暴切文本，而是保留标题层级、页码、代码块、表格、section path、element_type，并为 chunk 补充 contextual header。

## 2. 必须理解的知识点
- **Raw Chunk**：原始文本片段。
- **Contextual Chunk**：在 raw_text 前加入文档标题、章节路径、元素类型等上下文。
- **Structure-aware Chunk**：chunk metadata 中保存 `source/page/section/element_type/language`。
- **技术文档结构**：代码块和表格不能随便和普通段落混合。

## 3. 技术参考
- [Anthropic Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)

## 4. 数据结构
```python
class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    source_path: str
    title: str | None
    section_path: list[str]
    page: int | None
    element_type: Literal['heading','paragraph','code_block','table','list']
    language: str | None = None
    raw_text: str
    contextual_text: str
    token_count: int
    metadata: dict = {}
```

## 5. 设计方案
- Markdown：识别 heading、paragraph、code block、table。
- PDF：第一版保留 page + text，后续再增强表格和图片。
- contextual_text 格式：
```text
[Document] xxx
[Source] docs/a.md
[Section] RAG > Retriever > BM25
[ElementType] code_block

原始文本...
```

## 6. 实施步骤
1. 写 Markdown block parser。
2. 维护 section_stack。
3. 按 element_type 生成 chunk。
4. 生成 contextual_text。
5. 向 vector/BM25 index 写入 contextual_text。
6. 展示引用时显示 raw_text 和 metadata。

## 7. 伪代码
```python
def build_contextual_text(chunk):
    header = [
        f'[Document] {chunk.title}',
        f'[Source] {chunk.source_path}',
        f'[Section] {" > ".join(chunk.section_path)}',
        f'[ElementType] {chunk.element_type}'
    ]
    return '
'.join(header) + '

' + chunk.raw_text
```

## 8. 验收标准
- 每个 chunk 有稳定 chunk_id。
- Markdown 标题进入 section_path。
- 代码块 element_type=code_block。
- PDF 至少有 page。
- 检索结果能显示 source/section/page。
- 引用能追溯到 chunk。

## 9. 常见坑
- 只存纯文本，不存 metadata。
- chunk 太小导致上下文丢失。
- code block 被切碎。
- citation_id 不稳定，eval 无法复现。
