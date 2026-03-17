"""
提供商模块。

本模块包含各种 LLM API 提供商的实现，
包括消息转换、选项构建和流式调用功能。
"""

# Friday Responses API
from .friday_config import (
    FRIDAY_RESPONSES_API_URL,
    DEFAULT_FRIDAY_MODEL,
    FridayAuthConfig,
    FridayResponsesOptions,
    FridayStreamEventType,
    build_friday_request_params,
)
from .friday_responses import (
    stream_friday_responses,
    stream_simple_friday_responses,
    convert_messages_to_friday,
    convert_tools_to_friday,
)
from .simple_options import (
    build_base_options,
    clamp_reasoning,
    adjust_max_tokens_for_thinking,
)
from .transform_messages import transform_messages

__all__ = [
    # 消息转换
    "transform_messages",
    # 选项构建
    "build_base_options",
    "clamp_reasoning",
    "adjust_max_tokens_for_thinking",
    # Friday 配置
    "FRIDAY_RESPONSES_API_URL",
    "DEFAULT_FRIDAY_MODEL",
    "FridayAuthConfig",
    "FridayResponsesOptions",
    "FridayStreamEventType",
    "build_friday_request_params",
    # Friday 流函数
    "stream_friday_responses",
    "stream_simple_friday_responses",
    "convert_messages_to_friday",
    "convert_tools_to_friday",
]

