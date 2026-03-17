"""
Utility modules for the AI package.
"""

from .event_stream import (
    EventStream,
    AssistantMessageEventStream,
    create_assistant_message_event_stream,
)
from .json_parse import (
    parse_streaming_json,
    extract_partial_string_value,
)
from .overflow import (
    is_context_overflow,
    get_overflow_patterns,
)
from .sanitize_unicode import (
    sanitize_surrogates,
    is_valid_unicode,
    normalize_unicode,
)
from .validation import (
    validate_tool_call,
    validate_tool_arguments,
)

__all__ = [
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
]

