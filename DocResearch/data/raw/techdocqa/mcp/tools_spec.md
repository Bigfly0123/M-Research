---
title: MCP Tools Specification
source_url: https://modelcontextprotocol.io/specification/2025-03-26/server/tools
source_type: official_docs
topic: mcp_tools_spec
collected_at: 2026-05-18
---

# MCP Tools Specification

The Model Context Protocol (MCP) allows servers to expose tools that can be invoked by language models. Tools enable models to interact with external systems, such as querying databases, calling APIs, or performing computations. Each tool is uniquely identified by a name and includes metadata describing its schema.

## User Interaction Model

Tools in MCP are designed to be **model-controlled**, meaning that the language model can discover and invoke tools automatically based on its contextual understanding and the user's prompts.

However, implementations are free to expose tools through any interface pattern that suits their needs—the protocol itself does not mandate any specific user interaction model.

> **Trust & Safety**: For trust & safety and security, there **SHOULD** always be a human in the loop with the ability to deny tool invocations.
>
> Applications **SHOULD**:
> - Provide UI that makes clear which tools are being exposed to the AI model
> - Insert clear visual indicators when tools are invoked
> - Present confirmation prompts to the user for operations, to ensure a human is in the loop

## Capabilities

Servers that support tools **MUST** declare the `tools` capability:

```json
{
  "capabilities": {
    "tools": {
      "listChanged": true
    }
  }
}
```

`listChanged` indicates whether the server will emit notifications when the list of available tools changes.

## Protocol Messages

### Listing Tools

To discover available tools, clients send a `tools/list` request. This operation supports pagination.

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "method": "tools/list",
  "params": {
    "cursor": "optional-cursor-value"
  }
}
```

**Response:**

```json
{
  "jsonrpc": "2.0",
  "id": 1,
  "result": {
    "tools": [
      {
        "name": "get_weather",
        "description": "Get current weather information for a location",
        "inputSchema": {
          "type": "object",
          "properties": {
            "location": {
              "type": "string",
              "description": "City name or zip code"
            }
          },
          "required": ["location"]
        }
      }
    ],
    "nextCursor": "next-page-cursor"
  }
}
```

### Calling Tools

To invoke a tool, clients send a `tools/call` request:

**Request:**

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "method": "tools/call",
  "params": {
    "name": "get_weather",
    "arguments": {
      "location": "New York"
    }
  }
}
```

**Response:**

```json
{
  "jsonrpc": "2.0",
  "id": 2,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Current weather in New York:\nTemperature: 72°F\nConditions: Partly cloudy"
      }
    ],
    "isError": false
  }
}
```

### List Changed Notification

When the list of available tools changes, servers that declared the `listChanged` capability **SHOULD** send a notification:

```json
{
  "jsonrpc": "2.0",
  "method": "notifications/tools/list_changed"
}
```

## Message Flow

The typical message flow for tool interactions follows this sequence:

1. **Discovery**: Client sends `tools/list` to the Server; Server returns the list of available tools.
2. **Tool Selection**: The LLM selects a tool to use based on the conversation context and available tools.
3. **Invocation**: Client sends `tools/call` to the Server; Server returns the tool result; Client passes the result to the LLM.
4. **Updates**: Server sends `notifications/tools/list_changed` when tools change; Client fetches the updated tool list.

## Data Types

### Tool

A tool definition includes:

- **`name`**: Unique identifier for the tool (string)
- **`description`**: Human-readable description of functionality (string)
- **`inputSchema`**: JSON Schema defining expected parameters (object)
- **`annotations`**: Optional properties describing tool behavior (object)

> **Security Note**: For trust & safety and security, clients **MUST** consider tool annotations to be untrusted unless they come from trusted servers.

### Tool Result

Tool results can contain multiple content items of different types:

#### Text Content

```json
{
  "type": "text",
  "text": "Tool result text"
}
```

#### Image Content

```json
{
  "type": "image",
  "data": "base64-encoded-data",
  "mimeType": "image/png"
}
```

#### Audio Content

```json
{
  "type": "audio",
  "data": "base64-encoded-audio-data",
  "mimeType": "audio/wav"
}
```

#### Embedded Resources

Resources **MAY** be embedded to provide additional context or data, behind a URI that can be subscribed to or fetched again by the client later:

```json
{
  "type": "resource",
  "resource": {
    "uri": "resource://example",
    "mimeType": "text/plain",
    "text": "Resource content"
  }
}
```

## Error Handling

Tools use two error reporting mechanisms:

### 1. Protocol Errors

Standard JSON-RPC errors for issues like unknown tools, invalid arguments, or server errors:

```json
{
  "jsonrpc": "2.0",
  "id": 3,
  "error": {
    "code": -32602,
    "message": "Unknown tool: invalid_tool_name"
  }
}
```

### 2. Tool Execution Errors

Reported in tool results with `isError: true`:

```json
{
  "jsonrpc": "2.0",
  "id": 4,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "Failed to fetch weather data: API rate limit exceeded"
      }
    ],
    "isError": true
  }
}
```

Tool execution errors indicate that the tool was found and its arguments were valid, but the execution itself failed (e.g., API failure, business logic error).

## Tool Annotations

Tool annotations provide metadata about tool behavior that helps clients make informed decisions about tool usage. Common annotations include:

- **`readOnlyHint`**: Indicates the tool only reads data and does not modify state.
- **`destructiveHint`**: Indicates the tool may have destructive side effects.
- **`idempotentHint`**: Indicates calling the tool multiple times with the same arguments produces the same result.
- **`openWorldHint`**: Indicates the tool may interact with entities outside the server's knowledge.

## Security Considerations

1. **Servers MUST**:
   - Validate all tool inputs
   - Implement proper access controls
   - Rate limit tool invocations
   - Sanitize tool outputs

2. **Clients SHOULD**:
   - Prompt for user confirmation on sensitive operations
   - Show tool inputs to the user before calling the server, to avoid malicious or accidental data exfiltration
   - Validate tool results before passing to LLM
   - Implement timeouts for tool calls
   - Log tool usage for audit purposes

## Implementation Example

### Server-Side (Python)

```python
from mcp.server import Server

server = Server("weather-server")

@server.tool()
async def get_weather(location: str) -> str:
    """Get current weather for a location."""
    # Validate input
    if not location:
        raise ValueError("Location is required")
    
    # Fetch weather data
    weather_data = await fetch_weather_api(location)
    
    # Return formatted result
    return f"Temperature: {weather_data.temp}°F, Conditions: {weather_data.conditions}"

@server.tool()
async def get_forecast(location: str, days: int = 7) -> str:
    """Get weather forecast for a location."""
    forecast = await fetch_forecast_api(location, days)
    return format_forecast(forecast)
```

### Client-Side

```python
from mcp.client import Client

client = Client()

# Discover available tools
tools = await client.list_tools()

# Call a tool
result = await client.call_tool("get_weather", {"location": "New York"})
print(result.content[0].text)  # "Temperature: 72°F, Conditions: Partly cloudy"
```

## Relationship to Other MCP Features

Tools work alongside other MCP features:

- **Resources**: Read-only data that servers expose (complementary to tools for data access).
- **Prompts**: Reusable prompt templates that can include tool references.
- **Sampling**: Allows servers to request LLM completions, enabling agentic loops.

Tools are the primary mechanism for **mutating state** or **taking action** in MCP, while resources are preferred for **reading data** without side effects.
