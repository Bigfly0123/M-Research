# Eval Report Writer Instructions

## 角色描述
Eval Report Writer 负责生成评测对比报告，读取多组 results.jsonl，汇总指标，对比不同检索策略的效果。

## 输入
- input_paths: 多个 results.jsonl 文件路径列表
- output_path: 报告输出路径

## 处理逻辑
1. **加载数据**: 读取每个 results.jsonl，解析为记录列表
2. **计算汇总 (compute_summary)**: 对每组结果计算指标均值和平均延迟
3. **发现失败案例 (find_failure_cases)**: 找出 gold_doc_recall@10=0 的案例 (最多5个)
4. **生成报告**: 按 7 个章节组装 Markdown 报告

## 报告结构
1. **Dataset**: 数据集名称、样本量、任务描述
2. **Compared Configs**: 各配置的特征矩阵 (Dense/BM25/Graph/Repair)
3. **Metrics**: 指标说明
4. **Results**: 指标对比表
5. **Findings**: 关键发现 (首尾配置对比)
6. **Failure Cases**: 各配置的失败案例
7. **Conclusion**: 结论和后续计划

## 评测指标
- gold_doc_recall@10: top-10 检索结果覆盖了多少 gold documents
- all_gold_docs_hit@10: 是否所有 gold documents 都进入 top-10
- gold_chunk_recall@10: top-10 chunk 覆盖 gold chunks
- selected_evidence_recall: Evidence Composer 保留正确证据的比例
- answer_keyword_coverage: 答案关键词覆盖率
- avg_latency_ms: 平均延迟

## 配置特征映射
| config | Dense | BM25 | Graph | Repair |
|---|---|---|---|---|
| baseline_vector | yes | no | no | no |
| hybrid | yes | yes | no | no |
| hybrid_graph | yes | yes | yes | no |
| agentic_graph_repair | yes | yes | yes | yes |

## 输出
Markdown 格式的评测报告 (eval_report.md)

## 规则
- 多组结果按 config_name 组织
- 失败案例限制最多 5 个
- 指标值显示 4 位小数
- 延迟显示整数 ms
