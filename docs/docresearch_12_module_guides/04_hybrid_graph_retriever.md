# 04｜Hybrid + Graph Retriever 设计指导

> 项目定位：**DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统**。
> 目标不是普通 RAG 问答，而是围绕上下文规划、图增强检索、证据组合、自动评测、可追踪修复构建一个小而硬的高级项目。

## 1. 模块作用
这是项目最重要的“高级检索层”。目标是同时利用 dense semantic search、BM25 keyword search 和 lightweight graph expansion，解决技术术语精准匹配、多跳概念关联和普通向量检索召回不稳定的问题。

## 2. 必须理解的知识点
- **Dense Retrieval**：语义相似，适合概念解释。
- **BM25**：关键词匹配，适合函数名、参数名、缩写、模块名。
- **Hybrid Search**：融合 dense 和 BM25。
- **Lightweight Graph Retrieval**：从 chunk 抽取 technical terms，建立 term->chunk 和 term->related_term。
- **LightRAG / HippoRAG 2 启发**：图结构和关联记忆能弥补 flat chunks 的不足。

## 3. 技术参考
- [LangChain BM25 Retriever](https://docs.langchain.com/oss/python/integrations/retrievers/bm25)
- [LightRAG](https://arxiv.org/abs/2410.05779)
- [HippoRAG 2](https://openreview.net/forum?id=LWH8yn4HS2)

## 4. 输入输出
输出 RetrievedChunk：
```python
class RetrievedChunk(BaseModel):
    chunk_id: str
    text: str
    source: str
    section_path: list[str]
    retrieval_sources: list[str]
    dense_score: float | None = None
    bm25_score: float | None = None
    graph_score: float | None = None
    final_score: float
    metadata: dict
```

## 5. 设计方案
检索流程：
```text
dense top-20
bm25 top-20
graph top-20
   ↓
merge by chunk_id
   ↓
score normalization
   ↓
score fusion
   ↓
top-k evidence candidates
```

## 6. Graph Index 轻量实现
```python
term_to_chunks: dict[str, set[str]]
chunk_to_terms: dict[str, set[str]]
term_graph: dict[str, set[str]]
```
抽取术语可以先用规则：驼峰词、下划线词、大写缩写、高频技术词。

## 7. 分数融合
第一版用：
```python
final_score = 0.45*dense_norm + 0.35*bm25_norm + 0.20*graph_norm
```
如果一个 chunk 同时被多个 retriever 命中，可以加 bonus。

## 8. 实施步骤
1. 实现 dense retriever。
2. 实现 BM25 retriever。
3. 实现 technical term extraction。
4. 建 term graph。
5. 实现 one-hop graph expansion。
6. 合并、去重、分数融合。
7. 写 retrieval trace。

## 9. 验收标准
- dense/BM25/graph 三种来源都能出结果。
- 每个结果记录 retrieval_sources。
- 多跳问题能通过 graph 找到额外相关 chunk。
- eval 能对比 vector baseline 与 hybrid+graph。

## 10. 常见坑
- graph expansion 扩太远，引入噪声。
- dense 和 BM25 分数没归一化。
- 术语抽取过度复杂，影响进度。
- graph 结果没有证据文本，无法引用。
