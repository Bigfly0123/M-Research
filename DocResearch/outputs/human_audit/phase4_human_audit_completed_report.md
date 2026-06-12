# Phase 4 Human Audit Completed Report

## 1. Audit Scope

- Audited file: `phase4_human_audit_samples.jsonl`
- Total samples: 26
- Datasets: TechDocQA, GaRAGe, robustness out-of-domain, robustness insufficient-evidence, robustness citation-corruption.
- Note: the uploaded audit file contains question/answer/citation IDs but not full source chunk text. Therefore, `citation_support` is judged from answer-citation alignment, citation presence/format, and visible claim grounding, not from a full source-text re-read.

## 2. Scoring Rubric

| Field | 2 | 1 | 0 |
|---|---|---|---|
| answer_correctness | correct / safe refusal when evidence is insufficient | partially correct or safe but non-answer | incorrect or misleading |
| citation_support | citations adequately support the main answer or no citation needed for refusal | weak/partial/irrelevant citation support | unsupported or missing when required |
| answer_completeness | fully answers the question or appropriately refuses | incomplete/truncated/partial answer | does not answer the requested question |
| hallucination | 0 = none | 1 = minor unsupported claim | 2 = clear unsupported/incorrect claim |

## 3. Overall Metrics

| Metric | Value |
|---|---:|
| Total samples | 26 |
| Avg correctness | 1.423 / 2 |
| Avg citation support | 1.769 / 2 |
| Avg completeness | 1.346 / 2 |
| Hallucination rate | 0.077 |
| Perfect sample rate | 0.423 |

## 4. Metrics by Dataset

| dataset                          |   n |   avg_correctness |   avg_citation_support |   avg_completeness |   hallucination_rate |   perfect_rate |
|:---------------------------------|----:|------------------:|-----------------------:|-------------------:|---------------------:|---------------:|
| garage                           |  10 |               1.1 |                    1.7 |                0.9 |                  0.1 |            0.2 |
| robustness_citation_corruption   |   2 |               1.5 |                    1.5 |                1.5 |                  0   |            0.5 |
| robustness_insufficient_evidence |   2 |               2   |                    2   |                2   |                  0   |            1   |
| robustness_out_of_domain         |   2 |               2   |                    1.5 |                2   |                  0   |            0.5 |
| techdocqa                        |  10 |               1.5 |                    1.9 |                1.5 |                  0.1 |            0.5 |

## 5. Error Type Distribution

| error_type                              |   count |
|:----------------------------------------|--------:|
| none                                    |      11 |
| truncated_answer                        |       7 |
| retrieval_missing_safe_refusal          |       3 |
| weak_citation_or_cross_metric_confusion |       1 |
| incomplete_answer                       |       1 |
| partial_answer_missing_comparison       |       1 |
| unsupported_claim_or_entity_confusion   |       1 |
| minor_irrelevant_citation               |       1 |

## 6. Key Findings

1. **TechDocQA is mostly reliable**, but several answers are visibly truncated. This affects completeness more than faithfulness.
2. **GaRAGe has the largest quality variance**. Several samples are safe refusals caused by retrieval mismatch, and one sample contains a clear unsupported/entity-confusion issue about Spain's UEFA Euro 2024 victory.
3. **Robustness refusal behavior is generally good**. OOD and insufficient-evidence cases are mostly handled safely without hallucination.
4. **Ambiguous/citation-corruption scenarios need clearer reporting**. Some answers are safe, but citation relevance is not always strong.
5. **The main residual engineering issue is output truncation**, especially in code-heavy TechDocQA answers.

## 7. Recommended Report Updates

- Do not claim 100% answer quality from automatic metrics alone.
- Add a human-audit section noting that the audit found strong groundedness overall but lower completeness due to truncation/retrieval-missing safe refusals.
- Keep `ambiguous_question` as known limitation; do not add a new clarification agent at this stage.
- Add a final polish task: increase generation max tokens or enforce answer completion checks for code/list answers.

## 8. Detailed Audit Table

