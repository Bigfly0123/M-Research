# 09｜Citation Guardrails 设计指导

> 项目定位：**DocResearch-Agent 2026：面向技术文档的 Context-Engineered Agentic GraphRAG 可靠性系统**。
> 目标不是普通 RAG 问答，而是围绕上下文规划、图增强检索、证据组合、自动评测、可追踪修复构建一个小而硬的高级项目。

## 1. 模块作用
Citation Guardrails 是输出安全阀，负责检查引用格式、引用来源和引用支持关系。它保证答案不是“看起来有引用，实际乱引用”。

## 2. 必须理解的知识点
- **Guardrail**：自动验证输入、输出或工具行为，决定流程继续、暂停或停止。
- **Citation Syntax Check**：引用 ID 是否合法。
- **Citation Source Check**：引用是否来自当前 context_pack。
- **Citation Semantic Check**：引用证据是否支持 claim。

## 3. 技术参考
- [OpenAI Guardrails](https://developers.openai.com/api/docs/guides/agents/guardrails-approvals)
- [Ragas Faithfulness](https://docs.ragas.io/en/stable/concepts/metrics/available_metrics/faithfulness/)

## 4. 输出示例
```json
{
  "guardrail_pass": false,
  "invalid_citations": ["D3-C99"],
  "uncited_claims": ["The system uses PageRank."],
  "unsupported_claims": [
    {"claim": "Graph expansion improves retrieval.", "citation": "D1-C02", "reason": "Evidence only describes BM25."}
  ],
  "recommended_action": "regenerate_with_evidence_only"
}
```

## 5. 设计方案
第一版做三层：
1. 正则抽取 citation。
2. 检查 citation 是否在 context_pack。
3. 按句子切 claim，用关键词 overlap 或 LLM 判断支持关系。

## 6. 实施步骤
```python
def extract_citations(answer):
    return re.findall(r'\[D\d+-C\d+\]', answer)
```
然后：
- `invalid_citations = citations - valid_ids`
- 无引用则 fail
- 语义支持低则 fail

## 7. 验收标准
- 能识别不存在 citation_id。
- 能识别答案完全无引用。
- guardrail 失败触发 Repair Router。
- eval report 统计 citation_guardrail_pass_rate。

## 8. 常见坑
- 只检查格式，不检查来源。
- Guardrail 和 Judge 职责混乱。
- 引用格式不统一。
- semantic check 过度复杂，拖慢两周计划。
