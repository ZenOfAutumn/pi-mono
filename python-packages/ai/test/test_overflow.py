"""
utils/overflow.py 模块的单元测试。

测试目标：
1. 验证 is_context_overflow 能够正确识别上下文溢出错误
2. 验证支持多种提供商的错误模式
3. 验证静默溢出检测
"""

from src.core_types import AssistantMessage, Usage

import pytest
from src.utils.overflow import is_context_overflow, get_overflow_patterns


class TestIsContextOverflow:
    """测试 is_context_overflow 函数。"""

    def test_detects_anthropic_overflow(self):
        """
        测试检测 Anthropic 上下文溢出错误。
        预期结果：正确识别 Anthropic 的错误消息。
        """
        message = AssistantMessage(
            stopReason="error",
            errorMessage="prompt is too long: 213462 tokens > 200000 maximum",
        )

        assert is_context_overflow(message) is True

    def test_detects_openai_overflow(self):
        """
        测试检测 OpenAI 上下文溢出错误。
        预期结果：正确识别 OpenAI 的错误消息。
        """
        message = AssistantMessage(
            stopReason="error",
            errorMessage="Your input exceeds the context window of this model",
        )

        assert is_context_overflow(message) is True

    def test_detects_google_overflow(self):
        """
        测试检测 Google Gemini 上下文溢出错误。
        预期结果：正确识别 Google 的错误消息。
        """
        message = AssistantMessage(
            stopReason="error",
            errorMessage="The input token count (1196265) exceeds the maximum number of tokens allowed (1048575)",
        )

        assert is_context_overflow(message) is True

    def test_detects_xai_overflow(self):
        """
        测试检测 xAI Grok 上下文溢出错误。
        预期结果：正确识别 xAI 的错误消息。
        """
        message = AssistantMessage(
            stopReason="error",
            errorMessage="This model's maximum prompt length is 131072 but the request contains 537812 tokens",
        )

        assert is_context_overflow(message) is True

    def test_detects_groq_overflow(self):
        """
        测试检测 Groq 上下文溢出错误。
        预期结果：正确识别 Groq 的错误消息。
        """
        message = AssistantMessage(
            stopReason="error",
            errorMessage="Please reduce the length of the messages or completion",
        )

        assert is_context_overflow(message) is True

    def test_detects_openrouter_overflow(self):
        """
        测试检测 OpenRouter 上下文溢出错误。
        预期结果：正确识别 OpenRouter 的错误消息。
        """
        message = AssistantMessage(
            stopReason="error",
            errorMessage="This endpoint's maximum context length is 128000 tokens. However, you requested about 150000 tokens",
        )

        assert is_context_overflow(message) is True

    def test_detects_cerebras_overflow(self):
        """
        测试检测 Cerebras 上下文溢出错误（特殊格式）。
        预期结果：正确识别 Cerebras 的错误消息。
        """
        message = AssistantMessage(
            stopReason="error",
            errorMessage="400 (no body)",
        )

        assert is_context_overflow(message) is True

    def test_detects_cerebras_413_overflow(self):
        """
        测试检测 Cerebras 413 状态码溢出。
        预期结果：正确识别 413 状态码。
        """
        message = AssistantMessage(
            stopReason="error",
            errorMessage="413 status code (no body)",
        )

        assert is_context_overflow(message) is True

    def test_not_overflow_for_rate_limit(self):
        """
        测试速率限制错误不是上下文溢出。
        预期结果：429 错误不应该被识别为溢出。
        """
        message = AssistantMessage(
            stopReason="error",
            errorMessage="429 Too Many Requests",
        )

        assert is_context_overflow(message) is False

    def test_not_overflow_for_other_errors(self):
        """
        测试其他错误不是上下文溢出。
        预期结果：普通错误不被识别为溢出。
        """
        message = AssistantMessage(
            stopReason="error",
            errorMessage="Authentication failed",
        )

        assert is_context_overflow(message) is False

    def test_not_overflow_for_normal_message(self):
        """
        测试正常消息不是上下文溢出。
        预期结果：正常停止的消息不被识别为溢出。
        """
        message = AssistantMessage(
            stopReason="stop",
        )

        assert is_context_overflow(message) is False

    def test_detects_silent_overflow(self):
        """
        测试检测静默溢出（usage 超过 contextWindow）。
        预期结果：当 input tokens 超过 context window 时检测为溢出。
        """
        message = AssistantMessage(
            stopReason="stop",
            usage=Usage(input=150000, cacheRead=10000),
        )

        assert is_context_overflow(message, context_window=128000) is True

    def test_not_overflow_within_context(self):
        """
        测试在上下文范围内的消息不是溢出。
        预期结果：input tokens 小于 context window 时不被识别为溢出。
        """
        message = AssistantMessage(
            stopReason="stop",
            usage=Usage(input=50000, cacheRead=5000),
        )

        assert is_context_overflow(message, context_window=128000) is False


class TestGetOverflowPatterns:
    """测试 get_overflow_patterns 函数。"""

    def test_returns_list_of_patterns(self):
        """
        测试返回的模式列表。
        预期结果：返回非空的正则表达式列表。
        """
        patterns = get_overflow_patterns()

        assert isinstance(patterns, list)
        assert len(patterns) > 0

    def test_patterns_are_compiled(self):
        """
        测试返回的模式是编译好的正则表达式。
        预期结果：每个元素都是 Pattern 对象。
        """

        patterns = get_overflow_patterns()

        for pattern in patterns:
            assert hasattr(pattern, "search")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

