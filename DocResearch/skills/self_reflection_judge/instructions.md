# Self-Reflection Judge Instructions

## 角色描述
Self-Reflection Judge 是答案质量审查器，对生成的答案进行 4 维评估，审查失败时输出 failure_type 和 repair_action。

流程: rule_based_judge -> (可选) LLM 增强 -> 确定是否 pass。

## 输入
- question: 用户问题
- answer: 生成的答案
- context_pack: EvidenceItem 列表
- used_citations: 使用的引用 ID 列表
- unsupported_claims: 无支撑声明列表
- use_llm: 是否使用 LLM 增强 (默认 False)

## 处理逻辑
1. **规则版评估 (rule_based_judge)**: 基于词重叠、引用比例、证据数量计算 4 维分数
2. **阈值检查**: 任一维度低于阈值 → fail + 确定 failure_type + repair_action
3. **LLM 增强 (可选)**: 调用 LLM 对 4 维评分和 failure_type 进行深度评估
4. **特殊规则**: 若 used_citations 为空但 context_pack 非空 → citation_error

## LLM Prompt

```
You are a strict answer quality judge. Evaluate the answer on 4 dimensions (0.0-1.0).

Question: {question}
Answer: {answer}
Evidence:
{evidence}

Output ONLY valid JSON:
{
    "answer_relevance": 0.0-1.0,
    "citation_support": 0.0-1.0,
    "faithfulness": 0.0-1.0,
    "context_sufficiency": 0.0-1.0,
    "failure_type": "none" or one of [retrieval_miss, weak_evidence, citation_error, hallucination, incomplete_answer, context_noise],
    "reason": "brief explanation",
    "repair_action": null or one of [rewrite_query, graph_expand, recompose_evidence, regenerate_with_evidence_only, decompose_query, reduce_context_noise]
}
```

## 4 维评分 (0.0-1.0)
| 维度 | 计算方式 | 阈值 |
|---|---|---|
| answer_relevance | question-answer 词重叠率 * 1.5 | 0.75 |
| citation_support | used_citations / pack_size | 0.75 |
| faithfulness | 1.0 - unsupported_claims * 0.25 | 0.75 |
| context_sufficiency | min(1.0, pack_size / 5) | 0.65 |

## 7 种 Failure Type + Repair Action
| failure_type | repair_action | 含义 |
|---|---|---|
| none | null | 通过 |
| retrieval_miss | rewrite_query | 检索未命中 |
| weak_evidence | graph_expand | 证据不足 |
| citation_error | recompose_evidence | 引用错误 |
| hallucination | regenerate_with_evidence_only | 幻觉 |
| incomplete_answer | decompose_query | 答案不完整 |
| context_noise | reduce_context_noise | 上下文噪声 |

## 输出
JudgeResult 字段:
- pass_: 是否通过
- answer_relevance, citation_support, faithfulness, context_sufficiency: 4 维分数
- failure_type: 失败类型
- repair_action: 修复动作
- reason: 评估理由

## 规则
- 核心逻辑不依赖 LLM，LLM 仅作增强
- 优先级: answer_relevance > citation_support > faithfulness > context_sufficiency
- used_citations 为空但 pack 非空 → 直接判定 citation_error
- LLM 失败时 fallback 到规则版结果
