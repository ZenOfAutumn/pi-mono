"""
Agent types for the pi-agent-core package.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    TypedDict,
    Union,
    Awaitable,
    Protocol,
    runtime_checkable,
)
from enum import Enum


# Forward declarations for types that would come from pi-ai
@dataclass
class TextContent:
    """Text content block."""
    type: Literal["text"] = "text"
    text: str = ""


@dataclass
class ImageContent:
    """Image content block."""
    type: Literal["image"] = "image"
    data: str = ""
    mime_type: str = "image/png"


@dataclass
class ThinkingContent:
    """Thinking content block."""
    type: Literal["thinking"] = "thinking"
    thinking: str = ""


@dataclass
class ToolCall:
    """Tool call content block."""
    type: Literal["toolCall"] = "toolCall"
    id: str = ""
    name: str = ""
    arguments: Dict[str, Any] = field(default_factory=dict)


Content = Union[TextContent, ImageContent, ThinkingContent, ToolCall]


@dataclass
class Usage:
    """Token usage information."""
    input: int = 0
    output: int = 0
    cache_read: int = 0
    cache_write: int = 0
    total_tokens: int = 0
    cost: Dict[str, float] = field(default_factory=lambda: {
        "input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0, "total": 0.0
    })


@dataclass
class Model:
    """Model configuration."""
    api: str
    provider: str
    id: str


@dataclass
class Message:
    """Base message type."""
    role: str
    content: List[Content]
    timestamp: int


@dataclass
class UserMessage(Message):
    """User message."""
    role: Literal["user"] = "user"


@dataclass
class AssistantMessage(Message):
    """Assistant message."""
    role: Literal["assistant"] = "assistant"
    api: str = ""
    provider: str = ""
    model: str = ""
    usage: Usage = field(default_factory=Usage)
    stop_reason: str = "stop"
    error_message: Optional[str] = None


@dataclass
class ToolResultMessage(Message):
    """Tool result message."""
    role: Literal["toolResult"] = "toolResult"
    tool_call_id: str = ""
    tool_name: str = ""
    details: Dict[str, Any] = field(default_factory=dict)
    is_error: bool = False


# Type aliases
MessageUnion = Union[UserMessage, AssistantMessage, ToolResultMessage]


class ThinkingLevel(str, Enum):
    """Thinking/reasoning level for models that support it."""
    OFF = "off"
    MINIMAL = "minimal"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    XHIGH = "xhigh"


@runtime_checkable
class StreamFn(Protocol):
    """Stream function protocol."""
    def __call__(
        self,
        model: Model,
        context: 'Context',
        options: Optional['SimpleStreamOptions'] = None,
    ) -> Awaitable['EventStream']:
        ...


class SimpleStreamOptions(TypedDict, total=False):
    """Simple stream options."""
    temperature: Optional[float]
    max_tokens: Optional[int]
    reasoning: Optional[str]
    session_id: Optional[str]
    api_key: Optional[str]
    signal: Optional[Any]  # Would be threading.Event or similar
    on_payload: Optional[Callable[[Dict[str, Any]], None]]
    transport: Optional[str]
    thinking_budgets: Optional[Dict[str, int]]
    max_retry_delay_ms: Optional[int]


@dataclass
class AgentLoopConfig:
    """
    Configuration for the agent loop.
    """
    model: Model
    # Converts AgentMessage[] to LLM-compatible Message[] before each LLM call.
    convert_to_llm: Callable[[List['AgentMessage']], Awaitable[List[MessageUnion]]]
    # Optional transform applied to the context before convertToLlm.
    transform_context: Optional[Callable[[List['AgentMessage'], Optional[Any]], Awaitable[List['AgentMessage']]]] = None
    # Resolves an API key dynamically for each LLM call.
    get_api_key: Optional[Callable[[str], Awaitable[Optional[str]]]] = None
    # Returns steering messages to inject into the conversation mid-run.
    get_steering_messages: Optional[Callable[[], Awaitable[List['AgentMessage']]]] = None
    # Returns follow-up messages to process after the agent would otherwise stop.
    get_follow_up_messages: Optional[Callable[[], Awaitable[List['AgentMessage']]]] = None
    # Additional options
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    reasoning: Optional[str] = None
    session_id: Optional[str] = None
    api_key: Optional[str] = None
    thinking_budgets: Optional[Dict[str, int]] = None


class CustomAgentMessages(TypedDict, total=False):
    """
    Extensible interface for custom app messages.
    Apps can extend by adding new keys.
    """
    pass


# AgentMessage: Union of LLM messages + custom messages.
AgentMessage = Union[Message, Dict[str, Any]]


@dataclass
class AgentState:
    """Agent state containing all configuration and conversation data."""
    system_prompt: str = ""
    model: Optional[Model] = None
    thinking_level: ThinkingLevel = ThinkingLevel.OFF
    tools: List['AgentTool'] = field(default_factory=list)
    messages: List[AgentMessage] = field(default_factory=list)
    is_streaming: bool = False
    stream_message: Optional[AgentMessage] = None
    pending_tool_calls: Set[str] = field(default_factory=set)
    error: Optional[str] = None


@dataclass
class AgentToolResult:
    """Result from a tool execution."""
    # Content blocks supporting text and images
    content: List[Union[TextContent, ImageContent]]
    # Details to be displayed in a UI or logged
    details: Dict[str, Any]


# Callback for streaming tool execution updates
AgentToolUpdateCallback = Callable[[AgentToolResult], None]


@dataclass
class Tool:
    """Base tool definition."""
    name: str
    description: str
    parameters: Dict[str, Any]  # JSON Schema


@dataclass
class AgentTool(Tool):
    """Agent tool with execution capability."""
    # A human-readable label for the tool to be displayed in UI
    label: str = ""
    # Execute function
    execute: Optional[Callable[
        [str, Dict[str, Any], Optional[Any], Optional[AgentToolUpdateCallback]],
        Awaitable[AgentToolResult]
    ]] = None


@dataclass
class AgentContext:
    """Agent context with tools."""
    system_prompt: str
    messages: List[AgentMessage]
    tools: Optional[List[AgentTool]] = None


@dataclass
class Context:
    """LLM context."""
    system_prompt: str
    messages: List[Message]
    tools: Optional[List[Tool]] = None


# Agent event types
@dataclass
class AgentStartEvent:
    """Agent lifecycle start event."""
    type: Literal["agent_start"] = "agent_start"


@dataclass
class AgentEndEvent:
    """Agent lifecycle end event."""
    type: Literal["agent_end"] = "agent_end"
    messages: List[AgentMessage] = field(default_factory=list)


@dataclass
class TurnStartEvent:
    """Turn lifecycle start event."""
    type: Literal["turn_start"] = "turn_start"


@dataclass
class TurnEndEvent:
    """Turn lifecycle end event."""
    type: Literal["turn_end"] = "turn_end"
    message: AgentMessage = None  # type: ignore
    tool_results: List[ToolResultMessage] = field(default_factory=list)


@dataclass
class MessageStartEvent:
    """Message lifecycle start event."""
    type: Literal["message_start"] = "message_start"
    message: AgentMessage = None  # type: ignore


@dataclass
class MessageUpdateEvent:
    """Message update event (only for assistant messages during streaming)."""
    type: Literal["message_update"] = "message_update"
    message: AgentMessage = None  # type: ignore
    assistant_message_event: Optional[Dict[str, Any]] = None


@dataclass
class MessageEndEvent:
    """Message lifecycle end event."""
    type: Literal["message_end"] = "message_end"
    message: AgentMessage = None  # type: ignore


@dataclass
class ToolExecutionStartEvent:
    """Tool execution start event."""
    type: Literal["tool_execution_start"] = "tool_execution_start"
    tool_call_id: str = ""
    tool_name: str = ""
    args: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolExecutionUpdateEvent:
    """Tool execution update event."""
    type: Literal["tool_execution_update"] = "tool_execution_update"
    tool_call_id: str = ""
    tool_name: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    partial_result: Any = None


@dataclass
class ToolExecutionEndEvent:
    """Tool execution end event."""
    type: Literal["tool_execution_end"] = "tool_execution_end"
    tool_call_id: str = ""
    tool_name: str = ""
    result: Any = None
    is_error: bool = False


# Union of all agent events
AgentEvent = Union[
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
]

