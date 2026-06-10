---
title: DeepEval Metrics Introduction
source_url: https://docs.confident-ai.com/docs/metrics-introduction
source_type: official_docs
topic: deepeval_metrics
collected_at: 2026-05-18
---

# DeepEval: Introduction to LLM Metrics

`deepeval` offers 50+ SOTA, ready-to-use metrics for you to quickly get started with. Essentially, while a test case represents the thing you're trying to measure, the metric acts as the ruler based on a specific criteria of interest.

## Quick Summary

Almost all predefined metrics on `deepeval` uses **LLM-as-a-judge**, with various techniques such as **QAG** (question-answer-generation), **DAG** (deep acyclic graphs), and **G-Eval** to score test cases, which represents atomic interactions with your LLM app.

All of `deepeval`'s metrics output a **score between 0-1** based on its corresponding equation, as well as score **reasoning**. A metric is only successful if the evaluation score is equal to or greater than `threshold`, which is defaulted to `0.5` for all metrics.

## Metric Categories

### Custom Metrics

Custom metrics allow you to define your custom criteria using SOTA implementations of LLM-as-a-Judge metrics in everyday language:

- **G-Eval** – Best for subjective criteria like correctness, coherence, or tone; easy to set up.
- **DAG** – Decision-tree metric for objective or mixed criteria (e.g., verify format before tone).
- **Conversational G-Eval** – G-Eval for multi-turn conversations.
- **Conversational DAG** – DAG for multi-turn conversations.
- **Arena G-Eval** – G-Eval with arena-style comparison.
- **DIY metrics** – 100% self-coded metrics (e.g., BLEU, ROUGE).

You should aim to have **at least one** custom metric in your LLM evals pipeline.

### RAG Metrics

RAG metrics focus on the **retriever and generator components** independently:

**Retriever:**
- Contextual Relevancy
- Contextual Precision
- Contextual Recall

**Generator:**
- Answer Relevancy
- Faithfulness

```python
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric

test_case = LLMTestCase(input="...", actual_output="...")
relevancy = AnswerRelevancyMetric(threshold=0.5)
relevancy.measure(test_case)
print(relevancy.score, relevancy.reason)
```

### Agent Metrics

Agentic metrics evaluate the **overall execution flow** of your agent. There are six main agentic metrics:

- **Task Completion** – Assesses if the agent successfully completed a given task for a given LLM trace.
- **Argument Correctness** – Evaluates if the arguments passed to tools are correct.
- **Tool Correctness** – Evaluates if tools were called and used correctly.
- **Step Efficiency** – Measures if the agent takes efficient steps to complete a task.
- **Plan Adherence** – Evaluates if the agent follows its plan.
- **Plan Quality** – Assesses the quality of the agent's plan.

The task completion metric does not require a test case and will take an LLM trace to evaluate task completion.

```python
from deepeval.metrics import TaskCompletionMetric
from deepeval.tracing import observe
from deepeval.dataset import Golden
from deepeval import evaluate

task_completion = TaskCompletionMetric(threshold=0.5)

@observe(metrics=[task_completion])
def trip_planner_agent(input):
    @observe()
    def itinerary_generator(destination, days):
        return ["Eiffel Tower", "Louvre Museum", "Montmartre"][:days]
    return itinerary_generator("Paris", 2)

evaluate(observed_callback=trip_planner_agent, goldens=[Golden(input="Paris, 2")])
```

### Chatbot (Multi-turn) Metrics

Multi-turn metrics' main use case are for evaluating chatbots and use a `ConversationalTestCase` instead:

- **Knowledge Retention** – Evaluates if the chatbot retains knowledge learnt throughout a conversation.
- **Role Adherence** – Assesses if the chatbot stays in character.
- **Conversation Completeness** – Evaluates if conversations satisfy user needs.
- **Conversation Relevancy** – Measures if generated outputs are relevant to user inputs.

### Safety Metrics

Safety metrics concern LLM security:

- **Bias** – Detects bias in outputs.
- **Toxicity** – Detects toxic content.
- **Non-Advice** – Ensures the model doesn't give advice in restricted domains.
- **Misuse** – Detects misuse of the LLM.
- **PIILeakage** – Detects PII leakage.
- **Role Violation** – Detects role violations.

### Image Metrics

Metrics targeting images expect an image in the test case:

- **Image Coherence** – Evaluates image coherence.
- **Image Helpfulness** – Evaluates image helpfulness.
- **Image Reference** – Evaluates image reference quality.
- **Text-to-Image** – Evaluates text-to-image generation.
- **Image-Editing** – Evaluates image editing quality.

### Other Metrics

- **Hallucination** – Detects hallucinated content.
- **Json Correctness** – Validates JSON output correctness.
- **Summarization** – Evaluates summarization quality.
- **Ragas** – Integration with Ragas metrics.

## Why DeepEval Metrics?

Apart from the variety of metrics offered, `deepeval`'s metrics are a step up because they:

- Are research-backed LLM-as-a-Judge (GEval)
- One of the most used in the world (20 million+ daily evaluations)
- Make deterministic metric scores possible (when using `DAGMetric`)
- Are extra reliable as LLMs are only used for extremely confined tasks during evaluation
- Provide a comprehensive reason for the scores computed
- Integrated 100% with Confident AI

## Creating Custom Metrics with G-Eval

G-Eval is a state-of-the-art LLM evaluation framework for creating custom metrics using natural language:

