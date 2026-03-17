"""
Tests for agent_loop.py module.
"""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent_loop import (
    agent_loop,
    agent_loop_continue,
    AgentStream,
    _skip_tool_call,
)
from src.types import (
    AgentContext,
    AgentLoopConfig,
    AgentMessage,
    AgentTool,
    AgentToolResult,
    Model,
    TextContent,
    Usage,
)


def create_model():
    """Create a test model."""
    return Model(
        api="openai-responses",
        provider="openai",
        id="mock-model"
    )


def create_usage():
    """Create a test usage."""
    return {
        "input": 0,
        "output": 0,
        "cacheRead": 0,
        "cacheWrite": 0,
        "totalTokens": 0,
        "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
    }


def create_assistant_message(content, stop_reason="stop"):
    """Create a test assistant message."""
    return {
        "role": "assistant",
        "content": content,
        "api": "openai-responses",
        "provider": "openai",
        "model": "mock",
        "usage": create_usage(),
        "stop_reason": stop_reason,
        "timestamp": 1234567890,
    }


def create_user_message(text):
    """Create a test user message."""
    return {
        "role": "user",
        "content": text,
        "timestamp": 1234567890,
    }


def identity_converter(messages):
    """Simple identity converter for tests."""
    return [m for m in messages if m.get("role") in ("user", "assistant", "toolResult")]


def create_mock_stream_fn(responses):
    """Create a mock stream function that returns predefined responses."""
    call_index = [0]

    async def stream_fn(model, context, options):
        stream = AgentStream()

        async def run():
            if call_index[0] < len(responses):
                response = responses[call_index[0]]
                call_index[0] += 1

                # Emit start event
                stream.push({"type": "start", "partial": response})

                # Emit done event
                stream.push({"type": "done", "reason": response.get("stop_reason", "stop"), "partial": response})

        asyncio.create_task(run())
        return stream

    return stream_fn


class TestAgentStream:
    """Tests for AgentStream class."""

    def test_push_and_iterate(self):
        """Test pushing events and iterating over them."""
        stream = AgentStream()

        events = []

        async def collect():
            async for event in stream:
                events.append(event)
                if event.get("type") == "done":
                    stream.end()

        # Push events
        stream.push({"type": "start"})
        stream.push({"type": "done"})
        stream.end()

        asyncio.run(collect())

        assert len(events) == 2
        assert events[0]["type"] == "start"
        assert events[1]["type"] == "done"


class TestAgentLoop:
    """Tests for agent_loop function."""

    @pytest.mark.asyncio
    async def test_emit_events_with_agent_message_types(self):
        """Test that agent_loop emits events with AgentMessage types."""
        context = AgentContext(
            system_prompt="You are helpful.",
            messages=[],
            tools=[],
        )

        user_prompt = create_user_message("Hello")

        config = AgentLoopConfig(
            model=create_model(),
            convert_to_llm=identity_converter,
        )

        responses = [create_assistant_message([{"type": "text", "text": "Hi there!"}])]
        stream_fn = create_mock_stream_fn(responses)

        events = []

        # Create stream within the running event loop
        stream = agent_loop([user_prompt], context, config, None, stream_fn)

        # Give time for async tasks to complete
        await asyncio.sleep(0.2)

        async for event in stream:
            events.append(event)

        # Verify event sequence - agent_start is pushed first
        event_types = [e.get("type") for e in events]
        assert "turn_start" in event_types
        assert "message_start" in event_types
        assert "message_end" in event_types
        assert "turn_end" in event_types
        assert "agent_end" in event_types

    @pytest.mark.asyncio
    async def test_handle_custom_message_types(self):
        """Test handling custom message types via convertToLlm."""
        notification = {
            "role": "notification",
            "text": "This is a notification",
            "timestamp": 1234567890,
        }

        context = AgentContext(
            system_prompt="You are helpful.",
            messages=[notification],
            tools=[],
        )

        user_prompt = create_user_message("Hello")

        converted_messages = []

        def custom_converter(messages):
            nonlocal converted_messages
            converted_messages = [
                m for m in messages
                if m.get("role") != "notification" and m.get("role") in ("user", "assistant", "toolResult")
            ]
            return converted_messages

        config = AgentLoopConfig(
            model=create_model(),
            convert_to_llm=custom_converter,
        )

        responses = [create_assistant_message([{"type": "text", "text": "Response"}])]
        stream_fn = create_mock_stream_fn(responses)

        stream = agent_loop([user_prompt], context, config, None, stream_fn)

        async for _ in stream:
            pass

        # The notification should have been filtered out
        assert len(converted_messages) == 1
        assert converted_messages[0]["role"] == "user"

    @pytest.mark.asyncio
    async def test_handle_tool_calls(self):
        """Test handling tool calls and results."""
        executed = []

        async def execute_echo(tool_call_id, params, signal, on_update):
            executed.append(params["value"])
            return AgentToolResult(
                content=[TextContent(text=f"echoed: {params['value']}")],
                details={"value": params["value"]},
            )

        tool = AgentTool(
            name="echo",
            label="Echo",
            description="Echo tool",
            parameters={},
            execute=execute_echo,
        )

        context = AgentContext(
            system_prompt="",
            messages=[],
            tools=[tool],
        )

        user_prompt = create_user_message("echo something")

        config = AgentLoopConfig(
            model=create_model(),
            convert_to_llm=identity_converter,
        )

        # First response: tool call, second response: final
        call_index = [0]

        async def stream_fn(model, ctx, options):
            stream = AgentStream()

            async def run():
                if call_index[0] == 0:
                    message = create_assistant_message(
                        [{"type": "toolCall", "id": "tool-1", "name": "echo", "arguments": {"value": "hello"}}],
                        "toolUse"
                    )
                    stream.push({"type": "start", "partial": message})
                    stream.push({"type": "done", "reason": "toolUse", "partial": message})
                else:
                    message = create_assistant_message([{"type": "text", "text": "done"}])
                    stream.push({"type": "start", "partial": message})
                    stream.push({"type": "done", "reason": "stop", "partial": message})
                call_index[0] += 1

            asyncio.create_task(run())
            return stream

        events = []
        stream = agent_loop([user_prompt], context, config, None, stream_fn)

        async for event in stream:
            events.append(event)

        # Tool should have been executed
        assert executed == ["hello"]

        # Should have tool execution events
        tool_start = next((e for e in events if e.get("type") == "tool_execution_start"), None)
        tool_end = next((e for e in events if e.get("type") == "tool_execution_end"), None)
        assert tool_start is not None
        assert tool_end is not None
        assert tool_end["is_error"] is False


