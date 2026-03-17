"""
AI Module - Unified LLM API abstraction layer.

This module provides a unified interface for interacting with different
LLM providers, with automatic model discovery, provider configuration,
token and cost tracking, and simple context persistence.
"""

from .api_registry import (
    ApiProvider,
    register_api_provider,
    get_api_provider,
    get_api_providers,
    clear_api_providers,
)
from .env_api_keys import get_env_api_key
from .models import (
    register_models,
    get_model,
    get_providers,
    get_models,
    calculate_cost,
    supports_xhigh,
    models_are_equal,
)
from .providers.simple_options import (
    build_base_options,
    clamp_reasoning,
    adjust_max_tokens_for_thinking,
)
from .providers.transform_messages import transform_messages
from .stream import (
    stream,
    complete,
    stream_simple,
    complete_simple,
)
from .core_types import (
    # API and Provider types
    KnownApi,
    Api,
    KnownProvider,
    Provider,
    # Thinking types
    ThinkingLevel,
    ThinkingBudgets,
    # Stream options
    CacheRetention,
    Transport,
    StreamOptions,
    SimpleStreamOptions,
    # Content types
    TextContent,
    ThinkingContent,
    ImageContent,
    ToolCall,
    ContentBlock,
    # Usage types
    UsageCost,
    Usage,
    # Stop reason
    StopReason,
    # Message types
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    Message,
    # Tool definition
    Tool,
    ToolParameterSchema,
    # Context
    Context,
    # Streaming events
    StartEvent,
    TextStartEvent,
    TextDeltaEvent,
    TextEndEvent,
    ThinkingStartEvent,
    ThinkingDeltaEvent,
    ThinkingEndEvent,
    ToolCallStartEvent,
    ToolCallDeltaEvent,
    ToolCallEndEvent,
    DoneEvent,
    ErrorEvent,
    AssistantMessageEvent,
    # Model types
    OpenRouterRouting,
    VercelGatewayRouting,
    OpenAICompletionsCompat,
    OpenAIResponsesCompat,
    ModelCost,
    Model,
)
from .utils.event_stream import (
    EventStream,
    AssistantMessageEventStream,
    create_assistant_message_event_stream,
)
from .utils.json_parse import (
    parse_streaming_json,
    extract_partial_string_value,
)
from .utils.overflow import (
    is_context_overflow,
    get_overflow_patterns,
)
from .utils.sanitize_unicode import (
    sanitize_surrogates,
    is_valid_unicode,
    normalize_unicode,
)
from .utils.validation import (
    validate_tool_call,
    validate_tool_arguments,
)

__all__ = [
    # API and Provider types
    "KnownApi",
    "Api",
    "KnownProvider",
    "Provider",
    # Thinking types
    "ThinkingLevel",
    "ThinkingBudgets",
    # Stream options
    "CacheRetention",
    "Transport",
    "StreamOptions",
    "SimpleStreamOptions",
    # Content types
    "TextContent",
    "ThinkingContent",
    "ImageContent",
    "ToolCall",
    "ContentBlock",
    # Usage types
    "UsageCost",
    "Usage",
    # Stop reason
    "StopReason",
    # Message types
    "UserMessage",
    "AssistantMessage",
    "ToolResultMessage",
    "Message",
    # Tool definition
    "Tool",
    "ToolParameterSchema",
    # Context
    "Context",
    # Streaming events
    "StartEvent",
    "TextStartEvent",
    "TextDeltaEvent",
    "TextEndEvent",
    "ThinkingStartEvent",
    "ThinkingDeltaEvent",
    "ThinkingEndEvent",
    "ToolCallStartEvent",
    "ToolCallDeltaEvent",
    "ToolCallEndEvent",
    "DoneEvent",
    "ErrorEvent",
    "AssistantMessageEvent",
    # Model types
    "OpenRouterRouting",
    "VercelGatewayRouting",
    "OpenAICompletionsCompat",
    "OpenAIResponsesCompat",
    "ModelCost",
    "Model",
    # Event stream
    "EventStream",
    "AssistantMessageEventStream",
    "create_assistant_message_event_stream",
    # Validation
    "validate_tool_call",
    "validate_tool_arguments",
    # JSON parsing
    "parse_streaming_json",
    "extract_partial_string_value",
    # Overflow detection
    "is_context_overflow",
    "get_overflow_patterns",
    # Unicode sanitization
    "sanitize_surrogates",
    "is_valid_unicode",
    "normalize_unicode",
    # API registry
    "ApiProvider",
    "register_api_provider",
    "get_api_provider",
    "get_api_providers",
    "clear_api_providers",
    # Stream functions
    "stream",
    "complete",
    "stream_simple",
    "complete_simple",
    # Model management
    "register_models",
    "get_model",
    "get_providers",
    "get_models",
    "calculate_cost",
    "supports_xhigh",
    "models_are_equal",
    # Environment API keys
    "get_env_api_key",
    # Message transformation
    "transform_messages",
    # Simple options
    "build_base_options",
    "clamp_reasoning",
    "adjust_max_tokens_for_thinking",
]

