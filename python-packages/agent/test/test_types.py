"""
Tests for types.py module.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.types import (
    TextContent,
    ImageContent,
    ThinkingContent,
    ToolCall,
    Usage,
    Model,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    AgentState,
    AgentTool,
    AgentToolResult,
    AgentContext,
    ThinkingLevel,
    AgentStartEvent,
    AgentEndEvent,
    TurnStartEvent,
    TurnEndEvent,
    MessageStartEvent,
    MessageEndEvent,
    ToolExecutionStartEvent,
    ToolExecutionEndEvent,
)


class TestContentTypes:
    """Tests for content type classes."""

    def test_text_content(self):
        """Test TextContent creation."""
        content = TextContent(type="text", text="Hello")
        assert content.type == "text"
        assert content.text == "Hello"

    def test_image_content(self):
        """Test ImageContent creation."""
        content = ImageContent(type="image", data="base64data", mime_type="image/png")
        assert content.type == "image"
        assert content.data == "base64data"
        assert content.mime_type == "image/png"

    def test_thinking_content(self):
        """Test ThinkingContent creation."""
        content = ThinkingContent(type="thinking", thinking="Let me think...")
        assert content.type == "thinking"
        assert content.thinking == "Let me think..."

    def test_tool_call(self):
        """Test ToolCall creation."""
        content = ToolCall(
            type="toolCall",
            id="call-123",
            name="calculate",
            arguments={"expression": "1 + 2"}
        )
        assert content.type == "toolCall"
        assert content.id == "call-123"
        assert content.name == "calculate"
        assert content.arguments == {"expression": "1 + 2"}


class TestMessages:
    """Tests for message classes."""

    def test_user_message(self):
        """Test UserMessage creation."""
        message = UserMessage(
            role="user",
            content=[TextContent(text="Hello")],
            timestamp=1234567890
        )
        assert message.role == "user"
        assert len(message.content) == 1
        assert message.content[0].text == "Hello"

    def test_assistant_message(self):
        """Test AssistantMessage creation."""
        message = AssistantMessage(
            role="assistant",
            content=[TextContent(text="Hi there!")],
            timestamp=1234567890,
            api="openai-responses",
            provider="openai",
            model="gpt-4",
            usage=Usage(),
            stop_reason="stop"
        )
        assert message.role == "assistant"
        assert message.api == "openai-responses"
        assert message.provider == "openai"
        assert message.model == "gpt-4"
        assert message.stop_reason == "stop"

    def test_tool_result_message(self):
        """Test ToolResultMessage creation."""
        message = ToolResultMessage(
            role="toolResult",
            content=[TextContent(text="Result: 3")],
            timestamp=1234567890,
            tool_call_id="call-123",
            tool_name="calculate",
            details={},
            is_error=False
        )
        assert message.role == "toolResult"
        assert message.tool_call_id == "call-123"
        assert message.tool_name == "calculate"
        assert message.is_error is False


class TestUsage:
    """Tests for Usage class."""

    def test_usage_defaults(self):
        """Test Usage with default values."""
        usage = Usage()
        assert usage.input == 0
        assert usage.output == 0
        assert usage.cache_read == 0
        assert usage.cache_write == 0
        assert usage.total_tokens == 0

    def test_usage_with_values(self):
        """Test Usage with custom values."""
        usage = Usage(
            input=100,
            output=50,
            cache_read=20,
            cache_write=10,
            total_tokens=160
        )
        assert usage.input == 100
        assert usage.output == 50
        assert usage.total_tokens == 160


class TestModel:
    """Tests for Model class."""

    def test_model_creation(self):
        """Test Model creation."""
        model = Model(
            api="openai-responses",
            provider="openai",
            id="gpt-4o"
        )
        assert model.api == "openai-responses"
        assert model.provider == "openai"
        assert model.id == "gpt-4o"


class TestAgentState:
    """Tests for AgentState class."""

    def test_agent_state_defaults(self):
        """Test AgentState with default values."""
        state = AgentState()
        assert state.system_prompt == ""
        assert state.model is None
        assert state.thinking_level == ThinkingLevel.OFF
        assert state.tools == []
        assert state.messages == []
        assert state.is_streaming is False
        assert state.stream_message is None
        assert state.pending_tool_calls == set()
        assert state.error is None

    def test_agent_state_with_values(self):
        """Test AgentState with custom values."""
        model = Model(api="openai-responses", provider="openai", id="gpt-4")
        state = AgentState(
            system_prompt="You are helpful.",
            model=model,
            thinking_level=ThinkingLevel.HIGH,
            messages=[{"role": "user", "content": "Hello", "timestamp": 123}]
        )
        assert state.system_prompt == "You are helpful."
        assert state.model == model
        assert state.thinking_level == ThinkingLevel.HIGH
        assert len(state.messages) == 1


class TestAgentTool:
    """Tests for AgentTool class."""

    def test_agent_tool_creation(self):
        """Test AgentTool creation."""
        tool = AgentTool(
            name="calculate",
            description="Evaluate math expressions",
            parameters={"type": "object", "properties": {}},
            label="Calculator"
        )
        assert tool.name == "calculate"
        assert tool.description == "Evaluate math expressions"
        assert tool.label == "Calculator"

    def test_agent_tool_with_execute(self):
        """Test AgentTool with execute function."""
        async def execute_fn(tool_call_id, params, signal, on_update):
            return AgentToolResult(
                content=[TextContent(text="3")],
                details={}
            )

        tool = AgentTool(
            name="calculate",
            description="Evaluate math expressions",
            parameters={},
            label="Calculator",
            execute=execute_fn
        )
        assert tool.execute is not None


class TestAgentToolResult:
    """Tests for AgentToolResult class."""

    def test_agent_tool_result(self):
        """Test AgentToolResult creation."""
        result = AgentToolResult(
            content=[TextContent(text="Result: 3")],
            details={"value": 3}
        )
        assert len(result.content) == 1
        assert result.content[0].text == "Result: 3"
        assert result.details == {"value": 3}


class TestAgentContext:
    """Tests for AgentContext class."""

    def test_agent_context(self):
        """Test AgentContext creation."""
        context = AgentContext(
            system_prompt="You are helpful.",
            messages=[{"role": "user", "content": "Hello", "timestamp": 123}],
            tools=[]
        )
        assert context.system_prompt == "You are helpful."
        assert len(context.messages) == 1


class TestThinkingLevel:
    """Tests for ThinkingLevel enum."""

    def test_thinking_level_values(self):
        """Test ThinkingLevel enum values."""
        assert ThinkingLevel.OFF.value == "off"
        assert ThinkingLevel.MINIMAL.value == "minimal"
        assert ThinkingLevel.LOW.value == "low"
        assert ThinkingLevel.MEDIUM.value == "medium"
        assert ThinkingLevel.HIGH.value == "high"
        assert ThinkingLevel.XHIGH.value == "xhigh"


class TestAgentEvents:
    """Tests for Agent event classes."""

    def test_agent_start_event(self):
        """Test AgentStartEvent."""
        event = AgentStartEvent()
        assert event.type == "agent_start"

    def test_agent_end_event(self):
        """测试 AgentEndEvent。"""
        event = AgentEndEvent(messages=[])
        assert event.type == "agent_end"
        assert event.messages == []

    def test_turn_start_event(self):
        """测试 TurnStartEvent。"""
        event = TurnStartEvent()
        assert event.type == "turn_start"

    def test_turn_end_event(self):
        """测试 TurnEndEvent。"""
        event = TurnEndEvent(
            message={"role": "assistant", "content": []},
            tool_results=[]
        )
        assert event.type == "turn_end"

    def test_message_start_event(self):
        """测试 MessageStartEvent。"""
        event = MessageStartEvent(
            message={"role": "user", "content": "Hello", "timestamp": 123}
        )
        assert event.type == "message_start"

    def test_message_end_event(self):
        """测试 MessageEndEvent。"""
        event = MessageEndEvent(
            message={"role": "assistant", "content": []}
        )
        assert event.type == "message_end"

    def test_tool_execution_start_event(self):
        """测试 ToolExecutionStartEvent。"""
        event = ToolExecutionStartEvent(
            tool_call_id="call-123",
            tool_name="calculate",
            args={"expression": "1+2"}
        )
        assert event.type == "tool_execution_start"
        assert event.tool_call_id == "call-123"
        assert event.tool_name == "calculate"

    def test_tool_execution_end_event(self):
        """测试 ToolExecutionEndEvent。"""
        event = ToolExecutionEndEvent(
            tool_call_id="call-123",
            tool_name="calculate",
            result={"content": [], "details": {}},
            is_error=False
        )
        assert event.type == "tool_execution_end"
        assert event.is_error is False

