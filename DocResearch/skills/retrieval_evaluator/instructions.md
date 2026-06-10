# Retrieval Evaluator Instructions

## 角色描述
Retrieval Evaluator 是检索质量评估器，遵循 Corrective RAG 思想：检索可能错，先评估，再决定继续/改写/扩展。

流程: heuristic 评估 -> (可选) LLM 评估 -> 确定行动。

## 输入
- question: 用户问题
- chunks: 检索返回的 chunk 列表
- use_llm: 是否使用 LLM 评估 (默认 True)

## 处理逻辑
1. **启发式评估 (heuristic_evidence_score)**: 基于词重叠、top_score、来源多样性计算 confidence
2. **LLM 评估 (llm_evaluate)**: 当 heuristic 结果非 strong 时，调用 LLM 深度评估
3. **行动决策**: confidence >= 0.6 → strong/continue; 0.35-0.6 → weak/graph_expand; < 0.35 → irrelevant/rewrite_query

## LLM Prompt

```
Evaluate the retrieval quality for this question.

Question: {question}

Retrieved chunks:
{context}

Output ONLY valid JSON:
{
    "evidence_quality": "strong/weak/irrelevant/conflicting",
    "confidence": 0.0-1.0,
    "reason": "brief explanation",
    "missing_evidence": ["what is missing"],
    "recommended_action": "continue/rewrite_query/graph_expand/fallback_bm25"
}
```

## 输出
RetrievalEvalResult 字段:
- evidence_quality: strong / weak / irrelevant / conflicting
- confidence: 0.0-1.0
- reason: 评估理由
- missing_evidence: 缺失的证据描述
- recommended_action: continue / rewrite_query / graph_expand / fallback_bm25

## 规则
- 无 chunk 时直接判定 irrelevant + rewrite_query
- heuristic strong 时跳过 LLM 调用
- LLM 失败时 fallback 到 heuristic 结果
- status 映射: strong→ok, weak→warn, 其他→fail
