"""
types.py 模块的单元测试。

测试目标：
1. 验证所有数据类（dataclass）能够正确创建和初始化
2. 验证类型字段的默认值设置正确
3. 验证可选字段的行为
4. 验证嵌套数据结构的正确性
"""

import pytest
from src.core_types import (
    # 内容类型
    TextContent,
    ThinkingContent,
    ImageContent,
    ToolCall,
    # 使用量类型
    Usage,
    UsageCost,
    # 消息类型
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    # 工具和上下文
    Tool,
    Context,
    # 事件类型
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
    # 模型类型
    Model,
    ModelCost,
)


class TestTextContent:
    """测试 TextContent 数据类。"""

    def test_create_with_defaults(self):
        """
        测试使用默认值创建 TextContent。
        预期结果：type 字段为 "text"，text 字段为空字符串，textSignature 为 None。
        """
        content = TextContent()
        assert content.type == "text"
        assert content.text == ""
        assert content.textSignature is None

    def test_create_with_values(self):
        """
        测试使用自定义值创建 TextContent。
        预期结果：所有字段按传入值设置。
        """
        content = TextContent(text="Hello, World!", textSignature="sig-123")
        assert content.type == "text"
        assert content.text == "Hello, World!"
        assert content.textSignature == "sig-123"


class TestThinkingContent:
    """测试 ThinkingContent 数据类。"""

    def test_create_with_defaults(self):
        """
        测试使用默认值创建 ThinkingContent。
        预期结果：type 字段为 "thinking"，其他字段为默认值。
        """
        content = ThinkingContent()
        assert content.type == "thinking"
        assert content.thinking == ""
        assert content.thinkingSignature is None
        assert content.redacted is False

    def test_create_with_redacted(self):
        """
        测试创建 redacted 的 ThinkingContent。
        预期结果：redacted 字段为 True。
        """
        content = ThinkingContent(
            thinking="Secret thoughts...",
            thinkingSignature="encrypted-sig",
            redacted=True,
        )
        assert content.redacted is True
        assert content.thinkingSignature == "encrypted-sig"


class TestImageContent:
    """测试 ImageContent 数据类。"""

    def test_create_with_defaults(self):
        """
        测试使用默认值创建 ImageContent。
        预期结果：type 字段为 "image"，data 和 mimeType 为空。
        """
        content = ImageContent()
        assert content.type == "image"
        assert content.data == ""
        assert content.mimeType == ""

    def test_create_with_base64_data(self):
        """
        测试创建带有 base64 图像数据的 ImageContent。
        预期结果：data 和 mimeType 正确设置。
        """
        content = ImageContent(data="iVBORw0KGgo=", mimeType="image/png")
        assert content.type == "image"
        assert content.data == "iVBORw0KGgo="
        assert content.mimeType == "image/png"


class TestToolCall:
    """测试 ToolCall 数据类。"""

    def test_create_with_defaults(self):
        """
        测试使用默认值创建 ToolCall。
        预期结果：type 字段为 "toolCall"，arguments 为空字典。
        """
        tool_call = ToolCall()
        assert tool_call.type == "toolCall"
        assert tool_call.id == ""
        assert tool_call.name == ""
        assert tool_call.arguments == {}
        assert tool_call.thoughtSignature is None

    def test_create_with_arguments(self):
        """
        测试创建带有参数的 ToolCall。
        预期结果：arguments 字典包含传入的参数。
        """
        tool_call = ToolCall(
            id="call-123",
            name="calculate",
            arguments={"expression": "1 + 2", "precision": 2},
            thoughtSignature="google-sig",
        )
        assert tool_call.id == "call-123"
        assert tool_call.name == "calculate"
        assert tool_call.arguments == {"expression": "1 + 2", "precision": 2}
        assert tool_call.thoughtSignature == "google-sig"


