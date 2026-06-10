---
title: OpenAI Agents SDK - Tools and Guardrails
source_url: https://openai.github.io/openai-agents-python/tools/
source_type: official_docs
topic: openai_agents_tools
collected_at: 2026-05-18
---

# OpenAI Agents SDK - Tools

Tools let agents take actions: things like fetching data, running code, calling external APIs, and even using a computer. The SDK supports five categories:

- **Hosted OpenAI tools**: Run alongside the model on OpenAI servers.
- **Local/runtime execution tools**: `ComputerTool` and `ApplyPatchTool` always run in your environment, while `ShellTool` can run locally or in a hosted container.
- **Function calling**: Wrap any Python function as a tool.
- **Agents as tools**: Expose an agent as a callable tool without a full handoff.
- **Experimental: Codex tool**: Run workspace-scoped Codex tasks from a tool call.

## Choosing a Tool Type

| If you want to... | Start here |
|---|---|
| Use OpenAI-managed tools (web search, file search, code interpreter, hosted MCP, image generation) | Hosted tools |
| Defer large tool surfaces until runtime with tool search | Hosted tool search |
| Run tools in your own process or environment | Local runtime tools |
| Wrap Python functions as tools | Function tools |
| Let one agent call another without a handoff | Agents as tools |
| Run workspace-scoped Codex tasks from an agent | Experimental: Codex tool |

## Hosted Tools

OpenAI offers built-in tools when using the `OpenAIResponsesModel`:

- **`WebSearchTool`** — Lets an agent search the web.
- **`FileSearchTool`** — Retrieves information from your OpenAI Vector Stores.
- **`CodeInterpreterTool`** — Lets the LLM execute code in a sandboxed environment.
- **`HostedMCPTool`** — Exposes a remote MCP server's tools to the model.
- **`ImageGenerationTool`** — Generates images from a prompt.
- **`ToolSearchTool`** — Lets the model load deferred tools, namespaces, or hosted MCP servers on demand.

```python
from agents import Agent, FileSearchTool, Runner, WebSearchTool

agent = Agent(
    name="Assistant",
    tools=[
        WebSearchTool(),
        FileSearchTool(
            max_num_results=3,
            vector_store_ids=["VECTOR_STORE_ID"],
        ),
    ],
)

async def main():
    result = await Runner.run(agent, "Which coffee shop should I go to?")
    print(result.final_output)
```

### Hosted Tool Search

Tool search lets OpenAI Responses models defer large tool surfaces until runtime, so the model loads only the subset it needs for the current turn. This reduces tool-schema tokens without exposing every tool up front.

```python
from typing import Annotated
from agents import Agent, Runner, ToolSearchTool, function_tool, tool_namespace

@function_tool(defer_loading=True)
def get_customer_profile(
    customer_id: Annotated[str, "The customer ID to look up."],
) -> str:
    """Fetch a CRM customer profile."""
    return f"profile for {customer_id}"

crm_tools = tool_namespace(
    name="crm",
    description="CRM tools for customer lookups.",
    tools=[get_customer_profile, list_open_orders],
)

agent = Agent(
    name="Operations assistant",
    model="gpt-5.5",
    instructions="Load the crm namespace before using CRM tools.",
    tools=[*crm_tools, ToolSearchTool()],
)
```

Key points:
- Available only with OpenAI Responses models (`openai>=2.25.0`).
- Add exactly one `ToolSearchTool()` per agent with deferred-loading surfaces.
- Use `tool_namespace()` to group related tools (e.g., `crm`, `billing`, `shipping`).
- Keep each namespace small, ideally fewer than 10 functions.
- Prefer namespaces or hosted MCP servers over many individually deferred functions.

## Function Tools

You can use any Python function as a tool. The SDK sets it up automatically:

- **Name**: The function name (or override via `name_override`)
- **Description**: Extracted from the docstring
- **Schema**: Auto-created from function arguments
- **Argument descriptions**: From docstring (unless disabled)

```python
from agents import Agent, FunctionTool, RunContextWrapper, function_tool

@function_tool
async def fetch_weather(location: dict) -> str:
    """Fetch the weather for a given location.

    Args:
        location: The location to fetch the weather for.
    """
    return "sunny"

@function_tool(name_override="fetch_data")
def read_file(ctx: RunContextWrapper, path: str, directory: str | None = None) -> str:
    """Read the contents of a file.

    Args:
        path: The path to the file to read.
        directory: The directory to read the file from.
    """
    return "<file contents>"

agent = Agent(name="Assistant", tools=[fetch_weather, read_file])
```

### Custom Function Tools

For more control, create a `FunctionTool` directly:

```python
from pydantic import BaseModel
from agents import RunContextWrapper, FunctionTool

class FunctionArgs(BaseModel):
    username: str
    age: int

async def run_function(ctx: RunContextWrapper, args: str) -> str:
    parsed = FunctionArgs.model_validate_json(args)
    return f"{parsed.username} is {parsed.age} years old"

tool = FunctionTool(
    name="process_user",
    description="Processes extracted user data",
    params_json_schema=FunctionArgs.model_json_schema(),
    on_invoke_tool=run_function,
)
```