class TestAgentLoopContinue:
    """Tests for agent_loop_continue function."""

    def test_throw_when_no_messages(self):
        """Test that agent_loop_continue throws when context has no messages."""
        context = AgentContext(
            system_prompt="You are helpful.",
            messages=[],
            tools=[],
        )

        config = AgentLoopConfig(
            model=create_model(),
            convert_to_llm=identity_converter,
        )

        with pytest.raises(RuntimeError, match="Cannot continue: no messages in context"):
            agent_loop_continue(context, config)

    def test_throw_when_last_message_is_assistant(self):
        """Test that agent_loop_continue throws when last message is assistant."""
        context = AgentContext(
            system_prompt="You are helpful.",
            messages=[create_assistant_message([{"type": "text", "text": "Hi"}])],
            tools=[],
        )

        config = AgentLoopConfig(
            model=create_model(),
            convert_to_llm=identity_converter,
        )

        with pytest.raises(RuntimeError, match="Cannot continue from message role: assistant"):
            agent_loop_continue(context, config)

    @pytest.mark.asyncio
    async def test_continue_from_existing_context(self):
        """测试从现有上下文继续。"""
        user_message = create_user_message("Hello")

        context = AgentContext(
            system_prompt="You are helpful.",
            messages=[user_message],
            tools=[],
        )

        config = AgentLoopConfig(
            model=create_model(),
            convert_to_llm=identity_converter,
        )

        responses = [create_assistant_message([{"type": "text", "text": "Response"}])]
        stream_fn = create_mock_stream_fn(responses)

        events = []
        stream = agent_loop_continue(context, config, None, stream_fn)

        async for event in stream:
            events.append(event)

        # 应该只有助手消息事件（没有用户消息事件）
        message_end_events = [e for e in events if e.get("type") == "message_end"]
        assert len(message_end_events) == 1
        assert message_end_events[0]["message"]["role"] == "assistant"


class TestSkipToolCall:
    """_skip_tool_call 函数的测试。"""

    def test_skip_tool_call(self):
        """测试跳过工具调用。"""
        # 创建不需要事件循环的模拟流
        class MockStream:
            def __init__(self):
                self.events = []
            def push(self, event):
                self.events.append(event)

        stream = MockStream()
        tool_call = {
            "id": "tool-123",
            "name": "calculate",
            "arguments": {"expression": "1+2"},
        }

        result = _skip_tool_call(tool_call, stream)

        assert result["role"] == "toolResult"
        assert result["tool_call_id"] == "tool-123"
        assert result["tool_name"] == "calculate"
        assert result["is_error"] is True
        # result["content"][0] 是 TextContent 数据类，不是字典
        assert "Skipped" in result["content"][0].text

