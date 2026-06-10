---
title: Effective Context Engineering for AI Agents
source_url: https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents
source_type: blog
topic: anthropic_context_engineering
collected_at: 2026-05-18
---

# Effective Context Engineering for AI Agents

Context is a critical but finite resource for AI agents. In this post, we explore strategies for effectively curating and managing the context that powers them.

After a few years of prompt engineering being the focus of attention in applied AI, a new term has come to prominence: **context engineering**. Building with language models is becoming less about finding the right words and phrases for your prompts, and more about answering the broader question of "what configuration of context is most likely to generate our model's desired behavior?"

**Context** refers to the set of tokens included when sampling from a large-language model (LLM). The **engineering** problem at hand is optimizing the utility of those tokens against the inherent constraints of LLMs in order to consistently achieve a desired outcome. Effectively wrangling LLMs often requires *thinking in context* — in other words: considering the holistic state available to the LLM at any given time and what potential behaviors that state might yield.

## Context Engineering vs. Prompt Engineering

At Anthropic, we view context engineering as the natural progression of prompt engineering. Prompt engineering refers to methods for writing and organizing LLM instructions for optimal outcomes. **Context engineering** refers to the set of strategies for curating and maintaining the optimal set of tokens (information) during LLM inference, including all the other information that may land there outside of the prompts.

In the early days of engineering with LLMs, prompting was the biggest component of AI engineering work, as the majority of use cases required prompts optimized for one-shot classification or text generation tasks. As the term implies, the primary focus of prompt engineering is how to write effective prompts, particularly system prompts. However, as we move towards engineering more capable agents that operate over multiple turns of inference and longer time horizons, we need strategies for managing the entire context state (system instructions, tools, Model Context Protocol (MCP), external data, message history, etc).

An agent running in a loop generates more and more data that *could* be relevant for the next turn of inference, and this information must be cyclically refined. Context engineering is the art and science of curating what will go into the limited context window from that constantly evolving universe of possible information.

## Why Context Engineering Is Important

Despite their speed and ability to manage larger and larger volumes of data, LLMs, like humans, lose focus or experience confusion at a certain point. Studies on needle-in-a-haystack style benchmarking have uncovered the concept of **context rot**: as the number of tokens in the context window increases, the model's ability to accurately recall information from that context decreases.

While some models exhibit more gentle degradation than others, this characteristic emerges across all models. Context, therefore, must be treated as a finite resource with diminishing marginal returns. Like humans, who have limited working memory capacity, LLMs have an "attention budget" that they draw on when parsing large volumes of context. Every new token introduced depletes this budget by some amount, increasing the need to carefully curate the tokens available to the LLM.

This attention scarcity stems from architectural constraints of LLMs. LLMs are based on the transformer architecture, which enables every token to attend to every other token across the entire context. This results in n² pairwise relationships for n tokens.

As its context length increases, a model's ability to capture these pairwise relationships gets stretched thin, creating a natural tension between context size and attention focus. These factors create a performance gradient rather than a hard cliff: models remain highly capable at longer contexts but may show reduced precision for information retrieval and long-range reasoning compared to their performance on shorter contexts.

## The Anatomy of Effective Context

Given that LLMs are constrained by a finite attention budget, *good* context engineering means finding the *smallest possible* set of high-signal tokens that maximize the likelihood of some desired outcome.

### System Prompts

System prompts should be extremely clear and use simple, direct language that presents ideas at the *right altitude* for the agent. The right altitude is the Goldilocks zone between two common failure modes:

- **At one extreme**: Engineers hardcoding complex, brittle logic in their prompts to elicit exact agentic behavior. This creates fragility and increases maintenance complexity.
- **At the other extreme**: Engineers providing vague, high-level guidance that fails to give the LLM concrete signals for desired outputs or falsely assumes shared context.

The optimal altitude strikes a balance: specific enough to guide behavior effectively, yet flexible enough to provide the model with strong heuristics.

We recommend organizing prompts into distinct sections (like `<background_information>`, `<instructions>`, `## Tool guidance`, `## Output description`, etc) and using techniques like XML tagging or Markdown headers to delineate these sections.

Regardless of structure, strive for the minimal set of information that fully outlines expected behavior. Start by testing a minimal prompt with the best model available, then add clear instructions and examples to improve performance based on failure modes found during initial testing.

### Tools

Tools allow agents to operate with their environment and pull in new, additional context as they work. Because tools define the contract between agents and their information/action space, it's extremely important that tools promote efficiency, both by returning information that is token efficient and by encouraging efficient agent behaviors.

Tools should be self-contained, robust to error, and extremely clear with respect to their intended use. Input parameters should similarly be descriptive, unambiguous, and play to the inherent strengths of the model.

One of the most common failure modes is bloated tool sets that cover too much functionality or lead to ambiguous decision points about which tool to use. If a human engineer can't definitively say which tool should be used in a given situation, an AI agent can't be expected to do better.

