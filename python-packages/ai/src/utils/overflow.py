"""
上下文溢出检测工具。

本模块提供检测 LLM 响应是否指示上下文窗口溢出错误的功能，
这种情况在输入超过模型的上下文窗口时发生。
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING, List, Optional, Pattern

if TYPE_CHECKING:
    from ..core_types import AssistantMessage


# 检测不同提供商上下文溢出错误的正则表达式模式
_OVERFLOW_PATTERNS: List[Pattern] = [
    # Anthropic
    re.compile(r"prompt is too long", re.IGNORECASE),
    # Amazon Bedrock
    re.compile(r"input is too long for requested model", re.IGNORECASE),
    # OpenAI (Completions & Responses API)
    re.compile(r"exceeds the context window", re.IGNORECASE),
    # Google (Gemini)
    re.compile(r"input token count.*exceeds the maximum", re.IGNORECASE),
    # xAI (Grok)
    re.compile(r"maximum prompt length is \d+", re.IGNORECASE),
    # Groq
    re.compile(r"reduce the length of the messages", re.IGNORECASE),
    # OpenRouter (所有后端)
    re.compile(r"maximum context length is \d+ tokens", re.IGNORECASE),
    # GitHub Copilot
    re.compile(r"exceeds the limit of \d+", re.IGNORECASE),
    # llama.cpp server
    re.compile(r"exceeds the available context size", re.IGNORECASE),
    # LM Studio
    re.compile(r"greater than the context length", re.IGNORECASE),
    # MiniMax
    re.compile(r"context window exceeds limit", re.IGNORECASE),
    # Kimi For Coding
    re.compile(r"exceeded model token limit", re.IGNORECASE),
    # Mistral
    re.compile(r"too large for model with \d+ maximum context length", re.IGNORECASE),
    # z.ai 非标准 finish_reason
    re.compile(r"model_context_window_exceeded", re.IGNORECASE),
    # 通用回退模式
    re.compile(r"context[_ ]length[_ ]exceeded", re.IGNORECASE),
    re.compile(r"too many tokens", re.IGNORECASE),
    re.compile(r"token limit exceeded", re.IGNORECASE),
]


def is_context_overflow(
    message: "AssistantMessage",
    context_window: Optional[int] = None,
) -> bool:
    """
    检查助手消息是否表示上下文溢出错误。

    处理两种情况：
    1. 基于错误的溢出：大多数提供商返回 stopReason "error" 并带有
       特定的错误消息模式。
    2. 静默溢出：某些提供商接受溢出请求并成功返回。对于这些，
       我们检查 usage.input 是否超过上下文窗口。

    各提供商检测可靠性：
    - **可靠检测（返回带有可检测消息的错误）：**
      Anthropic, OpenAI, Google Gemini, xAI, Groq, Cerebras, Mistral,
      OpenRouter, llama.cpp, LM Studio, Kimi For Coding

    - **不可靠检测：**
      z.ai（有时静默接受溢出），Ollama（静默截断）

    Args:
        message: 要检查的助手消息
        context_window: 可选的上下文窗口大小，用于检测静默溢出

    Returns:
        如果消息指示上下文溢出则返回 True
    """
    # 情况 1：检查错误消息模式
    if message.stopReason == "error" and message.errorMessage:
        # 检查已知模式
        for pattern in _OVERFLOW_PATTERNS:
            if pattern.search(message.errorMessage):
                return True

        # Cerebras 对上下文溢出返回 400/413 且无 body
        # 注意：429 是速率限制，不是上下文溢出
        if re.match(r"^4(00|13)\s*(status code)?\s*\(no body\)", message.errorMessage, re.IGNORECASE):
            return True

    # 情况 2：静默溢出（z.ai 风格）- 成功但使用量超过上下文
    if context_window and message.stopReason == "stop":
        input_tokens = message.usage.input + message.usage.cacheRead
        if input_tokens > context_window:
            return True

    return False


def get_overflow_patterns() -> List[Pattern]:
    """
    获取溢出模式列表（用于测试）。

    Returns:
        溢出模式列表的副本
    """
    return _OVERFLOW_PATTERNS.copy()

