# Citation Guardrails Instructions

## 角色描述
Citation Guardrails 是引用可靠性护栏，对答案中的引用执行三层检查，确保引用格式正确、来源合法、声明有支撑。

## 输入
- answer: 生成的答案文本
- context_pack: EvidenceItem 列表 (含 citation_id)

## 处理逻辑

### 第一层: existence (格式检查)
- 正则匹配 `[D\d+-C\d+]` 格式的引用 ID
- 确认答案中包含引用标记

### 第二层: alignment (来源检查)
- 检查答案中每个引用 ID 是否存在于 context_pack 的 citation_id 集合中
- 识别无效引用 (不存在于 pack)

### 第三层: support (支撑检查)
- 拆分答案为句子 (按 .!?。！？ 分割)
- 对超过 20 字的长句子，检查是否包含引用标记
- 识别无引用支撑的声明

### 判定逻辑
| 条件 | action | 含义 |
|---|---|---|
| 答案为空 | block | 无法输出 |
| 完全无引用 | block | 答案无任何引用 |
| 全部引用无效 | block | 引用全部不在 pack 中 |
| 部分引用无效 或 存在未引用声明 | repair | 需修复 |
| 全部通过 | pass | 合格 |

## 输出
CitationGuardResult 字段:
- pass_: 是否通过
- invalid_citations: 无效引用列表
- unsupported_claims: 无引用支撑的声明列表
- action: pass / repair / block
- reason: 判定理由

## 规则
- 引用格式必须为 [D\d+-C\d+]
- 引用 ID 必须存在于 context_pack
- 超过 20 字的句子必须有引用支撑
- block 和 repair 都触发 next_action=repair
- unsupported_claims 最多返回 5 条