### Examples (Few-Shot Prompting)

Providing examples is a well known best practice. However, teams will often stuff a laundry list of edge cases into a prompt in attempt to articulate every possible rule. We do not recommend this. Instead, curate a set of diverse, canonical examples that effectively portray the expected behavior of the agent. For an LLM, examples are the "pictures" worth a thousand words.

## Context Retrieval and Agentic Search

As the field transitions to more agentic approaches, we increasingly see teams augmenting retrieval systems with "just in time" context strategies.

Rather than pre-processing all relevant data up front, agents built with the "just in time" approach maintain lightweight identifiers (file paths, stored queries, web links, etc.) and use these references to dynamically load data into context at runtime using tools. Claude Code uses this approach to perform complex data analysis over large databases — the model writes targeted queries, stores results, and leverages Bash commands like head and tail to analyze large volumes of data without ever loading full data objects into context.

This approach mirrors human cognition: we generally don't memorize entire corpuses of information, but rather introduce external organization and indexing systems like file systems, inboxes, and bookmarks to retrieve relevant information on demand.

Beyond storage efficiency, the metadata of these references provides a mechanism to efficiently refine behavior. To an agent operating in a file system, the presence of a file named `test_utils.py` in a `tests` folder implies a different purpose than the same file in `src/core_logic/`. Folder hierarchies, naming conventions, and timestamps all provide important signals.

Letting agents navigate and retrieve data autonomously also enables **progressive disclosure** — agents incrementally discover relevant context through exploration. Each interaction yields context that informs the next decision: file sizes suggest complexity; naming conventions hint at purpose; timestamps can be a proxy for relevance.

## Context Engineering for Long-Horizon Tasks

Long-horizon tasks require agents to maintain coherence, context, and goal-directed behavior over sequences of actions where the token count exceeds the LLM's context window. For tasks spanning tens of minutes to multiple hours, agents require specialized techniques.

### Compaction

Compaction is the practice of taking a conversation nearing the context window limit, summarizing its contents, and reinitializing a new context window with the summary. Compaction typically serves as the first lever in context engineering to drive better long-term coherence.

At its core, compaction distills the contents of a context window in a high-fidelity manner, enabling the agent to continue with minimal performance degradation. In Claude Code, this is implemented by passing the message history to the model to summarize and compress the most critical details. The model preserves architectural decisions, unresolved bugs, and implementation details while discarding redundant tool outputs or messages.

The art of compaction lies in the selection of what to keep versus what to discard. Overly aggressive compaction can result in the loss of subtle but critical context whose importance only becomes apparent later. One of the safest lightest touch forms of compaction is tool result clearing.

### Structured Note-Taking

Structured note-taking, or agentic memory, is a technique where the agent regularly writes notes persisted to memory outside of the context window. These notes get pulled back into the context window at later times.

This strategy provides persistent memory with minimal overhead. Like Claude Code creating a to-do list, or your custom agent maintaining a NOTES.md file, this simple pattern allows the agent to track progress across complex tasks, maintaining critical context and dependencies that would otherwise be lost across dozens of tool calls.

Claude playing Pokémon demonstrates how memory transforms agent capabilities. The agent maintains precise tallies across thousands of game steps — tracking objectives like "for the last 1,234 steps I've been training my Pokémon in Route 1, Pikachu has gained 8 levels toward the target of 10." Without prompting about memory structure, it develops maps of explored regions, remembers achievements, and maintains strategic notes.

### Sub-Agent Architectures

Sub-agent architectures provide another way around context limitations. Rather than one agent attempting to maintain state across an entire project, specialized sub-agents can handle focused tasks with clean context windows. The main agent coordinates with a high-level plan while subagents perform deep technical work. Each subagent might explore extensively, using tens of thousands of tokens or more, but returns only a condensed summary of its work (often 1,000-2,000 tokens).

This achieves a clear separation of concerns — the detailed search context remains isolated within sub-agents, while the lead agent focuses on synthesizing and analyzing the results.

The choice between these approaches depends on task characteristics:

- **Compaction** maintains conversational flow for tasks requiring extensive back-and-forth.
- **Note-taking** excels for iterative development with clear milestones.
- **Multi-agent architectures** handle complex research and analysis where parallel exploration pays dividends.

## Conclusion

Context engineering represents a fundamental shift in how we build with LLMs. As models become more capable, the challenge isn't just crafting the perfect prompt — it's thoughtfully curating what information enters the model's limited attention budget at each step. Whether you're implementing compaction for long-horizon tasks, designing token-efficient tools, or enabling agents to explore their environment just-in-time, the guiding principle remains the same: **find the smallest set of high-signal tokens that maximize the likelihood of your desired outcome**.

The techniques outlined will continue evolving as models improve. Smarter models require less prescriptive engineering, allowing agents to operate with more autonomy. But even as capabilities scale, treating context as a precious, finite resource will remain central to building reliable, effective agents.
