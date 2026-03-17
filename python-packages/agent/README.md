# pi-agent-core

General-purpose agent with state management and event streaming.

## Features

- **Stateful Agent**: Manage agent state, messages, and tools
- **Event Streaming**: Real-time event notifications for agent lifecycle
- **Tool Execution**: Support for tool definitions and execution
- **Message Queue**: Steering (interruption) and follow-up message queues
- **Async/Await**: Fully async/await compatible

## Installation

```bash
pip install pi-agent-core
```

## Quick Start

```python
from pi_agent_core import Agent, Model, ThinkingLevel

# Create an agent
agent = Agent()

# Configure the agent
agent.set_system_prompt("You are a helpful assistant.")
agent.set_model(Model(api="openai-chat", provider="openai", id="gpt-4o"))
agent.set_thinking_level(ThinkingLevel.HIGH)

# Subscribe to events
agent.subscribe(lambda event: print(f"Event: {event['type']}"))

# Run the agent
await agent.prompt("Hello, how can you help me?")
```

## API Reference

### Agent

Main agent class for managing state, messages, and tool execution.

#### Constructor

```python
agent = Agent(opts: Optional[AgentOptions] = None)
```

#### Methods

- `set_system_prompt(prompt: str)` - Set the system prompt
- `set_model(model: Model)` - Set the LLM model to use
- `set_thinking_level(level: ThinkingLevel)` - Set the thinking/reasoning level
- `set_tools(tools: List[AgentTool])` - Set available tools
- `subscribe(fn: Callable[[AgentEvent], None]) -> Callable[[], None]` - Subscribe to agent events
- `async prompt(input: Union[str, AgentMessage, List[AgentMessage]], images: Optional[List[ImageContent]] = None)` - Send a prompt to the agent
- `async continue_()` - Continue from the current context
- `abort()` - Abort the current operation
- `async wait_for_idle()` - Wait for the agent to become idle
- `reset()` - Reset agent state

#### Properties

- `state: AgentState` - Get the current agent state
- `session_id: Optional[str]` - Get/set the session ID
- `thinking_budgets: Optional[Dict[str, int]]` - Get/set thinking budgets
- `transport: str` - Get the current transport method
- `max_retry_delay_ms: Optional[int]` - Get/set max retry delay

### Types

#### Content Types

- `TextContent` - Text content
- `ImageContent` - Image content (base64 encoded)
- `ThinkingContent` - Thinking/reasoning content
- `ToolCall` - Tool call content

#### Message Types

- `UserMessage` - User message
- `AssistantMessage` - Assistant/LLM response message
- `ToolResultMessage` - Tool execution result message

#### Agent State

- `AgentState` - Current agent state including messages, tools, and configuration

#### Event Types

- `AgentStartEvent` - Agent started
- `AgentEndEvent` - Agent ended
- `TurnStartEvent` - New turn (LLM call + tool execution) started
- `TurnEndEvent` - Turn completed
- `MessageStartEvent` - Message started
- `MessageUpdateEvent` - Message updated (streaming)
- `MessageEndEvent` - Message ended
- `ToolExecutionStartEvent` - Tool execution started
- `ToolExecutionUpdateEvent` - Tool execution progress update
- `ToolExecutionEndEvent` - Tool execution ended

## License

MIT

