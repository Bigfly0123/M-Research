---
title: LangGraph StateGraph Low-Level Concepts
source_url: https://langchain-ai.github.io/langgraph/concepts/low_level/
source_type: official_docs
topic: langgraph_stategraph
collected_at: 2026-05-18
---

# LangGraph Low-Level Concepts: StateGraph

LangGraph is a low-level orchestration framework for building, managing, and deploying long-running, stateful agents. It is inspired by [Pregel](https://research.google/pubs/pub37252/) and [Apache Beam](https://beam.apache.org/), with its public interface drawing inspiration from [NetworkX](https://networkx.org/documentation/latest/). LangGraph is built by LangChain Inc, the creators of LangChain, but can be used without LangChain.

## Why LangGraph?

LangGraph provides low-level supporting infrastructure for *any* long-running, stateful workflow or agent:

- **Durable execution** — Build agents that persist through failures and can run for extended periods, automatically resuming from exactly where they left off.
- **Human-in-the-loop** — Seamlessly incorporate human oversight by inspecting and modifying agent state at any point during execution.
- **Comprehensive memory** — Create truly stateful agents with both short-term working memory for ongoing reasoning and long-term persistent memory across sessions.
- **Debugging with LangSmith** — Gain deep visibility into complex agent behavior with visualization tools that trace execution paths, capture state transitions, and provide detailed runtime metrics.
- **Production-ready deployment** — Deploy sophisticated agent systems confidently with scalable infrastructure designed to handle the unique challenges of stateful, long-running workflows.

## Core Abstractions

### StateGraph

`StateGraph` is the core class in LangGraph. It defines a graph where each node represents a step in your agent's workflow, and edges define the transitions between steps. The graph operates on a shared **state** object that is passed between nodes and updated at each step.

```python
from langgraph.graph import StateGraph, START, END
from typing import TypedDict

# Define the state schema
class AgentState(TypedDict):
    messages: list
    next_action: str

# Create a StateGraph
graph = StateGraph(AgentState)

# Add nodes
graph.add_node("agent", agent_function)
graph.add_node("tools", tool_function)

# Add edges
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", should_continue, {"continue": "tools", "end": END})
graph.add_edge("tools", "agent")

# Compile the graph
app = graph.compile()
```

### State

The **state** in LangGraph is the shared data structure that flows through the graph. It is typically defined as a `TypedDict` or a Pydantic model. Each node in the graph can read from and write to the state. LangGraph supports several state management patterns:

- **Overwrite**: The default reducer, where the new value replaces the old value.
- **Append**: Uses an `operator.add` reducer to append new values to a list.
- **Custom reducers**: You can define custom reducer functions for more complex state updates.

```python
from typing import Annotated
from typing_extensions import TypedDict
import operator

class State(TypedDict):
    messages: Annotated[list, operator.add]  # Appends new messages
    context: str  # Overwrites previous value
```

### Nodes

Nodes are the building blocks of a LangGraph graph. Each node is a Python function (or coroutine) that takes the current state as input and returns a partial state update. Nodes can:

- Call LLMs
- Execute tools
- Make decisions
- Transform data
- Interact with external systems

```python
def agent_node(state: AgentState) -> dict:
    """The agent node calls the LLM and decides what to do next."""
    response = llm.invoke(state["messages"])
    return {"messages": [response]}

def tool_node(state: AgentState) -> dict:
    """The tool node executes the selected tool."""
    tool_calls = state["messages"][-1].tool_calls
    results = [execute_tool(tc) for tc in tool_calls]
    return {"messages": results}
```

### Edges

Edges define the control flow of the graph. LangGraph supports several types of edges:

- **Normal edges**: Unconditional transitions from one node to another.
- **Conditional edges**: Transitions that depend on the current state, determined by a routing function.
- **Entry points**: Edges from `START` to the first node(s).
- **Exit points**: Edges to `END`, marking the completion of the graph.

```python
# Normal edge
graph.add_edge("tool_node", "agent_node")

# Conditional edge
def route_after_agent(state: AgentState) -> str:
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "tools"
    return "end"

graph.add_conditional_edges(
    "agent_node",
    route_after_agent,
    {"tools": "tool_node", "end": END}
)
```

## Key Features

### Subgraphs

Subgraphs allow you to compose complex workflows from simpler graphs. A subgraph is a graph that is used as a node within a parent graph. This enables modular design and reusability.

```python
from langgraph.graph import StateGraph

# Create a subgraph
child_graph = StateGraph(ChildState)
child_graph.add_node("step1", step1_fn)
child_graph.add_node("step2", step2_fn)
child_graph.add_edge("step1", "step2")
compiled_child = child_graph.compile()

# Use it as a node in the parent graph
parent_graph = StateGraph(ParentState)
parent_graph.add_node("child_process", compiled_child)
```

### Human-in-the-Loop

LangGraph supports interrupting execution at specific points to allow human review or input. This is critical for production deployments where human oversight is required.

```python
from langgraph.checkpoint.memory import MemorySaver

# Create a checkpointer for persistence
checkpointer = MemorySaver()

# Compile with interrupt before a specific node
app = graph.compile(
    checkpointer=checkpointer,
    interrupt_before=["human_review_node"]
)

# Run until the interrupt
result = app.invoke(initial_state, config={"configurable": {"thread_id": "1"}})

# Resume after human input
result = app.invoke(
    {"messages": [HumanMessage(content="Approved")]},
    config={"configurable": {"thread_id": "1"}}
)
```

### Checkpointing and Persistence

LangGraph provides built-in checkpointing to persist state across invocations. This enables:

- **Resuming execution**: Restart from the last checkpoint after failures.
- **Time travel**: Revert to previous states for debugging or replay.
- **Long-running workflows**: Execute workflows that span hours or days.

```python
from langgraph.checkpoint.sqlite import SqliteSaver

# Use SQLite for persistent checkpoints
with SqliteSaver.from_conn_string("checkpoints.db") as checkpointer:
    app = graph.compile(checkpointer=checkpointer)
    result = app.invoke(
        {"messages": [HumanMessage(content="Hello")]},
        config={"configurable": {"thread_id": "thread-1"}}
    )
```

### Streaming

LangGraph supports multiple streaming modes for real-time output:

- **`"values"`**: Streams the full state after each step.
- **`"updates"`**: Streams only the state updates (deltas) after each step.
- **`"messages"`**: Streams LLM message tokens as they are generated.

```python
# Stream updates
for event in app.stream(initial_state, stream_mode="updates"):
    print(event)

# Stream LLM tokens
for event in app.stream(initial_state, stream_mode="messages"):
    print(event)
```

## Common Patterns

### ReAct Agent Pattern

The ReAct (Reasoning + Acting) pattern is one of the most common agent architectures built with LangGraph:

1. **Agent node**: Calls the LLM to decide the next action
2. **Tool node**: Executes the selected tool
3. **Conditional edge**: Routes back to the agent or to the end based on the LLM's response

### Multi-Agent Pattern

Multiple agents can be orchestrated within a single LangGraph graph, each with its own specialized role:

```python
graph = StateGraph(AgentState)
graph.add_node("researcher", researcher_agent)
graph.add_node("coder", coder_agent)
graph.add_node("reviewer", reviewer_agent)
graph.add_conditional_edges("researcher", route_after_research, {"code": "coder", "end": END})
graph.add_edge("coder", "reviewer")
graph.add_conditional_edges("reviewer", route_after_review, {"revise": "coder", "approve": END})
```

### Branching and Parallel Execution

LangGraph supports fan-out/fan-in patterns where multiple nodes execute in parallel:

```python
# Fan-out: one node sends to multiple
graph.add_edge("router", "agent_a")
graph.add_edge("router", "agent_b")
graph.add_edge("router", "agent_c")

# Fan-in: multiple nodes converge to one
graph.add_edge("agent_a", "aggregator")
graph.add_edge("agent_b", "aggregator")
graph.add_edge("agent_c", "aggregator")
```

## LangGraph Ecosystem

While LangGraph can be used standalone, it integrates seamlessly with the LangChain ecosystem:

- **LangChain** — Provides integrations and composable components for LLM applications.
- **LangSmith** — Observability and evaluation for agent runs.
- **LangSmith Deployment** — Production deployment platform for long-running, stateful workflows.
- **Deep Agents** — A higher-level package built on LangGraph for agents that can plan, use subagents, and leverage file systems.

## Installation

```bash
pip install -U langgraph
```

For the JS/TS equivalent, see [LangGraph.js](https://github.com/langchain-ai/langgraphjs).
