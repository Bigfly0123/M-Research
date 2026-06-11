# Level 1 Retrieval Diagnosis Report

> Phase 2.1 诊断报告：分析 MultiHop-RAG 上 hybrid 退化和 graph 无增益的根因。

## 1. MultiHop-RAG Hybrid 退化分析

### 1.1 总体统计

- 总评测样本: 100
- BM25 优于 Hybrid: **6 条** (6.0%)
- Hybrid 优于 BM25: **19 条** (19.0%)
- 两者相同: **75 条** (75.0%)

### 1.2 all_gold_hit@10 统计

- BM25 all_gold_hit@10: 49/100 = 49.0%
- Hybrid all_gold_hit@10: 57/100 = 57.0%

### 1.3 退化原因分类

| 退化类型 | 数量 | 占比 |
|---|---:|---:|
| graph_expansion_noise | 7 | 7.0% |
| hybrid_fusion_dilution | 3 | 3.0% |
| bm25_strong_dense_noise | 3 | 3.0% |

### 1.4 核心发现

1. **BM25 在 MultiHop-RAG 上是最强单路检索器**。BM25 的 recall@10 显著高于 Dense，
   说明在英文新闻文本上，关键词精确匹配比语义向量检索更有效。

2. **Hybrid 退化主要来自 Dense 噪声稀释 BM25 信号**。
   当 BM25 找到正确文档但 Dense 返回无关文档时，固定权重的 RRF 融合
   会将 Dense 的噪声文档提升到 BM25 的高质量文档之前。

3. **Graph expansion 对新闻文本无效**。
   当前术语抽取规则 (CamelCase, snake_case, 技术白名单) 面向技术文档设计，
   对英文新闻文本几乎抽不出有效术语，导致 graph 路无贡献。

### 1.5 典型案例

#### 案例 1: mh_q_001088
- Query: Does 'The Verge' article suggest that Valve is narrowing its focus to games in its store, while 'Polygon' and 'Engadget'...
- Gold: ['mh_doc_000170', 'mh_doc_000354', 'mh_doc_000169']
- BM25 recall@10: 1.0 | Dense: 0.667 | Hybrid: 0.667 | Hybrid+Graph: 0.667
- Failure type: `hybrid_fusion_dilution`
- BM25 top3: ['mh_doc_000169', 'mh_doc_000354', 'mh_doc_000524']
- Hybrid top3: ['mh_doc_000354', 'mh_doc_000169', 'mh_doc_000524']

#### 案例 2: mh_q_001939
- Query: Which group of individuals could benefit from guides on selecting the right headphones on The Verge, access July Prime D...
- Gold: ['mh_doc_000250', 'mh_doc_000369', 'mh_doc_000104', 'mh_doc_000026']
- BM25 recall@10: 0.75 | Dense: 0.5 | Hybrid: 1.0 | Hybrid+Graph: 0.75
- Failure type: `graph_expansion_noise`
- BM25 top3: ['mh_doc_000567', 'mh_doc_000222', 'mh_doc_000250']
- Hybrid top3: ['mh_doc_000567', 'mh_doc_000250', 'mh_doc_000222']

#### 案例 3: mh_q_001466
- Query: Did the consistency of Google's stance on antitrust issues change according to a later report by TechCrunch on December ...
- Gold: ['mh_doc_000042', 'mh_doc_000014', 'mh_doc_000033']
- BM25 recall@10: 0.333 | Dense: 0.667 | Hybrid: 0.667 | Hybrid+Graph: 0.333
- Failure type: `graph_expansion_noise`
- BM25 top3: ['mh_doc_000033', 'mh_doc_000075', 'mh_doc_000002']
- Hybrid top3: ['mh_doc_000033', 'mh_doc_000237', 'mh_doc_000015']

#### 案例 4: mh_q_000121
- Query: Which company, covered by TechCrunch for its ability to construct new factories, also offers a two-pack of USB-C-to-USB-...
- Gold: ['mh_doc_000528', 'mh_doc_000519', 'mh_doc_000520', 'mh_doc_000002']
- BM25 recall@10: 0.75 | Dense: 0.25 | Hybrid: 0.5 | Hybrid+Graph: 0.5
- Failure type: `bm25_strong_dense_noise`
- BM25 top3: ['mh_doc_000002', 'mh_doc_000595', 'mh_doc_000520']
- Hybrid top3: ['mh_doc_000520', 'mh_doc_000536', 'mh_doc_000514']

#### 案例 5: mh_q_000162
- Query: Was there no change in the portrayal of Sam Altman's professional conduct between the TechCrunch report on Sam Altman's ...
- Gold: ['mh_doc_000011', 'mh_doc_000415', 'mh_doc_000333']
- BM25 recall@10: 1.0 | Dense: 1.0 | Hybrid: 1.0 | Hybrid+Graph: 0.667
- Failure type: `graph_expansion_noise`
- BM25 top3: ['mh_doc_000415', 'mh_doc_000516', 'mh_doc_000048']
- Hybrid top3: ['mh_doc_000415', 'mh_doc_000516', 'mh_doc_000333']

---

## 2. Adaptive Hybrid 效果

- Adaptive 优于 BM25: **16 条**
- Adaptive 劣于 BM25: **5 条**
- 两者相同: **79 条**

### 2.1 Adaptive 退化案例

- mh_q_001088: BM25=1.0, Adaptive=0.667, diff=-0.333
  - Query: Does 'The Verge' article suggest that Valve is narrowing its focus to games in its store, while 'Pol...
- mh_q_001939: BM25=0.75, Adaptive=0.5, diff=-0.25
  - Query: Which group of individuals could benefit from guides on selecting the right headphones on The Verge,...
- mh_q_000121: BM25=0.75, Adaptive=0.5, diff=-0.25
  - Query: Which company, covered by TechCrunch for its ability to construct new factories, also offers a two-p...
- mh_q_002158: BM25=1.0, Adaptive=0.5, diff=-0.5
  - Query: Did the Sporting News article featuring Jayden Fielding mention a missed field goal attempt, while t...
- mh_q_000912: BM25=1.0, Adaptive=0.667, diff=-0.333
  - Query: Does the Polygon article suggest that Valve has made multiple physical upgrades to the Steam Deck, w...

---

## 3. 结论与改进方向

1. **修复 RRF 融合**: 使用无权重标准 RRF 或让 BM25 权重 >= Dense 权重。
2. **默认关闭 Reranker**: 在 eval 中 reranker 不带来稳定提升。
3. **Graph 路对新闻文本无效**: 需要使用 NER 或 LLM 实体抽取替代技术术语规则。
4. **Adaptive hybrid 应至少不低于 BM25**: 通过 query 分析和置信信号动态选择融合权重。
