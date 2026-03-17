"""
providers/transform_messages.py 模块的单元测试。

测试目标：
1. 验证 transform_messages 能够正确转换消息
2. 验证 thinking 块的跨提供商转换
3. 验证孤立 tool call 的处理
"""

import pytest

from src.providers.transform_messages import transform_messages
from src.core_types import (
    Model,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    TextContent,
    ThinkingContent,
    ToolCall,
)


class TestTransformMessages:
    """测试 transform_messages 函数。"""

    def test_user_messages_unchanged(self):
        """
        测试用户消息不变换。
        预期结果：用户消息原样返回。
        """
        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
        )
        messages = [
            UserMessage(content="Hello!", timestamp=123),
        ]

        result = transform_messages(messages, model)

        assert len(result) == 1
        assert result[0].role == "user"
        assert result[0].content == "Hello!"

    def test_same_model_thinking_preserved(self):
        """
        测试同一模型的 thinking 块被保留。
        预期结果：thinking 块保持原样。
        """
        model = Model(
            id="gpt-4",
            name="GPT-4",
            api="openai-responses",
            provider="openai",
        )
        messages = [
            AssistantMessage(
                content=[
                    ThinkingContent(thinking="Let me think...", thinkingSignature="sig-123"),
                    TextContent(text="The answer is 42."),
                ],
                api="openai-responses",
                provider="openai",
                model="gpt-4",
            ),
        ]

        result = transform_messages(messages, model)

        assert len(result[0].content) == 2  # type: ignore
        assert result[0].content[0].type == "thinking"  # type: ignore

    def test_cross_model_thinking_converted_to_text(self):
        """
        测试跨模型的 thinking 块转换为文本。
        预期结果：thinking 块转换为普通文本。
        """
        model = Model(
            id="claude-3",
            name="Claude 3",
            api="anthropic-messages",
            provider="anthropic",
        )
        messages = [
            AssistantMessage(
                content=[
                    ThinkingContent(thinking="Let me think..."),
                    TextContent(text="The answer is 42."),
                ],
                api="openai-responses",
                provider="openai",
                model="gpt-4",
            ),
        ]

        result = transform_messages(messages, model)

        # thinking 块被转换为文本
        content = result[0].content  # type: ignore
        assert len(content) == 2
        assert content[0].type == "text"
        assert content[0].text == "Let me think..."

    def test_redacted_thinking_dropped_for_cross_model(self):
        """
        测试跨模型的 redacted thinking 被丢弃。
        预期结果：redacted thinking 不出现在结果中。
        """
        model = Model(
            id="claude-3",
            name="Claude 3",
            api="anthropic-messages",
            provider="anthropic",
        )
        messages = [
            AssistantMessage(
                content=[
                    ThinkingContent(thinking="", redacted=True, thinkingSignature="encrypted"),
                    TextContent(text="The answer is 42."),
                ],
                api="openai-responses",
                provider="openai",
                model="gpt-4",
            ),
        ]

        result = transform_messages(messages, model)

        content = result[0].content  # type: ignore
        assert len(content) == 1
        assert content[0].type == "text"

    def test_empty_thinking_dropped(self):
        """
        测试空 thinking 块被丢弃。
        预期结果：空 thinking 不出现在结果中。
        """
        model = Model(
            id="gpt-4",
            name="GPT-4",
            api="openai-responses",
            provider="openai",
        )
        messages = [
            AssistantMessage(
                content=[
                    ThinkingContent(thinking="   "),  # 仅空白
                    TextContent(text="The answer is 42."),
                ],
                api="openai-responses",
                provider="openai",
                model="gpt-4",
            ),
        ]

        result = transform_messages(messages, model)

        content = result[0].content  # type: ignore
        assert len(content) == 1
        assert content[0].type == "text"

    def test_tool_result_messages_unchanged(self):
        """
        测试 tool result 消息不变换。
        预期结果：tool result 消息原样返回。
        """
        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
        )
        messages = [
            ToolResultMessage(
                toolCallId="call-123",
                toolName="calculate",
                content=[TextContent(text="3")],
            ),
        ]

        result = transform_messages(messages, model)

        assert len(result) == 1
        assert result[0].role == "toolResult"

    def test_error_messages_skipped(self):
        """
        测试错误消息被跳过。
        预期结果：stopReason 为 error 的消息不出现。
        """
        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
        )
        messages = [
            AssistantMessage(
                content=[TextContent(text="Partial")],
                api="test-api",
                provider="test-provider",
                model="test-model",
                stopReason="error",
                errorMessage="Something went wrong",
            ),
            UserMessage(content="Try again", timestamp=456),
        ]

        result = transform_messages(messages, model)

        assert len(result) == 1
        assert result[0].role == "user"

    def test_aborted_messages_skipped(self):
        """
        测试中止消息被跳过。
        预期结果：stopReason 为 aborted 的消息不出现。
        """
        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
        )
        messages = [
            AssistantMessage(
                content=[TextContent(text="Partial")],
                api="test-api",
                provider="test-provider",
                model="test-model",
                stopReason="aborted",
            ),
        ]

        result = transform_messages(messages, model)

        assert len(result) == 0


class TestOrphanedToolCalls:
    """测试孤立 tool call 的处理。"""

    def test_orphaned_tool_call_gets_synthetic_result(self):
        """
        测试孤立的 tool call 获得合成结果。
        预期结果：没有对应 tool result 的 tool call 获得合成的错误结果。
        """
        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
        )
        messages = [
            AssistantMessage(
                content=[
                    ToolCall(id="call-123", name="calculate", arguments={}),
                ],
                api="test-api",
                provider="test-provider",
                model="test-model",
            ),
            # 没有 tool result，直接是用户消息
            UserMessage(content="Continue", timestamp=123),
        ]

        result = transform_messages(messages, model)

        # 应该有 3 条消息：assistant, synthetic tool result, user
        assert len(result) == 3
        assert result[1].role == "toolResult"
        assert result[1].isError is True  # type: ignore
        assert result[1].toolCallId == "call-123"  # type: ignore

    def test_tool_result_matched_correctly(self):
        """
        测试 tool result 正确匹配。
        预期结果：有对应 tool result 的不生成合成结果。
        """
        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
        )
        messages = [
            AssistantMessage(
                content=[
                    ToolCall(id="call-123", name="calculate", arguments={}),
                ],
                api="test-api",
                provider="test-provider",
                model="test-model",
            ),
            ToolResultMessage(
                toolCallId="call-123",
                toolName="calculate",
                content=[TextContent(text="3")],
            ),
        ]

        result = transform_messages(messages, model)

        # 应该只有 2 条消息，没有合成结果
        assert len(result) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

