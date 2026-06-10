---
title: Ragas Available Metrics
source_url: https://docs.ragas.io/en/latest/concepts/metrics/available_metrics/
source_type: official_docs
topic: ragas_metrics
collected_at: 2026-05-18
---

# Ragas: List of Available Metrics

Ragas provides a set of evaluation metrics that can be used to measure the performance of your LLM application. These metrics are designed to help you objectively measure the performance of your application. Metrics are available for different applications and tasks, such as RAG and Agentic workflows.

Each metric is essentially a paradigm designed to evaluate a particular aspect of the application. LLM-based metrics might use one or more LLM calls to arrive at the score or result. You can also modify or write your own metrics using Ragas.

## Retrieval Augmented Generation (RAG) Metrics

### Context Precision

Context Precision evaluates whether all the relevant items present in the contexts are ranked higher in the list. It rewards systems that rank relevant context chunks higher than irrelevant ones.

**Formula**: Context Precision = Σ(Precision@k × rel(k)) / Σ(rel(k))

Where:
- Precision@k = (number of relevant items in top k) / k
- rel(k) = 1 if item at rank k is relevant, 0 otherwise

This metric is important because even if a RAG system retrieves all the relevant documents, if they're buried under irrelevant ones, the LLM may not effectively use them.

### Context Recall

Context Recall measures how well the retrieved context aligns with the ground truth answer. It computes the proportion of ground truth claims that can be attributed to the retrieved context.

**Formula**: Context Recall = |GT claims attributable to context| / |GT claims|

A high context recall indicates that the retrieval system is finding the necessary information to answer the question.

### Context Entities Recall

Context Entities Recall is similar to Context Recall but focuses on named entities. It measures the proportion of entities in the ground truth that are present in the retrieved context.

### Noise Sensitivity

Noise Sensitivity measures how sensitive the RAG system is to noise (irrelevant information) in the retrieved context. A good RAG system should be robust to irrelevant context and still produce correct answers.

### Response Relevancy

Response Relevancy evaluates how relevant the generated response is to the user's question. It uses an LLM to generate questions that the response could be answering, and measures the semantic similarity between the generated questions and the original question.

**Key idea**: A good response should be relevant to the question asked, not contain unnecessary information, and not miss important aspects of the question.

### Faithfulness

Faithfulness measures how factually consistent the generated answer is with the retrieved context. It decomposes the answer into individual claims and checks each claim against the context.

**Formula**: Faithfulness = |claims supported by context| / |total claims|

This is one of the most critical RAG metrics because hallucinations (claims not supported by the context) undermine the entire purpose of RAG.

### Multimodal Faithfulness

Extends Faithfulness to multimodal RAG systems that process images alongside text. It checks whether claims in the answer are supported by both text and image contexts.

### Multimodal Relevance

Extends Response Relevancy to multimodal contexts, evaluating whether the response is relevant given both text and image inputs.

## Nvidia Metrics

### Answer Accuracy

Measures the accuracy of the generated answer compared to the ground truth answer using Nvidia's evaluation methodology.

### Context Relevance

Evaluates how relevant the retrieved context is to the query, using Nvidia's approach to context assessment.

### Response Groundedness

Measures how well the response is grounded in the provided context, ensuring that the answer is derived from the retrieved information rather than hallucinated.

## Agents or Tool Use Metrics

### Topic Adherence

Evaluates whether the agent stays on topic throughout the conversation and doesn't drift away from the user's intended subject.

### Tool Call Accuracy

Measures the accuracy of tool calls made by the agent. It compares the expected tool calls (from ground truth) with the actual tool calls made by the agent.

**Formula**: Tool Call Accuracy = |correct tool calls| / |total tool calls|

### Tool Call F1

Provides an F1 score for tool call evaluation, balancing precision and recall of tool call predictions.

### Agent Goal Accuracy

Evaluates whether the agent successfully achieves the goal or task it was given. This is particularly useful for multi-turn agent interactions where the agent must complete a complex task through a series of steps.

## Natural Language Comparison Metrics

### Factual Correctness

Measures the factual correctness of the generated answer compared to a reference answer. It decomposes both answers into claims and compares them.

### Semantic Similarity

Uses embedding-based similarity to measure how semantically close the generated answer is to the reference answer. Unlike exact match, this captures paraphrases and alternative phrasings.

### Non-LLM String Similarity

Traditional string similarity metrics that don't require LLM calls:

- **Levenshtein distance**: Edit distance between strings.
- **Jaro-Winkler similarity**: String similarity with bonus for matching prefixes.

### BLEU Score

The Bilingual Evaluation Understudy (BLEU) score, originally developed for machine translation evaluation. It measures n-gram precision between generated and reference text.

### CHRF Score

Character n-gram F-score (CHRF), a character-level metric that's more robust to morphological variations than word-level metrics like BLEU.

### ROUGE Score

Recall-Oriented Understudy for Gisting Evaluation (ROUGE), commonly used for summarization evaluation:
- **ROUGE-1**: Unigram overlap
- **ROUGE-2**: Bigram overlap
- **ROUGE-L**: Longest common subsequence

### String Presence

Checks whether specific strings are present in the generated output. Useful for evaluating whether key information is included.

### Exact Match

Binary metric that returns 1 if the generated answer exactly matches the reference, 0 otherwise. Simple but strict.

## SQL Metrics

### Execution-based Datacompy Score

Evaluates SQL query correctness by executing both the generated and reference queries against a database and comparing the results using the `datacompy` library. This catches semantically equivalent queries that differ in syntax.

### SQL Query Equivalence

Uses an LLM to determine whether the generated SQL query is semantically equivalent to the reference query, without needing to execute them.

## General Purpose Metrics

### Aspect Critic

Evaluates specific aspects of the output using an LLM judge. You define the aspect (e.g., "clarity", "conciseness", "correctness") and the LLM evaluates the output on that dimension.

```python
from ragas.metrics import AspectCritic

clarity_critic = AspectCritic(
    name="clarity",
    definition="Is the response clear and easy to understand?"
)
```

### Simple Criteria Scoring

Scores the output on a simple numeric criteria defined by the user. The LLM acts as a judge and assigns a score.

### Rubrics-based Scoring

Uses detailed rubrics to evaluate the output. Each rubric level has a description of what constitutes that score level.

### Instance-specific Rubrics Scoring

Similar to rubrics-based scoring but allows different rubrics for each evaluation instance, enabling fine-grained per-question evaluation criteria.

## Other Task Metrics

### Summarization Score

Evaluates the quality of summaries by measuring:
- **Coverage**: How well the summary covers the key information in the source.
- **Conciseness**: Whether the summary is appropriately brief without losing important information.
- **Faithfulness**: Whether the summary is factually consistent with the source.

## Using Multiple Metrics

Ragas supports evaluating multiple metrics simultaneously:

```python
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_precision,
    context_recall,
)

result = evaluate(
    dataset=your_dataset,
    metrics=[faithfulness, answer_relevancy, context_precision, context_recall],
)
```

## Custom Metrics

You can create custom metrics by implementing the `Metric` interface:

```python
from ragas.metrics import Metric

class MyCustomMetric(Metric):
    name = "my_custom_metric"
    
    async def _ascore(self, row, llm=None):
        # Implement your scoring logic
        return score
```

This extensibility allows you to design metrics for your specific use case while leveraging Ragas's evaluation infrastructure.
