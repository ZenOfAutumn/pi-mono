"""
pi-agent-core package.

A stateful agent with tool execution and event streaming.
"""

# Core Agent
from .agent import Agent, AgentOptions
# Loop functions
from .agent_loop import agent_loop, agent_loop_continue
# Types
from .types import (
    # Content types
    TextContent,
    ImageContent,
    ThinkingContent,
    ToolCall,
    Content,
    # Messages
    Message,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    MessageUnion,
    # Model and context
    Model,
    Context,
    AgentContext,
    # State
    AgentState,
    AgentMessage,
    # Tools
    Tool,
    AgentTool,
    AgentToolResult,
    AgentToolUpdateCallback,
    # Events
    AgentEvent,
    AgentStartEvent,
    AgentEndEvent,
    TurnStartEvent,
    TurnEndEvent,
    MessageStartEvent,
    MessageUpdateEvent,
    MessageEndEvent,
    ToolExecutionStartEvent,
    ToolExecutionUpdateEvent,
    ToolExecutionEndEvent,
    # Config
    AgentLoopConfig,
    SimpleStreamOptions,
    ThinkingLevel,
    StreamFn,
    Usage,
)

__all__ = [
    # Agent
    "Agent",
    "AgentOptions",
    # Loop functions
    "agent_loop",
    "agent_loop_continue",
    # Content types
    "TextContent",
    "ImageContent",
    "ThinkingContent",
    "ToolCall",
    "Content",
    # Messages
    "Message",
    "UserMessage",
    "AssistantMessage",
    "ToolResultMessage",
    "MessageUnion",
    # Model and context
    "Model",
    "Context",
    "AgentContext",
    # State
    "AgentState",
    "AgentMessage",
    # Tools
    "Tool",
    "AgentTool",
    "AgentToolResult",
    "AgentToolUpdateCallback",
    # Events
    "AgentEvent",
    "AgentStartEvent",
    "AgentEndEvent",
    "TurnStartEvent",
    "TurnEndEvent",
    "MessageStartEvent",
    "MessageUpdateEvent",
    "MessageEndEvent",
    "ToolExecutionStartEvent",
    "ToolExecutionUpdateEvent",
    "ToolExecutionEndEvent",
    # Config
    "AgentLoopConfig",
    "SimpleStreamOptions",
    "ThinkingLevel",
    "StreamFn",
    "Usage",
]