class TestUsage:
    """测试 Usage 数据类。"""

    def test_create_with_defaults(self):
        """
        测试使用默认值创建 Usage。
        预期结果：所有计数字段为 0，cost 为 UsageCost 实例。
        """
        usage = Usage()
        assert usage.input == 0
        assert usage.output == 0
        assert usage.cacheRead == 0
        assert usage.cacheWrite == 0
        assert usage.totalTokens == 0
        assert isinstance(usage.cost, UsageCost)

    def test_create_with_values(self):
        """
        测试使用自定义值创建 Usage。
        预期结果：所有字段按传入值设置。
        """
        usage = Usage(
            input=100,
            output=50,
            cacheRead=20,
            cacheWrite=10,
            totalTokens=160,
        )
        assert usage.input == 100
        assert usage.output == 50
        assert usage.totalTokens == 160


class TestUsageCost:
    """测试 UsageCost 数据类。"""

    def test_create_with_defaults(self):
        """
        测试使用默认值创建 UsageCost。
        预期结果：所有字段为 0.0。
        """
        cost = UsageCost()
        assert cost.input == 0.0
        assert cost.output == 0.0
        assert cost.cacheRead == 0.0
        assert cost.cacheWrite == 0.0
        assert cost.total == 0.0

    def test_create_with_values(self):
        """
        测试使用自定义值创建 UsageCost。
        预期结果：所有字段按传入值设置。
        """
        cost = UsageCost(
            input=2.5,
            output=10.0,
            cacheRead=0.3,
            cacheWrite=3.75,
            total=16.55,
        )
        assert cost.input == 2.5
        assert cost.output == 10.0
        assert cost.total == 16.55


class TestUserMessage:
    """测试 UserMessage 数据类。"""

    def test_create_with_string_content(self):
        """
        测试创建字符串内容的 UserMessage。
        预期结果：content 为字符串，role 为 "user"。
        """
        message = UserMessage(content="Hello!", timestamp=1234567890)
        assert message.role == "user"
        assert message.content == "Hello!"
        assert message.timestamp == 1234567890

    def test_create_with_list_content(self):
        """
        测试创建列表内容的 UserMessage（支持多模态）。
        预期结果：content 为内容块列表。
        """
        message = UserMessage(
            content=[
                TextContent(text="What is in this image?"),
                ImageContent(data="base64imagedata", mimeType="image/png"),
            ],
            timestamp=1234567890,
        )
        assert message.role == "user"
        assert len(message.content) == 2  # type: ignore
        assert message.content[0].text == "What is in this image?"  # type: ignore


class TestAssistantMessage:
    """测试 AssistantMessage 数据类。"""

    def test_create_with_defaults(self):
        """
        测试使用默认值创建 AssistantMessage。
        预期结果：所有字段为默认值，content 为空列表。
        """
        message = AssistantMessage()
        assert message.role == "assistant"
        assert message.content == []
        assert message.api == ""
        assert message.provider == ""
        assert message.model == ""
        assert message.stopReason == "stop"
        assert message.errorMessage is None

    def test_create_with_content(self):
        """
        测试创建带有内容的 AssistantMessage。
        预期结果：content 列表包含传入的内容块。
        """
        message = AssistantMessage(
            content=[TextContent(text="Hello there!")],
            api="openai-responses",
            provider="openai",
            model="gpt-4",
            usage=Usage(input=10, output=5),
            stopReason="stop",
            timestamp=1234567890,
        )
        assert message.role == "assistant"
        assert len(message.content) == 1
        assert message.content[0].text == "Hello there!"
        assert message.api == "openai-responses"
        assert message.provider == "openai"
        assert message.model == "gpt-4"

    def test_create_with_error(self):
        """
        测试创建错误的 AssistantMessage。
        预期结果：stopReason 为 "error"，errorMessage 包含错误信息。
        """
        message = AssistantMessage(
            content=[TextContent(text="Partial response")],
            stopReason="error",
            errorMessage="Rate limit exceeded",
        )
        assert message.stopReason == "error"
        assert message.errorMessage == "Rate limit exceeded"


