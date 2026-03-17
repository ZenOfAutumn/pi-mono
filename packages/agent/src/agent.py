"""
Agent class that uses the agent-loop directly.
No transport abstraction - calls stream_simple via the loop.
"""
from __future__ import annotations
import asyncio
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    Union,
    Awaitable,
)
from copy import deepcopy

from .types import (
    AgentContext,
    AgentEvent,
    AgentLoopConfig,
    AgentMessage,
    AgentState,
    AgentTool,
    AssistantMessage,
    ImageContent,
    Message,
    Model,
    TextContent,
    ThinkingLevel,
    ToolResultMessage,
    Usage,
    StreamFn,
)


def default_convert_to_llm(messages: List[AgentMessage]) -> List[Message]:
    """Default convertToLlm: Keep only LLM-compatible messages."""
    return [
        m for m in messages
        if m.get("role") in ("user", "assistant", "toolResult")
    ]


@dataclass
class AgentOptions:
    """Options for creating an Agent."""
    initial_state: Optional[Dict[str, Any]] = None
    # Converts AgentMessage[] to LLM-compatible Message[] before each LLM call.
    convert_to_llm: Optional[Callable[[List[AgentMessage]], Union[List[Message], Awaitable[List[Message]]]]] = None
    # Optional transform applied to context before convertToLlm.
    transform_context: Optional[Callable[[List[AgentMessage], Optional[Any]], Awaitable[List[AgentMessage]]]] = None
    # Steering mode: "all" = send all steering messages at once, "one-at-a-time" = one per turn
    steering_mode: Literal["all", "one-at-a-time"] = "one-at-a-time"
    # Follow-up mode: "all" = send all follow-up messages at once, "one-at-a-time" = one per turn
    follow_up_mode: Literal["all", "one-at-a-time"] = "one-at-a-time"
    # Custom stream function (for proxy backends, etc.).
    stream_fn: Optional[StreamFn] = None
    # Optional session identifier forwarded to LLM providers.
    session_id: Optional[str] = None
    # Resolves an API key dynamically for each LLM call.
    get_api_key: Optional[Callable[[str], Union[Optional[str], Awaitable[Optional[str]]]]] = None
    # Inspect or replace provider payloads before they are sent.
    on_payload: Optional[Callable[[Dict[str, Any]], None]] = None
    # Custom token budgets for thinking levels.
    thinking_budgets: Optional[Dict[str, int]] = None
    # Preferred transport for providers.
    transport: str = "sse"
    # Maximum delay in milliseconds to wait for a retry.
    max_retry_delay_ms: Optional[int] = None


