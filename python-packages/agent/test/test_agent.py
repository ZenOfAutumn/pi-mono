"""
Tests for agent.py module.
"""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.agent import Agent, AgentOptions, default_convert_to_llm
from src.types import (
    AgentState,
    AgentTool,
    AgentToolResult,
    Model,
    TextContent,
    ThinkingLevel,
    Usage,
)


def create_model():
    """Create a test model."""
    return Model(
        api="openai-responses",
        provider="openai",
        id="mock-model"
    )


def create_assistant_message(text: str):
    """Create a test assistant message."""
    return {
        "role": "assistant",
        "content": [{"type": "text", "text": text}],
        "api": "openai-responses",
        "provider": "openai",
        "model": "mock",
        "usage": Usage().__dict__,
        "stop_reason": "stop",
        "timestamp": 1234567890,
    }


class MockAssistantStream:
    """Mock stream for testing."""

    def __init__(self):
        self._queue = asyncio.Queue()
        self._result = None
        self._ended = asyncio.Event()

    def push(self, event):
        """Push an event to the stream."""
        self._queue.put_nowait(event)

    def end(self, result=None):
        """End the stream."""
        self._result = result
        self._ended.set()

    async def __aiter__(self):
        while True:
            try:
                event = self._queue.get_nowait()
                yield event
                continue
            except asyncio.QueueEmpty:
                pass

            if self._ended.is_set():
                return

            done, pending = await asyncio.wait(
                [asyncio.create_task(self._queue.get()),
                 asyncio.create_task(self._ended.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            if self._ended.is_set() and self._queue.empty():
                return

            try:
                event = self._queue.get_nowait()
                yield event
            except asyncio.QueueEmpty:
                pass


class TestAgent:
    """Tests for Agent class."""

    def test_create_agent_with_default_state(self):
        """Test creating an agent instance with default state."""
        agent = Agent()

        assert agent.state is not None
        assert agent.state.system_prompt == ""
        # Model should be None in Python (no default model)
        assert agent.state.thinking_level == ThinkingLevel.OFF
        assert agent.state.tools == []
        assert agent.state.messages == []
        assert agent.state.is_streaming is False
        assert agent.state.stream_message is None
        assert agent.state.pending_tool_calls == set()
        assert agent.state.error is None

    def test_create_agent_with_custom_initial_state(self):
        """Test creating an agent with custom initial state."""
        model = create_model()
        opts = AgentOptions(
            initial_state={
                "system_prompt": "You are a helpful assistant.",
                "model": model,
                "thinking_level": ThinkingLevel.LOW,
            }
        )
        agent = Agent(opts)

        assert agent.state.system_prompt == "You are a helpful assistant."
        assert agent.state.model == model
        assert agent.state.thinking_level == ThinkingLevel.LOW

    def test_subscribe_to_events(self):
        """Test subscribing to events."""
        agent = Agent()

        event_count = 0

        def on_event(event):
            nonlocal event_count
            event_count += 1

        unsubscribe = agent.subscribe(on_event)

        # No initial event on subscribe
        assert event_count == 0

        # State mutators don't emit events
        agent.set_system_prompt("Test prompt")
        assert event_count == 0
        assert agent.state.system_prompt == "Test prompt"

        # Unsubscribe should work
        unsubscribe()
        agent.set_system_prompt("Another prompt")
        assert event_count == 0  # Should not increase

    def test_update_state_with_mutators(self):
        """Test updating state with mutators."""
        agent = Agent()

        # Test setSystemPrompt
        agent.set_system_prompt("Custom prompt")
        assert agent.state.system_prompt == "Custom prompt"

        # Test setModel
        new_model = create_model()
        agent.set_model(new_model)
        assert agent.state.model == new_model

        # Test setThinkingLevel
        agent.set_thinking_level(ThinkingLevel.HIGH)
        assert agent.state.thinking_level == ThinkingLevel.HIGH

        # Test setTools
        tools = [AgentTool(name="test", description="test tool", parameters={}, label="Test")]
        agent.set_tools(tools)
        assert agent.state.tools == tools

        # Test replaceMessages
        messages = [{"role": "user", "content": "Hello", "timestamp": 123}]
        agent.replace_messages(messages)
        assert agent.state.messages == messages
        assert agent.state.messages is not messages  # Should be a copy

        # Test appendMessage
        new_message = {"role": "assistant", "content": [{"type": "text", "text": "Hi"}]}
        agent.append_message(new_message)
        assert len(agent.state.messages) == 2
        assert agent.state.messages[1] == new_message

        # Test clearMessages
        agent.clear_messages()
        assert agent.state.messages == []

    def test_steering_message_queue(self):
        """Test steering message queue."""
        agent = Agent()

        message = {"role": "user", "content": "Steering message", "timestamp": 123}
        agent.steer(message)

        # The message is queued but not yet in state.messages
        assert message not in agent.state.messages

    def test_follow_up_message_queue(self):
        """Test follow-up message queue."""
        agent = Agent()

        message = {"role": "user", "content": "Follow-up message", "timestamp": 123}
        agent.follow_up(message)

        # The message is queued but not yet in state.messages
        assert message not in agent.state.messages

    def test_abort_controller(self):
        """Test abort controller."""
        agent = Agent()

        # Should not throw even if nothing is running
        agent.abort()

    def test_has_queued_messages(self):
        """Test has_queued_messages method."""
        agent = Agent()

        assert agent.has_queued_messages() is False

        agent.steer({"role": "user", "content": "test", "timestamp": 123})
        assert agent.has_queued_messages() is True

        agent.clear_steering_queue()
        assert agent.has_queued_messages() is False

        agent.follow_up({"role": "user", "content": "test", "timestamp": 123})
        assert agent.has_queued_messages() is True

        agent.clear_all_queues()
        assert agent.has_queued_messages() is False

    def test_steering_and_follow_up_modes(self):
        """Test steering and follow-up modes."""
        agent = Agent()

        assert agent.get_steering_mode() == "one-at-a-time"
        assert agent.get_follow_up_mode() == "one-at-a-time"

        agent.set_steering_mode("all")
        assert agent.get_steering_mode() == "all"

        agent.set_follow_up_mode("all")
        assert agent.get_follow_up_mode() == "all"

    def test_session_id(self):
        """Test session ID."""
        opts = AgentOptions(session_id="session-abc")
        agent = Agent(opts)

        assert agent.session_id == "session-abc"

        agent.session_id = "session-def"
        assert agent.session_id == "session-def"

    def test_reset(self):
        """Test reset method."""
        agent = Agent()

        agent.set_system_prompt("Test prompt")
        agent.append_message({"role": "user", "content": "Hello", "timestamp": 123})
        agent.steer({"role": "user", "content": "Steer", "timestamp": 123})
        agent.follow_up({"role": "user", "content": "Follow", "timestamp": 123})

        agent.reset()

        assert agent.state.messages == []
        assert agent.state.is_streaming is False
        assert agent.state.stream_message is None
        assert agent.state.pending_tool_calls == set()
        assert agent.state.error is None
        assert not agent.has_queued_messages()


class TestDefaultConvertToLlm:
    """Tests for default_convert_to_llm function."""

    def test_filter_non_llm_messages(self):
        """Test that non-LLM messages are filtered out."""
        messages = [
            {"role": "user", "content": "Hello", "timestamp": 123},
            {"role": "assistant", "content": [], "timestamp": 124},
            {"role": "toolResult", "content": [], "tool_call_id": "1", "timestamp": 125},
            {"role": "notification", "text": "Notification", "timestamp": 126},
            {"role": "custom", "content": "Custom", "timestamp": 127},
        ]

        result = default_convert_to_llm(messages)

        assert len(result) == 3
        assert result[0]["role"] == "user"
        assert result[1]["role"] == "assistant"
        assert result[2]["role"] == "toolResult"


class TestAgentOptions:
    """Tests for AgentOptions class."""

    def test_default_options(self):
        """Test default options."""
        opts = AgentOptions()
        assert opts.initial_state is None
        assert opts.convert_to_llm is None
        assert opts.transform_context is None
        assert opts.steering_mode == "one-at-a-time"
        assert opts.follow_up_mode == "one-at-a-time"
        assert opts.stream_fn is None
        assert opts.session_id is None

    def test_custom_options(self):
        """Test custom options."""
        model = create_model()

        async def custom_convert(messages):
            return messages

        opts = AgentOptions(
            initial_state={"model": model},
            convert_to_llm=custom_convert,
            steering_mode="all",
            follow_up_mode="all",
            session_id="test-session",
        )

        assert opts.initial_state == {"model": model}
        assert opts.convert_to_llm == custom_convert
        assert opts.steering_mode == "all"
        assert opts.follow_up_mode == "all"
        assert opts.session_id == "test-session"

