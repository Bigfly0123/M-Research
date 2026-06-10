# Repair Router Instructions

## 角色描述
Repair Router 根据 Judge 诊断的 failure_type 路由到对应的修复动作和下一节点。
由 REPAIR_POLICY 和 REPAIR_NODE_MAP 双字典驱动。

## 输入
- failure_type: Judge 诊断的失败类型
- repair_count: 当前已修复次数
- max_repair_count: 最大修复次数 (默认 3)
- judge_result: Judge 结果 (可选，用于补充 reason)

## 处理逻辑
1. **无故障检查**: failure_type 为 none 或 null → 无需修复，next_node=end
2. **修复次数上限**: repair_count >= max_repair_count → 停止修复，保守降级，next_node=end
3. **路由查表**: 根据 REPAIR_POLICY 查找 repair_action，再根据 REPAIR_NODE_MAP 查找 next_node
4. **构建决策**: 组装 RepairDecision (repair_action, repair_reason, next_node, failure_type)

## REPAIR_POLICY 路由表
| failure_type | repair_action | 含义 |
|---|---|---|
| retrieval_miss | rewrite_query | 检索未命中，改写查询 |
| weak_evidence | graph_expand | 证据不足，图扩展 |
| citation_error | evidence_recompose | 引用错误，重组证据 |
| hallucination | regenerate_with_evidence_only | 幻觉，仅用证据重新生成 |
| incomplete_answer | decompose_question | 答案不完整，分解问题 |
| context_noise | reduce_context | 上下文噪声，精简上下文 |

## REPAIR_NODE_MAP 节点映射
| repair_action | next_node |
|---|---|
| rewrite_query | context_planner |
| graph_expand | hybrid_graph_retriever |
| evidence_recompose | evidence_composer |
| regenerate_with_evidence_only | answer_generator |
| decompose_question | context_planner |
| reduce_context | evidence_composer |

## 输出
RepairDecision 字段:
- repair_action: 修复动作
- repair_reason: 修复理由
- next_node: 下一节点
- updated_state_patch: 状态更新补丁 (默认空)
- failure_type: 原始故障类型

## 规则
- 未知 failure_type 默认路由到 regenerate_with_evidence_only
- 修复次数达上限后停止，返回 status=warn
- 无故障时返回 status=ok, next_action=end
- judge_result 中的 reason 会附加到 repair_reason
