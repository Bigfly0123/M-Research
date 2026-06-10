---
title: LangGraph Agentic RAG Tutorial
source_url: https://langchain-ai.github.io/langgraph/tutorials/agentic_rag/
source_type: official_docs
topic: langgraph_agentic_rag
collected_at: 2026-05-18
---

# Agentic RAG with LangGraph

Agentic RAG (Retrieval-Augmented Generation) is an advanced pattern where an LLM agent autonomously decides when and how to retrieve information, rather than following a fixed retrieve-then-generate pipeline. LangGraph provides the ideal framework for building agentic RAG systems because it supports stateful, multi-step workflows with conditional branching.

## Why Agentic RAG?

Traditional RAG pipelines follow a rigid flow: embed the query → retrieve documents → generate a response. This approach has several limitations:

- **No self-correction**: If the retrieved documents are irrelevant, the system cannot try again with a better query.
- **No multi-step reasoning**: Complex questions may require multiple retrieval steps.
- **No tool selection**: The system always uses the same retrieval strategy.

Agentic RAG addresses these limitations by giving the LLM control over the retrieval process. The agent can:

1. Decide whether retrieval is needed at all
2. Reformulate queries for better retrieval
3. Try multiple retrieval strategies
4. Evaluate retrieved documents for relevance
5. Decide whether to retrieve more or generate a final answer

## Architecture

The core architecture of an Agentic RAG system in LangGraph consists of:

### State Definition

```python
from typing import Annotated, TypedDict
from langchain_core.messages import BaseMessage
import operator

class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], operator.add]
    documents: list
    iteration: int
```

### Graph Structure

```python
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode

# Define the graph
graph = StateGraph(AgentState)

# Add the agent node (LLM with tools)
graph.add_node("agent", agent_fn)

# Add the retrieval tool node
graph.add_node("retrieve", retrieve_fn)

# Add the grade documents node
graph.add_node("grade_documents", grade_fn)

# Add the rewrite query node
graph.add_node("rewrite_query", rewrite_fn)

# Add the generate node
graph.add_node("generate", generate_fn)

# Define edges
graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", route_after_agent)
graph.add_edge("retrieve", "grade_documents")
graph.add_conditional_edges("grade_documents", route_after_grade)
graph.add_edge("rewrite_query", "retrieve")
graph.add_edge("generate", END)
```

## Implementation Steps

### Step 1: Define Retrieval Tools

The agent needs tools to interact with the retrieval system:

```python
from langchain_core.tools import tool

@tool
def retriever_tool(query: str) -> str:
    """Search and return relevant documents from the knowledge base."""
    docs = vectorstore.similarity_search(query, k=4)
    if not docs:
        return "No relevant documents found."
    return "\n\n".join(doc.page_content for doc in docs)

@tool
def web_search_tool(query: str) -> str:
    """Search the web for information not available in the knowledge base."""
    return web_search.run(query)
```

### Step 2: Create the Agent Node

The agent node uses an LLM bound with tools to decide what to do:

```python
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage

tools = [retriever_tool, web_search_tool]
llm_with_tools = ChatOpenAI(model="gpt-4").bind_tools(tools)

def agent_fn(state: AgentState) -> dict:
    system = SystemMessage(content=(
        "You are a helpful assistant. Use the retriever tool to search the "
        "knowledge base first. If you can't find relevant information, "
        "use the web search tool. Always cite your sources."
    ))
    response = llm_with_tools.invoke([system] + state["messages"])
    return {"messages": [response]}
```

### Step 3: Document Grading

After retrieval, the agent grades the documents for relevance:

```python
from pydantic import BaseModel, Field

class GradeDocuments(BaseModel):
    """Score for document relevance."""
    score: str = Field(description="Document relevance: 'relevant' or 'irrelevant'")

grade_llm = ChatOpenAI(model="gpt-4").with_structured_output(GradeDocuments)

def grade_fn(state: AgentState) -> dict:
    """Grade retrieved documents for relevance to the question."""
    question = state["messages"][0].content
    docs = state["documents"]
    
    filtered_docs = []
    for doc in docs:
        score = grade_llm.invoke(
            f"Is this document relevant to the question: {question}?\n\n"
            f"Document: {doc.page_content}"
        )
        if score.score == "relevant":
            filtered_docs.append(doc)
    
    return {"documents": filtered_docs}
```

### Step 4: Query Rewriting

If no relevant documents are found, the query can be rewritten:

```python
def rewrite_fn(state: AgentState) -> dict:
    """Rewrite the query to improve retrieval results."""
    question = state["messages"][0].content
    
    rewritten = ChatOpenAI(model="gpt-4").invoke(
        f"Rephrase this question to be more specific and better suited "
        f"for a vector search: {question}"
    )
    return {"messages": [HumanMessage(content=rewritten.content)]}
```

