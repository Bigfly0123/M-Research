# 07｜Grounded Answer Generator 设计指导

> 项目定位：**DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统**。
> 目标不是普通 RAG 问答，而是围绕上下文规划、图增强检索、证据组合、自动评测、可追踪修复构建一个小而硬的高级项目。

## 1. 模块作用
Grounded Answer Generator 只基于 Evidence Composer 提供的 context_pack 生成答案。它必须带引用，并在证据不足时明确说明不足，不能使用外部知识补全。

## 2. 必须理解的知识点
- **Grounded Generation**：答案所有关键 claim 都被证据支持。
- **Claim-level Citation**：每个关键结论尽量跟 citation_id。
- **Unsupported Claims**：无法由证据支持的内容要标记，而不是强答。

## 3. 技术参考
- [Ragas Faithfulness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)
- [OpenAI Guardrails](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals)

## 4. 输入输出
```json
{
  "answer": "Evidence Composer compresses and organizes retrieved chunks into a citation-ready context pack [D1-C12].",
  "used_citations": ["D1-C12"],
  "unsupported_claims": [],
  "answer_confidence": "medium"
}
```

## 5. Prompt 关键规则
```text
1. Use ONLY the evidence pack.
2. Every important claim must include citation ids like [D1-C03].
3. If evidence is insufficient, say what is missing.
4. Do not use outside knowledge.
5. Return JSON only.
```

## 6. 实施步骤
1. 格式化 context_pack。
2. 调用 LLM 生成 JSON。
3. 解析 used_citations。
4. 检查 used_citations 是否存在于 context_pack。
5. 将结果交给 Citation Guardrails。

## 7. 验收标准
- 答案包含 citation_id。
- used_citations 都来自 context_pack。
- 证据不足时不强答。
- 输出 JSON 可解析。
- trace 记录 answer_confidence 和 used_citations。

## 8. 常见坑
- prompt 没限制外部知识。
- 引用全堆在段尾，不支持具体 claim。
- 未引用的关键判断太多。
- 输出不是 JSON，后续无法自动评测。
