# StratRAG 2026 数据集处理指南

## 1. 数据集简介
- 来源：[HuggingFace StratRAG 2026](https://huggingface.co/datasets/Aryanp088/StratRAG)
- 样本数：约 2,500 条
- 特点：
  - 每条问题通常有 15 个候选文档（2 gold + 13 distractors）
  - 主要用于测试 **多跳检索能力**
  - gold 文档已标注，可用于评测 retriever 的召回率和 ranking 精度

## 2. 处理步骤
1. **下载数据**
   ```bash
   git lfs install
   git clone https://huggingface.co/datasets/Aryanp088/StratRAG
   ```
2. **抽样**
   - 按需求抽取 50～100 条样本作为 eval subset
3. **数据格式转换**
   - 转为 JSONL，每条记录包含：
     - `id`：样本唯一标识
     - `question`：问题文本
     - `gold_doc_ids`：标注的 gold 文档 id
     - `candidate_doc_ids`：所有候选文档 id
     - `expected_answer`：参考答案（可为空，用于 retriever-only eval）
     - `difficulty`：可选
4. **gold chunk 映射**
   - 将 gold_doc_ids 对应的文档拆成 chunk（可按段落或句子）
   - 生成 `gold_chunk_ids`，用于 GraphRAG 测试
5. **接入 Eval Runner**
   - 评测指标：
     - `retrieval recall @1/5/10`
     - `mean reciprocal rank (MRR)`
     - `hit rate` (是否至少返回一个 gold chunk)
   - 可选：测试不同 retriever（BM25 / vector / hybrid / graph）

## 3. 注意事项
- StratRAG 偏向检索测试，不关注生成质量
- 不需要生成复杂答案，focus on `retrieval recall`
- 抽样时尽量保留 gold 文档和 distractors 的比例

---

# GaRAGe 2025 数据集处理指南

## 1. 数据集简介
- 来源：[HuggingFace GaRAGe 2025](https://huggingface.co/datasets/AmazonScience/GaRAGe)
- 样本数：约 1,000 条
- 特点：
  - 侧重 **grounding / citation**
  - 每个问题有一个 gold 参考答案和相关文档
  - 适合评估 **Evidence Composer、Answer Judge、自修复能力**

## 2. 处理步骤
1. **下载数据**
   ```bash
   git lfs install
   git clone https://huggingface.co/datasets/AmazonScience/GaRAGe
   ```
2. **抽样**
   - 选取 50 条代表性问题
3. **数据格式转换**
   - JSONL 字段：
     - `id`：样本 id
     - `question`：问题
     - `gold_doc_ids`：gold 文档 id
     - `gold_chunk_ids`：拆分后的 chunk id
     - `expected_answer`：参考答案文本
     - `difficulty`：可选
4. **gold chunk 映射**
   - 将 gold 文档拆分成 chunk，保持原始引用信息
   - 每条 chunk 保留 source_path / doc_id / section
5. **接入 Eval Runner**
   - 评测指标：
     - `answer groundedness`（答案是否基于 gold chunk）
     - `citation accuracy`（引用是否正确）
     - `factual correctness`（可选）
   - 可选：结合 Self-Reflection Judge 检查答案忠实度

## 3. 注意事项
- GaRAGe 的任务重点是证据支持，不侧重多跳检索
- 可以配合 TechDocQA 做 grounding benchmark
- 保证 gold chunk 与问题答案的一一对应，避免偏差