### Pydantic Field Constraints

Use Pydantic's `Field` to add constraints and descriptions:

```python
from typing import Annotated
from pydantic import Field
from agents import function_tool

@function_tool
def score_a(score: int = Field(..., ge=0, le=100, description="Score 0-100")) -> str:
    return f"Score recorded: {score}"

@function_tool
def score_b(score: Annotated[int, Field(..., ge=0, le=100, description="Score 0-100")]) -> str:
    return f"Score recorded: {score}"
```

### Function Tool Timeouts

```python
import asyncio
from agents import Agent, Runner, function_tool

@function_tool(timeout=2.0)
async def slow_lookup(query: str) -> str:
    await asyncio.sleep(10)
    return f"Result for {query}"
```

Timeout behaviors:
- `timeout_behavior="error_as_result"` (default): Returns a timeout message to the model.
- `timeout_behavior="raise_exception"`: Raises `ToolTimeoutError` and fails the run.
- `timeout_error_function=...`: Customizes the timeout message.

### Error Handling in Function Tools

```python
from agents import function_tool, RunContextWrapper

def my_custom_error_function(context: RunContextWrapper, error: Exception) -> str:
    """Custom function for user-friendly error message."""
    print(f"Tool call failed: {error}")
    return "An internal server error occurred. Please try again later."

@function_tool(failure_error_function=my_custom_error_function)
def get_user_profile(user_id: str) -> str:
    """Fetches a user profile from a mock API."""
    if user_id == "user_123":
        return "User profile for user_123 successfully retrieved."
    else:
        raise ValueError(f"Could not retrieve profile for {user_id}.")
```

## Agents as Tools

Model agents as tools for orchestration without full handoffs:

```python
from agents import Agent, Runner

spanish_agent = Agent(
    name="Spanish agent",
    instructions="You translate the user's message to Spanish",
)

french_agent = Agent(
    name="French agent",
    instructions="You translate the user's message to French",
)

orchestrator_agent = Agent(
    name="orchestrator_agent",
    instructions="You are a translation agent. You use the tools to translate.",
    tools=[
        spanish_agent.as_tool(
            tool_name="translate_to_spanish",
            tool_description="Translate the user's message to Spanish",
        ),
        french_agent.as_tool(
            tool_name="translate_to_french",
            tool_description="Translate the user's message to French",
        ),
    ],
)
```

### Structured Input for Tool-Agents

By default, `Agent.as_tool()` expects a single string input. Pass a Pydantic model for structured input:

```python
from pydantic import BaseModel, Field

class TranslationInput(BaseModel):
    text: str = Field(description="Text to translate.")
    source: str = Field(description="Source language.")
    target: str = Field(description="Target language.")

translator_tool = translator_agent.as_tool(
    tool_name="translate_text",
    tool_description="Translate text between languages.",
    parameters=TranslationInput,
    include_input_schema=True,
)
```

### Approval Gates for Tool-Agents

`Agent.as_tool(..., needs_approval=...)` uses the same approval flow as `function_tool`. If approval is required, the run pauses and pending items appear in `result.interruptions`.

## Local Runtime Tools

Local runtime tools execute outside the model response. The model decides when to call them, but your application performs the actual work.

- **`ComputerTool`**: Implement the `Computer` or `AsyncComputer` interface for GUI/browser automation.
- **`ShellTool`**: Run shell commands locally or in a hosted container.
- **`ApplyPatchTool`**: Implement `ApplyPatchEditor` to apply diffs locally.

```python
from agents import Agent, ShellTool, ApplyPatchTool
from agents.computer import AsyncComputer
from agents.editor import ApplyPatchEditor

async def run_shell(request):
    return "shell output"

agent = Agent(
    name="Local tools agent",
    tools=[
        ShellTool(executor=run_shell),
        ApplyPatchTool(editor=MyEditor()),
    ],
)
```

## Guardrails

Guardrails provide safety and validation layers for agent interactions. The SDK supports two types:

### Input Guardrails

Run before the agent processes user input:

```python
from agents import Agent, Runner, GuardrailFunctionOutput, input_guardrail

@input_guardrail
async def check_sensitive_info(ctx, agent, input):
    """Prevent sensitive information from being processed."""
    if "password" in input.lower():
        return GuardrailFunctionOutput(
            output_info="Input contains sensitive information",
            tripwire_triggered=True,
        )
    return GuardrailFunctionOutput(output_info=None, tripwire_triggered=False)
```

### Output Guardrails

Run after the agent produces output:

```python
from agents import output_guardrail

@output_guardrail
async def check_for_hallucination(ctx, agent, output):
    """Validate the agent's output for accuracy."""
    # Check against known facts or patterns
    return GuardrailFunctionOutput(output_info=None, tripwire_triggered=False)
```

When a guardrail's `tripwire_triggered` is `True`, the run is terminated with a `GuardrailTripwireTriggered` exception.
