# MultiHop-RAG Evaluation Report

## 1. Dataset

- Dataset: MultiHop-RAG
- Sample size: 100
- Task: multi-hop retrieval and QA
- Corpus: MultiHop-RAG corpus

## 2. Compared Configs

| Config | Dense | BM25 | Graph | Repair |
|---|---|---|---|---|
| baseline_vector | yes | no | no | no |
| hybrid | yes | yes | no | no |
| hybrid_graph | yes | yes | yes | no |

## 3. Metrics

- Gold Doc Recall@10
- All Gold Docs Hit@10
- Gold Chunk Recall@10
- Selected Evidence Recall
- Avg Latency

## 4. Results

| Config | Gold Doc Recall@10 | All Gold Docs Hit@10 | Gold Chunk Recall@10 | Selected Evidence Recall | Avg Latency |
|---|---:|---:|---:|---:|---:|
| baseline_vector | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| hybrid | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |
| hybrid_graph | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0 |

## 5. Findings

1. baseline_vector 的 Gold Doc Recall@10 (0.0000) 优于或等于 hybrid_graph (0.0000)

## 6. Failure Cases

### baseline_vector

- [mh_q_002119] Did the 'Sport Grill' article attribute the defeat of the Belgium Women's National Football Team by ... (gold: 2 docs)
- [mh_q_000558] Between the TechCrunch report on EU's call for AI safeguards related to deepfake election risks and ... (gold: 3 docs)
- [mh_q_001661] After the Polygon report on the Steam Deck OLED published at 18:00:00 on November 9, 2023, and the E... (gold: 3 docs)
- [mh_q_001088] Does 'The Verge' article suggest that Valve is narrowing its focus to games in its store, while 'Pol... (gold: 3 docs)
- [mh_q_001246] Does 'The Guardian' article suggest that Manchester United struggles with pressure in the Champions ... (gold: 2 docs)

### hybrid

- [mh_q_002119] Did the 'Sport Grill' article attribute the defeat of the Belgium Women's National Football Team by ... (gold: 2 docs)
- [mh_q_000558] Between the TechCrunch report on EU's call for AI safeguards related to deepfake election risks and ... (gold: 3 docs)
- [mh_q_001661] After the Polygon report on the Steam Deck OLED published at 18:00:00 on November 9, 2023, and the E... (gold: 3 docs)
- [mh_q_001088] Does 'The Verge' article suggest that Valve is narrowing its focus to games in its store, while 'Pol... (gold: 3 docs)
- [mh_q_001246] Does 'The Guardian' article suggest that Manchester United struggles with pressure in the Champions ... (gold: 2 docs)

### hybrid_graph

- [mh_q_002119] Did the 'Sport Grill' article attribute the defeat of the Belgium Women's National Football Team by ... (gold: 2 docs)
- [mh_q_000558] Between the TechCrunch report on EU's call for AI safeguards related to deepfake election risks and ... (gold: 3 docs)
- [mh_q_001661] After the Polygon report on the Steam Deck OLED published at 18:00:00 on November 9, 2023, and the E... (gold: 3 docs)
- [mh_q_001088] Does 'The Verge' article suggest that Valve is narrowing its focus to games in its store, while 'Pol... (gold: 3 docs)
- [mh_q_001246] Does 'The Guardian' article suggest that Manchester United struggles with pressure in the Champions ... (gold: 2 docs)

## 7. Conclusion

- 第一版先跑 retrieval_only，验证检索质量。
- 后续接入 full_qa 模式，评估完整 pipeline。