class Agent:
    """
    Agent class that uses the agent-loop directly.
    Manages conversation state, tool execution, and event streaming.
    """

    def __init__(self, opts: Optional[AgentOptions] = None):
        opts = opts or AgentOptions()

        # Initialize state with defaults
        self._state = AgentState(
            system_prompt="",
            model=None,
            thinking_level=ThinkingLevel.OFF,
            tools=[],
            messages=[],
            is_streaming=False,
            stream_message=None,
            pending_tool_calls=set(),
            error=None,
        )

        # Override with initial state if provided
        if opts.initial_state:
            for key, value in opts.initial_state.items():
                if hasattr(self._state, key):
                    setattr(self._state, key, value)

        self._convert_to_llm = opts.convert_to_llm or default_convert_to_llm
        self._transform_context = opts.transform_context
        self._steering_mode = opts.steering_mode
        self._follow_up_mode = opts.follow_up_mode
        self._stream_fn = opts.stream_fn
        self._session_id = opts.session_id
        self._get_api_key = opts.get_api_key
        self._on_payload = opts.on_payload
        self._thinking_budgets = opts.thinking_budgets
        self._transport = opts.transport
        self._max_retry_delay_ms = opts.max_retry_delay_ms

        self._listeners: Set[Callable[[AgentEvent], None]] = set()
        self._abort_event: Optional[asyncio.Event] = None
        self._steering_queue: List[AgentMessage] = []
        self._follow_up_queue: List[AgentMessage] = []
        self._running_task: Optional[asyncio.Task] = None

    @property
    def state(self) -> AgentState:
        """Get the current agent state."""
        return self._state

    @property
    def session_id(self) -> Optional[str]:
        """Get the current session ID."""
        return self._session_id

    @session_id.setter
    def session_id(self, value: Optional[str]):
        """Set the session ID for provider caching."""
        self._session_id = value

    @property
    def thinking_budgets(self) -> Optional[Dict[str, int]]:
        """Get the current thinking budgets."""
        return self._thinking_budgets

    @thinking_budgets.setter
    def thinking_budgets(self, value: Optional[Dict[str, int]]):
        """Set custom thinking budgets for token-based providers."""
        self._thinking_budgets = value

    @property
    def transport(self) -> str:
        """Get the current preferred transport."""
        return self._transport

    def set_transport(self, value: str):
        """Set the preferred transport."""
        self._transport = value

    @property
    def max_retry_delay_ms(self) -> Optional[int]:
        """Get the current max retry delay."""
        return self._max_retry_delay_ms

    @max_retry_delay_ms.setter
    def max_retry_delay_ms(self, value: Optional[int]):
        """Set the maximum delay to wait for server-requested retries."""
        self._max_retry_delay_ms = value

    def subscribe(self, fn: Callable[[AgentEvent], None]) -> Callable[[], None]:
        """
        Subscribe to agent events.
        Returns an unsubscribe function.
        """
        self._listeners.add(fn)
        return lambda: self._listeners.discard(fn)

    # State mutators
    def set_system_prompt(self, value: str):
        """Set the system prompt."""
        self._state.system_prompt = value

    def set_model(self, model: Model):
        """Set the model."""
        self._state.model = model

    def set_thinking_level(self, level: ThinkingLevel):
        """Set the thinking level."""
        self._state.thinking_level = level

    def set_steering_mode(self, mode: Literal["all", "one-at-a-time"]):
        """Set the steering mode."""
        self._steering_mode = mode

    def get_steering_mode(self) -> Literal["all", "one-at-a-time"]:
        """Get the steering mode."""
        return self._steering_mode

    def set_follow_up_mode(self, mode: Literal["all", "one-at-a-time"]):
        """Set the follow-up mode."""
        self._follow_up_mode = mode

    def get_follow_up_mode(self) -> Literal["all", "one-at-a-time"]:
        """Get the follow-up mode."""
        return self._follow_up_mode

    def set_tools(self, tools: List[AgentTool]):
        """Set the tools."""
        self._state.tools = tools

    def replace_messages(self, messages: List[AgentMessage]):
        """Replace all messages."""
        self._state.messages = messages.copy()

    def append_message(self, message: AgentMessage):
        """Append a message to the conversation."""
        self._state.messages = [*self._state.messages, message]

    def steer(self, message: AgentMessage):
        """
        Queue a steering message to interrupt the agent mid-run.
        Delivered after current tool execution, skips remaining tools.
        """
        self._steering_queue.append(message)

    def follow_up(self, message: AgentMessage):
        """
        Queue a follow-up message to be processed after the agent finishes.
        Delivered only when agent has no more tool calls or steering messages.
        """
        self._follow_up_queue.append(message)

    def clear_steering_queue(self):
        """Clear the steering queue."""
        self._steering_queue = []

    def clear_follow_up_queue(self):
        """Clear the follow-up queue."""
        self._follow_up_queue = []

    def clear_all_queues(self):
        """Clear all message queues."""
        self._steering_queue = []
        self._follow_up_queue = []

    def has_queued_messages(self) -> bool:
        """Check if there are any queued messages."""
        return len(self._steering_queue) > 0 or len(self._follow_up_queue) > 0

    def _dequeue_steering_messages(self) -> List[AgentMessage]:
        """Dequeue steering messages based on mode."""
        if self._steering_mode == "one-at-a-time":
            if self._steering_queue:
                first = self._steering_queue[0]
                self._steering_queue = self._steering_queue[1:]
                return [first]
            return []

        steering = self._steering_queue.copy()
        self._steering_queue = []
        return steering

    def _dequeue_follow_up_messages(self) -> List[AgentMessage]:
        """Dequeue follow-up messages based on mode."""
        if self._follow_up_mode == "one-at-a-time":
            if self._follow_up_queue:
                first = self._follow_up_queue[0]
                self._follow_up_queue = self._follow_up_queue[1:]
                return [first]
            return []

        follow_up = self._follow_up_queue.copy()
        self._follow_up_queue = []
        return follow_up

    def clear_messages(self):
        """Clear all messages."""
        self._state.messages = []

    def abort(self):
        """Abort the current operation."""
        if self._abort_event:
            self._abort_event.set()

    async def wait_for_idle(self) -> None:
        """Wait for the agent to become idle."""
        if self._running_task:
            await self._running_task

    def reset(self):
        """Reset the agent state."""
        self._state.messages = []
        self._state.is_streaming = False
        self._state.stream_message = None
        self._state.pending_tool_calls = set()
        self._state.error = None
        self._steering_queue = []
        self._follow_up_queue = []

    async def prompt(
        self,
        input: Union[str, AgentMessage, List[AgentMessage]],
        images: Optional[List[ImageContent]] = None,
    ) -> None:
        """
        Send a prompt to the agent.
        Can accept a string, single message, or list of messages.
        """
        if self._state.is_streaming:
            raise RuntimeError(
                "Agent is already processing a prompt. Use steer() or follow_up() to queue messages, "
                "or wait for completion."
            )

        model = self._state.model
        if not model:
            raise RuntimeError("No model configured")

        msgs: List[AgentMessage]

        if isinstance(input, list):
            msgs = input
        elif isinstance(input, str):
            content: List[Union[TextContent, ImageContent]] = [TextContent(text=input)]
            if images:
                content.extend(images)
            msgs = [{
                "role": "user",
                "content": [{"type": c.type, **{k: v for k, v in c.__dict__.items() if k != "type"}}
                           for c in content],
                "timestamp": int(asyncio.get_event_loop().time() * 1000),
            }]
        else:
            msgs = [input]

        await self._run_loop(msgs)

    async def continue_(self) -> None:
        """
        Continue from current context.
        Used for retries and resuming queued messages.
        """
        if self._state.is_streaming:
            raise RuntimeError("Agent is already processing. Wait for completion before continuing.")

        messages = self._state.messages
        if not messages:
            raise RuntimeError("No messages to continue from")

        if messages[-1].get("role") == "assistant":
            queued_steering = self._dequeue_steering_messages()
            if queued_steering:
                await self._run_loop(queued_steering, skip_initial_steering_poll=True)
                return

            queued_follow_up = self._dequeue_follow_up_messages()
            if queued_follow_up:
                await self._run_loop(queued_follow_up)
                return

            raise RuntimeError("Cannot continue from message role: assistant")

        await self._run_loop()

    async def _run_loop(
        self,
        messages: Optional[List[AgentMessage]] = None,
        skip_initial_steering_poll: bool = False,
    ) -> None:
        """Run the agent loop."""
        from .agent_loop import agent_loop, agent_loop_continue

        model = self._state.model
        if not model:
            raise RuntimeError("No model configured")

        self._abort_event = asyncio.Event()
        self._state.is_streaming = True
        self._state.stream_message = None
        self._state.error = None

        reasoning = None if self._state.thinking_level == ThinkingLevel.OFF else self._state.thinking_level.value

        context = AgentContext(
            system_prompt=self._state.system_prompt,
            messages=self._state.messages.copy(),
            tools=self._state.tools,
        )

        config = AgentLoopConfig(
            model=model,
            reasoning=reasoning,
            convert_to_llm=self._convert_to_llm,
            transform_context=self._transform_context,
            get_api_key=self._get_api_key,
            session_id=self._session_id,
            thinking_budgets=self._thinking_budgets,
            get_steering_messages=self._dequeue_steering_messages if not skip_initial_steering_poll else lambda: [],
            get_follow_up_messages=self._dequeue_follow_up_messages,
        )

        partial: Optional[AgentMessage] = None

        try:
            if messages:
                stream = agent_loop(messages, context, config, self._abort_event, self._stream_fn)
            else:
                stream = agent_loop_continue(context, config, self._abort_event, self._stream_fn)

            async for event in stream:
                # Update internal state based on events
                if event["type"] == "message_start":
                    partial = event["message"]
                    self._state.stream_message = event["message"]

                elif event["type"] == "message_update":
                    partial = event["message"]
                    self._state.stream_message = event["message"]

                elif event["type"] == "message_end":
                    partial = None
                    self._state.stream_message = None
                    self.append_message(event["message"])

                elif event["type"] == "tool_execution_start":
                    self._state.pending_tool_calls.add(event["tool_call_id"])

                elif event["type"] == "tool_execution_end":
                    self._state.pending_tool_calls.discard(event["tool_call_id"])

                elif event["type"] == "turn_end":
                    if event["message"].get("role") == "assistant" and event["message"].get("error_message"):
                        self._state.error = event["message"]["error_message"]

                elif event["type"] == "agent_end":
                    self._state.is_streaming = False
                    self._state.stream_message = None

                # Emit to listeners
                self._emit(event)

            # Handle any remaining partial message
            if partial and partial.get("role") == "assistant" and partial.get("content"):
                content = partial.get("content", [])
                has_content = any(
                    (c.get("type") == "thinking" and c.get("thinking", "").strip()) or
                    (c.get("type") == "text" and c.get("text", "").strip()) or
                    (c.get("type") == "toolCall" and c.get("name", "").strip())
                    for c in content
                )
                if has_content:
                    self.append_message(partial)
                elif self._abort_event and self._abort_event.is_set():
                    raise RuntimeError("Request was aborted")

        except Exception as err:
            error_msg: AgentMessage = {
                "role": "assistant",
                "content": [{"type": "text", "text": ""}],
                "api": model.api,
                "provider": model.provider,
                "model": model.id,
                "usage": Usage().__dict__,
                "stopReason": "aborted" if self._abort_event and self._abort_event.is_set() else "error",
                "errorMessage": str(err),
                "timestamp": int(asyncio.get_event_loop().time() * 1000),
            }

            self.append_message(error_msg)
            self._state.error = str(err)
            self._emit({"type": "agent_end", "messages": [error_msg]})

        finally:
            self._state.is_streaming = False
            self._state.stream_message = None
            self._state.pending_tool_calls = set()
            self._abort_event = None

    def _emit(self, event: AgentEvent):
        """Emit an event to all listeners."""
        for listener in self._listeners:
            listener(event)