class TestToolResultMessage:
    """测试 ToolResultMessage 数据类。"""

    def test_create_with_defaults(self):
        """
        测试使用默认值创建 ToolResultMessage。
        预期结果：所有字段为默认值。
        """
        message = ToolResultMessage()
        assert message.role == "toolResult"
        assert message.toolCallId == ""
        assert message.toolName == ""
        assert message.content == []
        assert message.details is None
        assert message.isError is False

    def test_create_with_result(self):
        """
        测试创建带有结果的 ToolResultMessage。
        预期结果：所有字段按传入值设置。
        """
        message = ToolResultMessage(
            toolCallId="call-123",
            toolName="calculate",
            content=[TextContent(text="Result: 3")],
            details={"value": 3, "cached": False},
            isError=False,
            timestamp=1234567890,
        )
        assert message.toolCallId == "call-123"
        assert message.toolName == "calculate"
        assert len(message.content) == 1
        assert message.content[0].text == "Result: 3"
        assert message.details == {"value": 3, "cached": False}

    def test_create_with_error(self):
        """
        测试创建错误的 ToolResultMessage。
        预期结果：isError 为 True。
        """
        message = ToolResultMessage(
            toolCallId="call-456",
            toolName="divide",
            content=[TextContent(text="Error: Division by zero")],
            isError=True,
        )
        assert message.isError is True


class TestTool:
    """测试 Tool 数据类。"""

    def test_create_with_defaults(self):
        """
        测试使用默认值创建 Tool。
        预期结果：name 和 description 为空，parameters 为空对象 schema。
        """
        tool = Tool(name="", description="")
        assert tool.name == ""
        assert tool.description == ""
        assert tool.parameters == {"type": "object", "properties": {}}

    def test_create_with_parameters(self):
        """
        测试创建带有参数 schema 的 Tool。
        预期结果：parameters 包含正确的 JSON Schema。
        """
        tool = Tool(
            name="calculate",
            description="Evaluate mathematical expressions",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "The expression to evaluate",
                    },
                    "precision": {
                        "type": "integer",
                        "description": "Number of decimal places",
                    },
                },
                "required": ["expression"],
            },
        )
        assert tool.name == "calculate"
        assert tool.description == "Evaluate mathematical expressions"
        assert "expression" in tool.parameters["properties"]
        assert "precision" in tool.parameters["properties"]


class TestContext:
    """测试 Context 数据类。"""

    def test_create_with_defaults(self):
        """
        测试使用默认值创建 Context。
        预期结果：systemPrompt 为 None，messages 为空列表，tools 为 None。
        """
        context = Context()
        assert context.systemPrompt is None
        assert context.messages == []
        assert context.tools is None

    def test_create_with_messages(self):
        """
        测试创建带有消息的 Context。
        预期结果：messages 列表包含传入的消息。
        """
        context = Context(
            systemPrompt="You are a helpful assistant.",
            messages=[
                UserMessage(content="Hello!", timestamp=123),
                AssistantMessage(content=[TextContent(text="Hi!")], timestamp=456),
            ],
            tools=[Tool(name="get_time", description="Get current time")],
        )
        assert context.systemPrompt == "You are a helpful assistant."
        assert len(context.messages) == 2
        assert len(context.tools) == 1  # type: ignore


