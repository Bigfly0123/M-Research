---
license: odc-by
task_categories:
- question-answering
- feature-extraction
language:
- en
pretty_name: MultiHop-RAG
size_categories:
- 1K<n<10K
configs:
- config_name: MultiHopRAG
  data_files: "MultiHopRAG.json"
- config_name: corpus
  data_files: "corpus.json"

---
# Dataset Card for Dataset Name

A Dataset for Evaluating Retrieval-Augmented Generation Across Documents


### Dataset Description

**MultiHop-RAG**: a QA dataset to evaluate retrieval and reasoning across documents with metadata in the RAG pipelines. It contains 2556 queries, with evidence for each query distributed across 2 to 4 documents. The queries also involve document metadata, reflecting complex scenarios commonly found in real-world RAG applications.

### Dataset Sources 

<!-- Provide the basic links for the dataset. -->

- **Github:** [MultiHop-RAG](https://github.com/yixuantt/MultiHop-RAG)
- **Paper:** [MultiHop-RAG: Benchmarking Retrieval-Augmented Generation for Multi-Hop Queries](https://arxiv.org/abs/2401.15391)

## Citation 

**BibTeX:**
```
@misc{tang2024multihoprag,
      title={MultiHop-RAG: Benchmarking Retrieval-Augmented Generation for Multi-Hop Queries}, 
      author={Yixuan Tang and Yi Yang},
      year={2024},
      eprint={2401.15391},
      archivePrefix={arXiv},
      primaryClass={cs.CL}
}
```