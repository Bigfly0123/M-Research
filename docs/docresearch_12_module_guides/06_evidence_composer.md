# 06｜Evidence Composer 设计指导

> 项目定位：**DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统**。
> 目标不是普通 RAG 问答，而是围绕上下文规划、图增强检索、证据组合、自动评测、可追踪修复构建一个小而硬的高级项目。

## 1. 模块作用
Evidence Composer 把检索候选 chunk 组织成可给 LLM 使用的 context_pack。它不是简单选择 top-k，而是去重、压缩、排序、标注证据角色、生成 citation_id，并控制 context budget。

## 2. 必须理解的知识点
- **Context Pack**：最终送入 Answer Generator 的证据包。
- **Evidence Role**：definition、mechanism、example、limitation、code_reference。
- **Context Compression**：保留与问题相关的证据句，减少噪声。
- **Citation ID**：稳定引用标识，例如 D1-C12。

## 3. 技术参考
- [Anthropic Context Engineering](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Ragas Metrics](https://docs.ragas.io/en/v0.1.21/concepts/metrics/)

## 4. 输出示例
```json
{
  "context_pack": [
    {
      "citation_id": "D1-C12",
      "chunk_id": "chunk_12",
      "source": "design.md",
      "section": "Hybrid + Graph Retriever",
      "compressed_text": "...",
      "supporting_role": "mechanism"
    }
  ],
  "dropped_chunks": [{"chunk_id": "chunk_18", "reason": "duplicate"}],
  "total_context_tokens": 2850
}
```

## 5. 设计方案
1. 按 chunk_id 去重。
2. 按 final_score + source diversity 排序。
3. 给每条证据分配 supporting_role。
4. 超长 chunk 做 query-focused compression。
5. 控制总 token 不超过 context_plan.context_budget。
6. 生成稳定 citation_id。

## 6. 实施步骤
- Step 1：deduplicate。
- Step 2：classify_role。
- Step 3：compress_chunk。
- Step 4：make_citation_id。
- Step 5：compose_context_pack。
- Step 6：记录 dropped_chunks。

## 7. 验收标准
- 每条 evidence 有 citation_id。
- total_context_tokens 不超过预算。
- dropped_chunks 有原因。
- Answer Generator 只能引用 context_pack 中的 citation_id。
- trace 记录 evidence composition 过程。

## 8. 常见坑
- 只按分数取 top-k，证据重复。
- 压缩时删掉关键证据。
- citation_id 不稳定。
- 不记录 dropped reason，无法 debug。