class TestStreamingEvents:
    """测试流式事件数据类。"""

    def test_start_event(self):
        """
        测试创建 StartEvent。
        预期结果：type 为 "start"，partial 为 AssistantMessage 实例。
        """
        event = StartEvent()
        assert event.type == "start"
        assert isinstance(event.partial, AssistantMessage)

    def test_text_delta_event(self):
        """
        测试创建 TextDeltaEvent。
        预期结果：type 为 "text_delta"，delta 包含增量文本。
        """
        event = TextDeltaEvent(contentIndex=0, delta="Hello")
        assert event.type == "text_delta"
        assert event.contentIndex == 0
        assert event.delta == "Hello"

    def test_text_end_event(self):
        """
        测试创建 TextEndEvent。
        预期结果：type 为 "text_end"，content 包含完整文本。
        """
        event = TextEndEvent(contentIndex=0, content="Hello, World!")
        assert event.type == "text_end"
        assert event.content == "Hello, World!"

    def test_tool_call_end_event(self):
        """
        测试创建 ToolCallEndEvent。
        预期结果：type 为 "toolcall_end"，toolCall 包含完整的工具调用。
        """
        tool_call = ToolCall(id="call-123", name="calculate", arguments={"expr": "1+1"})
        event = ToolCallEndEvent(contentIndex=0, toolCall=tool_call)
        assert event.type == "toolcall_end"
        assert event.toolCall.id == "call-123"
        assert event.toolCall.name == "calculate"

    def test_done_event(self):
        """
        测试创建 DoneEvent。
        预期结果：type 为 "done"，reason 为停止原因。
        """
        message = AssistantMessage(content=[TextContent(text="Done!")])
        event = DoneEvent(reason="stop", message=message)
        assert event.type == "done"
        assert event.reason == "stop"
        assert event.message.content[0].text == "Done!"

    def test_done_event_with_tool_use(self):
        """
        测试创建 toolUse 原因的 DoneEvent。
        预期结果：reason 为 "toolUse"。
        """
        event = DoneEvent(reason="toolUse")
        assert event.reason == "toolUse"

    def test_error_event(self):
        """
        测试创建 ErrorEvent。
        预期结果：type 为 "error"，reason 为错误类型。
        """
        error_msg = AssistantMessage(
            content=[TextContent(text="Partial")],
            stopReason="error",
            errorMessage="Connection failed",
        )
        event = ErrorEvent(reason="error", error=error_msg)
        assert event.type == "error"
        assert event.reason == "error"
        assert event.error.errorMessage == "Connection failed"

    def test_aborted_event(self):
        """
        测试创建 aborted 原因的 ErrorEvent。
        预期结果：reason 为 "aborted"。
        """
        event = ErrorEvent(reason="aborted")
        assert event.reason == "aborted"


class TestModel:
    """测试 Model 数据类。"""

    def test_create_model(self):
        """
        测试创建 Model。
        预期结果：所有字段按传入值设置。
        """
        model = Model(
            id="gpt-4o-mini",
            name="GPT-4o Mini",
            api="openai-responses",
            provider="openai",
            baseUrl="https://api.openai.com/v1",
            reasoning=False,
            input=["text", "image"],
            cost=ModelCost(input=0.15, output=0.6),
            contextWindow=128000,
            maxTokens=16384,
        )
        assert model.id == "gpt-4o-mini"
        assert model.name == "GPT-4o Mini"
        assert model.api == "openai-responses"
        assert model.provider == "openai"
        assert model.reasoning is False
        assert "image" in model.input
        assert model.cost.input == 0.15
        assert model.contextWindow == 128000

    def test_model_with_custom_headers(self):
        """
        测试创建带有自定义 headers 的 Model。
        预期结果：headers 字段包含传入的字典。
        """
        model = Model(
            id="custom-model",
            name="Custom Model",
            api="openai-completions",
            provider="custom",
            headers={"X-Custom-Auth": "bearer-token"},
        )
        assert model.headers == {"X-Custom-Auth": "bearer-token"}


class TestModelCost:
    """测试 ModelCost 数据类。"""

    def test_create_with_defaults(self):
        """
        测试使用默认值创建 ModelCost。
        预期结果：所有字段为 0.0。
        """
        cost = ModelCost()
        assert cost.input == 0.0
        assert cost.output == 0.0
        assert cost.cacheRead == 0.0
        assert cost.cacheWrite == 0.0

    def test_create_with_values(self):
        """
        测试使用自定义值创建 ModelCost。
        预期结果：所有字段按传入值设置。
        """
        cost = ModelCost(input=3.0, output=15.0, cacheRead=0.3, cacheWrite=3.75)
        assert cost.input == 3.0
        assert cost.output == 15.0
        assert cost.cacheRead == 0.3
        assert cost.cacheWrite == 3.75


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

