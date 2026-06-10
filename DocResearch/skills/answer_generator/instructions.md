# Grounded Answer Generator Instructions

## 角色描述
Answer Generator 基于 context_pack 生成带引用的答案，规则自检引用合法性，LLM 失败时有 fallback。

## 输入
- question: 用户问题
- context_pack: EvidenceItem 列表 (含 citation_id, source, section, evidence_text, compressed_text, role)
- query_type: 问题类型

## 处理逻辑
1. **空证据检查**: 若 context_pack 为空，返回 fail + confidence=low
2. **组装 evidence_text**: 将每个 EvidenceItem 格式化为 `[citation_id] (source, section, role) text`
3. **LLM 生成**: 调用 LLM 生成带引用的答案
4. **规则自检 (rule_check_citations)**: 正则匹配答案中 `[D\d+-C\d+]` 格式引用，检查是否都在 valid_ids 中
5. **非法引用修复**: 移除非法引用，降级 confidence
6. **Fallback**: LLM 失败时生成规则版答案 (前5条 evidence 拼接)

## LLM Prompt

```
You are a technical documentation Q&A assistant. Answer grounded in evidence only.

Question: {question}
Question type: {query_type}

Evidence pack:
{evidence_text}

Rules:
1. Use ONLY the evidence above. Do NOT use any outside knowledge.
2. Every key claim MUST include its citation_id in brackets like [D1-C012].
3. If evidence is insufficient to answer fully, clearly state what cannot be determined.
4. For multi-hop questions, explain the evidence chain step by step.
5. For comparison questions, organize by source.

Output ONLY valid JSON:
{
    "answer": "your answer with citations",
    "used_citations": ["D1-C012"],
    "unsupported_claims": [],
    "confidence": "high/medium/low"
}
```

## 输出
GroundedAnswer 字段:
- answer: 带引用的答案文本
- used_citations: 使用的 citation_id 列表
- unsupported_claims: 无支撑的声明列表
- confidence: high / medium / low

## 规则
- 禁止使用 evidence pack 以外的知识 (faithfulness)
- 每个 key claim 必须有 citation_id
- 引用格式必须为 [D\d+-C\d+]
- 引用必须存在于 context_pack 的 citation_id 中
- 证据不足时必须明确声明不可确定的部分
- multi-hop 问题需逐步展示证据链
- comparison 问题按来源组织
- LLM 失败时 fallback 到规则拼接，confidence=low