|   idx | dataset                          | qid        |   correctness |   citation_support |   completeness |   hallucination | error_type                              | note                                                                                                            |
|------:|:---------------------------------|:-----------|--------------:|-------------------:|---------------:|----------------:|:----------------------------------------|:----------------------------------------------------------------------------------------------------------------|
|     0 | techdocqa                        | q_40       |             1 |                  2 |              1 |               0 | truncated_answer                        | 答案方向正确，引用可支持核心说法，但末尾引用格式/回答内容被截断，完整性下降。                                   |
|     1 | techdocqa                        | q_7        |             2 |                  2 |              2 |               0 | none                                    | 准确解释 G-Eval 的用途和自定义评估指标场景，引用支持充分。                                                      |
|     2 | techdocqa                        | q_1        |             2 |                  2 |              2 |               0 | none                                    | 定义简洁准确，直接回答问题，引用支持充分。                                                                      |
|     3 | techdocqa                        | q_17       |             2 |                  2 |              2 |               0 | none                                    | 准确说明 retriever_tool 的检索与无结果返回逻辑，引用充分。                                                      |
|     4 | techdocqa                        | q_15       |             1 |                  2 |              1 |               0 | truncated_answer                        | 方法方向正确，但回答在 generate_statement 处截断，步骤未完整展开。                                              |
|     5 | techdocqa                        | q_14       |             2 |                  2 |              2 |               0 | none                                    | 解释自定义 prompt 的目的合理，引用支持。                                                                        |
|     6 | techdocqa                        | q_8        |             1 |                  2 |              1 |               0 | truncated_answer                        | 流程方向正确，但代码示例明显截断，导致可操作性不足。                                                            |
|     7 | techdocqa                        | q_6        |             1 |                  2 |              1 |               0 | truncated_answer                        | 流程说明基本正确，但代码示例在 import 处截断，完整性不足。                                                      |
|     8 | techdocqa                        | q_5        |             1 |                  1 |              1 |               1 | weak_citation_or_cross_metric_confusion | 回答把 retriever 指标部分转向 RAGAS 并使用“推测”，对 DeepEval RAG Metrics 的说明不够严格，存在弱引用/轻微混淆。 |
|     9 | techdocqa                        | q_27       |             2 |                  2 |              2 |               0 | none                                    | 准确说明长任务 agent 需要 compaction/子代理以管理有限上下文，引用支持。                                         |
|    10 | garage                           | q_40       |             1 |                  1 |              1 |               0 | incomplete_answer                       | 回答只给出幂等性通用定义，未充分说明 Kinesis Streams 处理可靠性中的去重/重试/重复事件影响。                     |
|    11 | garage                           | q_7        |             1 |                  2 |              0 |               0 | retrieval_missing_safe_refusal          | 安全拒答且无幻觉，但没有回答原问题，说明检索证据不足或召回不匹配。                                              |
|    12 | garage                           | q_1        |             2 |                  2 |              2 |               0 | none                                    | 回答直接说明合作扩大受众，引用支持。                                                                            |
|    13 | garage                           | q_17       |             1 |                  1 |              1 |               0 | truncated_answer                        | 结论方向合理，但回答被截断，证据支持与解释完整性不足。                                                          |
|    14 | garage                           | q_15       |             1 |                  2 |              0 |               0 | retrieval_missing_safe_refusal          | 安全拒答，没有编造 MariMed 策略；但没有回答原问题，属于检索缺失。                                               |
|    15 | garage                           | q_14       |             2 |                  2 |              2 |               0 | none                                    | 完整列出 MLOps 的收益与挑战，引用较充分。                                                                       |
|    16 | garage                           | q_8        |             1 |                  2 |              1 |               0 | truncated_answer                        | 事实方向基本正确，但答案被截断，部分成就说明不完整。                                                            |
|    17 | garage                           | q_6        |             1 |                  2 |              1 |               0 | partial_answer_missing_comparison       | 回答覆盖 Russell 2000 与 S&P 500，但未充分回答与 Nasdaq Composite 的比较。                                      |
|    18 | garage                           | q_34       |             0 |                  1 |              1 |               2 | unsupported_claim_or_entity_confusion   | 把 Aitana Bonmatí 与 Spain UEFA Euro 2024 男足夺冠因素关联，明显语境混淆/不支持。                               |
|    19 | garage                           | q_5        |             1 |                  2 |              0 |               0 | retrieval_missing_safe_refusal          | 安全拒答且没有无证据编造，但未回答原问题；应归为检索缺失而非答案成功。                                          |
|    20 | robustness_out_of_domain         | robust_001 |             2 |                  1 |              2 |               0 | minor_irrelevant_citation               | OOD 问题处理正确，拒绝给出硬件建议；但引用的文档与 GPU 问题关联较弱。                                           |
|    21 | robustness_out_of_domain         | robust_005 |             2 |                  2 |              2 |               0 | none                                    | 正确拒答当前汇率问题，没有编造实时信息。                                                                        |
|    22 | robustness_insufficient_evidence | robust_006 |             2 |                  2 |              2 |               0 | none                                    | 正确指出证据中没有具体 LangGraph 版本信息。                                                                     |
|    23 | robustness_insufficient_evidence | robust_010 |             2 |                  2 |              2 |               0 | none                                    | 正确指出证据中没有 DeepEval 在 MMLU 上的 benchmark 分数或比较。                                                 |
|    24 | robustness_citation_corruption   | robust_016 |             1 |                  1 |              1 |               0 | truncated_answer                        | 回答方向合理，但内容被截断，且 citation_corruption 场景下仍需检查引用是否被真正验证。                           |
|    25 | robustness_citation_corruption   | robust_020 |             2 |                  2 |              2 |               0 | none                                    | 在无直接证据时拒绝解释 dense vs BM25，符合 grounded answer 要求。                                               |
