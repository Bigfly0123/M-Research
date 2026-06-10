# Evidence Composer Instructions

## 角色描述
Evidence Composer 负责将检索到的 chunk 组织为引用就绪的上下文包 (context pack)。
核心流程: 去重 → 按 final_score 排序 → 角色标注 → citation_id 绑定 → budget 截断 → 超长压缩。

## 输入
- chunks: 检索返回的 chunk 列表 (含 chunk_id, text, final_score, source, section 等字段)
- question: 用户问题 (用于角色分类)
- context_budget: 上下文 token 预算 (默认 3500)

## 处理逻辑
1. **去重 (deduplicate)**: 按 chunk_id 去重，记录 dropped 重复项
2. **排序**: 按 final_score 降序排列
3. **角色标注 (classify_role)**: 根据文本内容关键词分类为 6 种 role
4. **citation_id 绑定**: citation_id 即 chunk_id
5. **budget 截断**: 累计 token 不超 context_budget; definition/procedure/code 角色有更高优先级，超预算时优先保留
6. **压缩 (compress_chunk)**: 超 500 token 的 chunk 截断压缩 (当前为规则截断，非 LLM 压缩)
7. **状态判定**: pack >= 3 → ok; pack 1-2 → warn; pack 0 → fail

## 6 种 Evidence Role
| Role | 优先级 | 识别关键词 |
|---|---|---|
| definition | 0 (最高) | define, definition, 是指, 定义为, is a, refers to |
| procedure | 1 | how to, step, process, algorithm, 步骤, 流程 |
| code | 2 | ```, def, class, import, function |
| comparison | 3 | compare, versus, vs, difference, 对比, 区别 |
| example | 4 | example, for instance, e.g., 例如, 示例 |
| limitation | 5 (最低) | limitation, cannot, does not support, 限制, 不支持 |

## 输出
ContextPack 字段:
- status: ok / warn / fail
- context_pack: EvidenceItem 列表
- dropped_chunks: 被丢弃的 chunk (含原因)
- total_context_tokens: 实际使用的 token 数

EvidenceItem 字段:
- citation_id, chunk_id, source, section_path, evidence_text, compressed_text, role, support_score

## 规则
- 每个 chunk 必须有唯一 citation_id
- 超预算时优先保留 definition/procedure/code 角色
- 截断压缩上限 500 token (~1500 字符)
- 无 chunk 输入时返回 fail + next_action=check_retrieval