### Step 5: Generate the Final Answer

```python
def generate_fn(state: AgentState) -> dict:
    """Generate the final answer based on retrieved documents."""
    question = state["messages"][0].content
    docs = state["documents"]
    context = "\n\n".join(doc.page_content for doc in docs)
    
    response = ChatOpenAI(model="gpt-4").invoke(
        f"Answer the question based on the following context.\n\n"
        f"Context: {context}\n\nQuestion: {question}"
    )
    return {"messages": [AIMessage(content=response.content)]}
```

### Step 6: Routing Functions

Conditional edges route the workflow based on the current state:

```python
def route_after_agent(state: AgentState) -> str:
    """Route after the agent decides what to do."""
    last_message = state["messages"][-1]
    if last_message.tool_calls:
        return "retrieve"
    return "generate"

def route_after_grade(state: AgentState) -> str:
    """Route after grading documents."""
    if not state["documents"]:
        return "rewrite_query"
    return "generate"
```

## Advanced Patterns

### Self-RAG

Self-RAG extends Agentic RAG with reflection capabilities. The agent can:

1. Generate an answer
2. Reflect on whether the answer is faithful to the retrieved context
3. If not faithful, retry with different retrieval or generation strategy

```python
def reflect_on_answer(state: AgentState) -> dict:
    """Reflect on whether the generated answer is faithful to the documents."""
    answer = state["messages"][-1].content
    docs = state["documents"]
    context = "\n".join(doc.page_content for doc in docs)
    
    reflection = llm.invoke(
        f"Is this answer faithful to the context? Answer 'yes' or 'no'.\n\n"
        f"Context: {context}\n\nAnswer: {answer}"
    )
    return {"reflection": reflection.content}
```

### Corrective RAG (CRAG)

Corrective RAG adds a corrective step that can route to web search when local retrieval fails:

```python
def corrective_route(state: AgentState) -> str:
    """Route based on document quality assessment."""
    docs = state["documents"]
    
    if len(docs) >= 2:  # Enough relevant documents
        return "generate"
    elif len(docs) == 1:  # Marginal relevance, supplement with web
        return "web_search"
    else:  # No relevant documents, rely on web
        return "web_search"
```

### Multi-Index Retrieval

For systems with multiple knowledge bases, the agent can select which index(es) to query:

```python
@tool
def search_technical_docs(query: str) -> str:
    """Search technical documentation."""
    return tech_vectorstore.similarity_search(query, k=4)

@tool
def search_business_docs(query: str) -> str:
    """Search business documentation."""
    return biz_vectorstore.similarity_search(query, k=4)

@tool
def search_code_examples(query: str) -> str:
    """Search code examples and snippets."""
    return code_vectorstore.similarity_search(query, k=4)
```

## Putting It All Together

```python
# Build the complete graph
graph = StateGraph(AgentState)

graph.add_node("agent", agent_fn)
graph.add_node("retrieve", ToolNode([retriever_tool]))
graph.add_node("grade_documents", grade_fn)
graph.add_node("rewrite_query", rewrite_fn)
graph.add_node("generate", generate_fn)

graph.add_edge(START, "agent")
graph.add_conditional_edges("agent", route_after_agent, {
    "retrieve": "retrieve",
    "generate": "generate"
})
graph.add_edge("retrieve", "grade_documents")
graph.add_conditional_edges("grade_documents", route_after_grade, {
    "rewrite_query": "rewrite_query",
    "generate": "generate"
})
graph.add_edge("rewrite_query", "agent")
graph.add_edge("generate", END)

# Compile and run
app = graph.compile()
result = app.invoke({"messages": [HumanMessage(content="What is LangGraph?")]})
```

## Benefits of LangGraph for Agentic RAG

1. **Stateful execution**: The graph maintains full state across retrieval and generation steps.
2. **Conditional routing**: Flexible control flow based on retrieval quality.
3. **Human-in-the-loop**: Pause for human review before generating answers.
4. **Checkpointing**: Resume long-running RAG workflows after failures.
5. **Streaming**: Stream intermediate results for real-time user feedback.
6. **Observability**: Full tracing of retrieval and reasoning steps via LangSmith.

## References

- [LangGraph Documentation](https://docs.langchain.com/oss/python/langgraph/overview)
- [LangGraph Quickstart](https://docs.langchain.com/oss/python/langgraph/quickstart)
- [Self-RAG Paper](https://arxiv.org/abs/2310.11511)
- [Corrective RAG Paper](https://arxiv.org/abs/2401.15884)