```python
from deepeval.test_case import LLMTestCase, SingleTurnParams
from deepeval.metrics import GEval

test_case = LLMTestCase(input="...", actual_output="...", expected_output="...")
correctness = GEval(
    name="Correctness",
    criteria="Correctness - determine if the actual output is correct according to the expected output.",
    evaluation_params=[SingleTurnParams.ACTUAL_OUTPUT, SingleTurnParams.EXPECTED_OUTPUT],
    strict_mode=True
)

correctness.measure(test_case)
print(correctness.score, correctness.reason)
```

For multi-turn conversations:

```python
from deepeval.test_case import Turn, MultiTurnParams, ConversationalTestCase
from deepeval.metrics import ConversationalGEval

convo_test_case = ConversationalTestCase(
    turns=[Turn(role="user", content="..."), Turn(role="assistant", content="...")]
)
professionalism_metric = ConversationalGEval(
    name="Professionalism",
    criteria="Determine whether the assistant has acted professionally based on the content.",
    evaluation_params=[MultiTurnParams.CONTENT],
    strict_mode=True
)
professionalism_metric.measure(convo_test_case)
```

## Choosing Your Metrics

When deciding on metrics, limit yourself to **no more than 5 metrics**:

- **2-3** generic, system-specific metrics (e.g., contextual precision for RAG, tool correctness for agents)
- **1-2** custom, use case-specific metrics (e.g., helpfulness for a medical chatbot)

Key considerations:

- **Custom metrics** are use case specific and architecture agnostic. Start with G-Eval for simplicity; use DAG for more control.
- **Generic metrics** are system specific and use case agnostic.
- **Reference-based metrics** need ground truth (e.g., contextual recall, tool correctness).
- **Referenceless metrics** work without labeled data, ideal for production evaluation.

Recommendations:
- **RAG**: Focus on `AnswerRelevancyMetric` and `FaithfulnessMetric`
- **Agents**: Use `ToolCorrectnessMetric` to verify proper tool selection
- **Chatbots**: Implement `ConversationCompletenessMetric`
- **Custom**: Create custom evaluations with G-Eval or DAG frameworks

## Configuring LLM Judges

You can use **ANY** LLM judge in `deepeval`, including OpenAI, Azure OpenAI, Ollama, Anthropic, Gemini, LiteLLM, etc.

### OpenAI

```bash
export OPENAI_API_KEY=<your-openai-api-key>
```

### Azure OpenAI

```bash
deepeval set-azure-openai \
    --base-url=<endpoint> \
    --model=<model_name> \
    --deployment-name=<deployment_name> \
    --api-version=<api_version> \
    --model-version=<model_version>
```

### Ollama

```bash
deepeval set-ollama --model=deepseek-r1:1.5b
```

### Custom LLM

```python
from deepeval.models.base_model import DeepEvalBaseLLM

class CustomLLM(DeepEvalBaseLLM):
    def __init__(self, model):
        self.model = model

    def load_model(self):
        return self.model

    def generate(self, prompt: str) -> str:
        chat_model = self.load_model()
        return chat_model.invoke(prompt).content

    async def a_generate(self, prompt: str) -> str:
        chat_model = self.load_model()
        res = await chat_model.ainvoke(prompt)
        return res.content

    def get_model_name(self):
        return "Custom Model"
```

## Using Metrics

### End-to-End Evals

```python
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric
from deepeval import evaluate

test_case = LLMTestCase(input="...", actual_output="...")
evaluate(test_cases=[test_case], metrics=[AnswerRelevancyMetric()])
```

### Component-Level Evals

```python
from deepeval.tracing import observe, update_current_span
from deepeval.metrics import AnswerRelevancyMetric

@observe()
def llm_app(input: str):
    @observe(metrics=[AnswerRelevancyMetric()])
    def nested_component():
        update_current_span(test_case=LLMTestCase(...))
        pass
    nested_component()
```

### One-Off Evals

```python
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.test_case import LLMTestCase

test_case = LLMTestCase(...)
metric = AnswerRelevancyMetric(threshold=0.5)
metric.measure(test_case)
print(metric.score, metric.reason)
```

All metrics support:
- `metric.score` – Score between 0-1
- `metric.reason` – Explanation for the score
- `metric.is_successful()` – True if score >= threshold
- `threshold` – Success threshold (default 0.5)
- `strict_mode` – Forces binary score (0 or 1)
- `verbose_mode` – Prints metric logs during execution
- `async_mode` – Controls concurrent execution (default True)

## Async Evaluation

```python
import asyncio

async def evaluate_all():
    await asyncio.gather(
        metric1.a_measure(test_case),
        metric2.a_measure(test_case),
        metric3.a_measure(test_case),
    )

asyncio.run(evaluate_all())
```

## Debugging Metrics

Turn on `verbose_mode` for any metric to debug its inner workings:

```python
metric = AnswerRelevancyMetric(verbose_mode=True)
metric.measure(test_case)
```

## Customizing Metric Prompts

All metrics use LLM-as-a-judge evaluation with unique default prompt templates. You can customize these to improve evaluation accuracy:

```python
from deepeval.metrics import AnswerRelevancyMetric
from deepeval.metrics.answer_relevancy import AnswerRelevancyTemplate

class CustomTemplate(AnswerRelevancyTemplate):
    @staticmethod
    def generate_statements(actual_output: str):
        return f"""Given the text, breakdown and generate a list of statements presented.

Text:
{actual_output}

JSON:
"""

metric = AnswerRelevancyMetric(evaluation_template=CustomTemplate)
```
