"""
Agent loop that works with AgentMessage throughout.
Transforms to Message[] only at the LLM call boundary.
"""
from __future__ import annotations
import asyncio
from typing import (
    Any,
    AsyncGenerator,
    Callable,
    Dict,
    List,
    Optional,
    Union,
)
from dataclasses import dataclass

from .types import (
    AgentContext,
    AgentEvent,
    AgentLoopConfig,
    AgentMessage,
    AgentTool,
    AgentToolResult,
    AssistantMessage,
    Context,
    Message,
    TextContent,
    ToolResultMessage,
    StreamFn,
)


@dataclass
class EventStream:
    """Async event stream that yields events and returns a final result."""
    events: List[AgentEvent]
    result: Any

    def __aiter__(self):
        return self

    async def __anext__(self) -> AgentEvent:
        if not self.events:
            raise StopAsyncIteration
        return self.events.pop(0)


class AgentStream:
    """Stream for agent events."""

    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._result: Optional[List[AgentMessage]] = None
        self._ended = asyncio.Event()

    def push(self, event: AgentEvent):
        """Push an event to the stream."""
        self._queue.put_nowait(event)

    def end(self, result: Optional[List[AgentMessage]] = None):
        """End the stream with a final result."""
        self._result = result
        self._ended.set()

    async def __aiter__(self):
        while True:
            # Check if we have events in the queue
            try:
                event = self._queue.get_nowait()
                yield event
                continue
            except asyncio.QueueEmpty:
                pass

            # Check if stream has ended
            if self._ended.is_set():
                return

            # Wait for either an event or the end
            done, pending = await asyncio.wait(
                [asyncio.create_task(self._queue.get()),
                 asyncio.create_task(self._ended.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )

            for task in pending:
                task.cancel()

            if self._ended.is_set() and self._queue.empty():
                return

            # Get the event
            try:
                event = self._queue.get_nowait()
                yield event
            except asyncio.QueueEmpty:
                pass


def agent_loop(
    prompts: List[AgentMessage],
    context: AgentContext,
    config: AgentLoopConfig,
    signal: Optional[asyncio.Event] = None,
    stream_fn: Optional[StreamFn] = None,
) -> AgentStream:
    """
    Start an agent loop with a new prompt message.
    The prompt is added to the context and events are emitted for it.
    """
    stream = AgentStream()

    async def run():
        new_messages: List[AgentMessage] = [*prompts]
        current_context = AgentContext(
            system_prompt=context.system_prompt,
            messages=[*context.messages, *prompts],
            tools=context.tools,
        )

        stream.push({"type": "agent_start"})
        stream.push({"type": "turn_start"})

        for prompt in prompts:
            stream.push({"type": "message_start", "message": prompt})
            stream.push({"type": "message_end", "message": prompt})

        await _run_loop(current_context, new_messages, config, signal, stream, stream_fn)

    asyncio.create_task(run())
    return stream


def agent_loop_continue(
    context: AgentContext,
    config: AgentLoopConfig,
    signal: Optional[asyncio.Event] = None,
    stream_fn: Optional[StreamFn] = None,
) -> AgentStream:
    """
    Continue an agent loop from the current context without adding a new message.
    Used for retries - context already has user message or tool results.

    Important: The last message in context must convert to a user or toolResult message.
    """
    if not context.messages:
        raise RuntimeError("Cannot continue: no messages in context")

    if context.messages[-1].get("role") == "assistant":
        raise RuntimeError("Cannot continue from message role: assistant")

    stream = AgentStream()

    async def run():
        new_messages: List[AgentMessage] = []
        current_context = AgentContext(
            system_prompt=context.system_prompt,
            messages=context.messages.copy(),
            tools=context.tools,
        )

        stream.push({"type": "agent_start"})
        stream.push({"type": "turn_start"})

        await _run_loop(current_context, new_messages, config, signal, stream, stream_fn)

    asyncio.create_task(run())
    return stream


async def _run_loop(
    current_context: AgentContext,
    new_messages: List[AgentMessage],
    config: AgentLoopConfig,
    signal: Optional[asyncio.Event],
    stream: AgentStream,
    stream_fn: Optional[StreamFn],
) -> None:
    """Main loop logic shared by agent_loop and agent_loop_continue."""
    first_turn = True

    # Check for steering messages at start
    get_steering = config.get_steering_messages
    pending_messages: List[AgentMessage] = await get_steering() if get_steering else []

    # Outer loop: continues when queued follow-up messages arrive
    while True:
        has_more_tool_calls = True
        steering_after_tools: Optional[List[AgentMessage]] = None

        # Inner loop: process tool calls and steering messages
        while has_more_tool_calls or pending_messages:
            if not first_turn:
                stream.push({"type": "turn_start"})
            else:
                first_turn = False

            # Process pending messages
            if pending_messages:
                for message in pending_messages:
                    stream.push({"type": "message_start", "message": message})
                    stream.push({"type": "message_end", "message": message})
                    current_context.messages.append(message)
                    new_messages.append(message)
                pending_messages = []

            # Stream assistant response
            message = await _stream_assistant_response(
                current_context, config, signal, stream, stream_fn
            )
            new_messages.append(message)

            if message.get("stop_reason") in ("error", "aborted"):
                stream.push({"type": "turn_end", "message": message, "tool_results": []})
                stream.push({"type": "agent_end", "messages": new_messages})
                stream.end(new_messages)
                return

            # Check for tool calls
            content = message.get("content", [])
            tool_calls = [c for c in content if c.get("type") == "toolCall"]
            has_more_tool_calls = len(tool_calls) > 0

            tool_results: List[ToolResultMessage] = []
            if has_more_tool_calls:
                tool_execution = await _execute_tool_calls(
                    current_context.tools,
                    message,
                    signal,
                    stream,
                    config.get_steering_messages,
                )
                tool_results.extend(tool_execution["tool_results"])
                steering_after_tools = tool_execution.get("steering_messages")

                for result in tool_results:
                    current_context.messages.append(result)
                    new_messages.append(result)

            stream.push({"type": "turn_end", "message": message, "tool_results": tool_results})

            # Get steering messages after turn completes
            if steering_after_tools:
                pending_messages = steering_after_tools
                steering_after_tools = None
            else:
                pending_messages = await get_steering() if get_steering else []

        # Check for follow-up messages
        get_follow_up = config.get_follow_up_messages
        follow_up_messages = await get_follow_up() if get_follow_up else []
        if follow_up_messages:
            pending_messages = follow_up_messages
            continue

        # No more messages, exit
        break

    stream.push({"type": "agent_end", "messages": new_messages})
    stream.end(new_messages)


async def _stream_assistant_response(
    context: AgentContext,
    config: AgentLoopConfig,
    signal: Optional[asyncio.Event],
    stream: AgentStream,
    stream_fn: Optional[StreamFn],
) -> Dict[str, Any]:
    """
    Stream an assistant response from the LLM.
    This is where AgentMessage[] gets transformed to Message[] for the LLM.
    """
    # Apply context transform if configured
    messages = context.messages
    if config.transform_context:
        messages = await config.transform_context(messages, signal)

    # Convert to LLM-compatible messages
    convert_fn = config.convert_to_llm
    if asyncio.iscoroutinefunction(convert_fn):
        llm_messages = await convert_fn(messages)
    else:
        llm_messages = convert_fn(messages)

    # Build LLM context
    llm_context = Context(
        system_prompt=context.system_prompt,
        messages=llm_messages,
        tools=context.tools,
    )

    # Resolve API key
    resolved_api_key = None
    if config.get_api_key:
        get_key = config.get_api_key(config.model.provider)
        if asyncio.iscoroutine(get_key):
            resolved_api_key = await get_key
        else:
            resolved_api_key = get_key
    resolved_api_key = resolved_api_key or config.api_key

    # Build options
    options = {
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "reasoning": config.reasoning,
        "session_id": config.session_id,
        "api_key": resolved_api_key,
        "signal": signal,
        "thinking_budgets": config.thinking_budgets,
    }

    # Use stream function or default
    if stream_fn:
        response = await stream_fn(config.model, llm_context, options)
    else:
        # Would call stream_simple from pi-ai
        raise NotImplementedError("No stream function provided. Import from pi-ai or provide custom stream_fn.")

    partial_message: Optional[Dict[str, Any]] = None
    added_partial = False

    async for event in response:
        event_type = event.get("type")

        if event_type == "start":
            partial_message = event.get("partial", {})
            context.messages.append(partial_message)
            added_partial = True
            stream.push({"type": "message_start", "message": {**partial_message}})

        elif event_type in (
            "text_start", "text_delta", "text_end",
            "thinking_start", "thinking_delta", "thinking_end",
            "toolcall_start", "toolcall_delta", "toolcall_end"
        ):
            if partial_message:
                partial_message = event.get("partial", partial_message)
                context.messages[-1] = partial_message
                stream.push({
                    "type": "message_update",
                    "assistant_message_event": event,
                    "message": {**partial_message},
                })

        elif event_type in ("done", "error"):
            # Get final message from response
            final_message = event.get("partial", partial_message or {})
            if added_partial:
                context.messages[-1] = final_message
            else:
                context.messages.append(final_message)

            if not added_partial:
                stream.push({"type": "message_start", "message": {**final_message}})

            stream.push({"type": "message_end", "message": final_message})
            return final_message

    # Return final result
    return partial_message or {}


async def _execute_tool_calls(
    tools: Optional[List[AgentTool]],
    assistant_message: Dict[str, Any],
    signal: Optional[asyncio.Event],
    stream: AgentStream,
    get_steering_messages: Optional[Callable[[], Awaitable[List[AgentMessage]]]],
) -> Dict[str, Any]:
    """Execute tool calls from an assistant message."""
    content = assistant_message.get("content", [])
    tool_calls = [c for c in content if c.get("type") == "toolCall"]

    results: List[ToolResultMessage] = []
    steering_messages: Optional[List[AgentMessage]] = None

    for index, tool_call in enumerate(tool_calls):
        tool_call_id = tool_call.get("id", "")
        tool_name = tool_call.get("name", "")
        args = tool_call.get("arguments", {})

        tool = None
        if tools:
            tool = next((t for t in tools if t.name == tool_name), None)

        stream.push({
            "type": "tool_execution_start",
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "args": args,
        })

        result: AgentToolResult
        is_error = False

        try:
            if not tool:
                raise RuntimeError(f"Tool {tool_name} not found")

            # Validate arguments (simplified)
            validated_args = args

            # Execute tool
            execute_fn = tool.execute
            if execute_fn is None:
                raise RuntimeError(f"Tool {tool_name} has no execute function")

            # Call with progress callback
            def on_update(partial_result: AgentToolResult):
                stream.push({
                    "type": "tool_execution_update",
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "args": args,
                    "partial_result": partial_result,
                })

            if asyncio.iscoroutinefunction(execute_fn):
                result = await execute_fn(tool_call_id, validated_args, signal, on_update)
            else:
                result = execute_fn(tool_call_id, validated_args, signal, on_update)

        except Exception as e:
            result = AgentToolResult(
                content=[TextContent(text=str(e))],
                details={},
            )
            is_error = True

        stream.push({
            "type": "tool_execution_end",
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "result": result,
            "is_error": is_error,
        })

        tool_result_message: ToolResultMessage = {
            "role": "toolResult",
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "content": result.content,
            "details": result.details,
            "is_error": is_error,
            "timestamp": int(asyncio.get_event_loop().time() * 1000),
        }

        results.append(tool_result_message)
        stream.push({"type": "message_start", "message": tool_result_message})
        stream.push({"type": "message_end", "message": tool_result_message})

        # Check for steering messages
        if get_steering_messages:
            steering = await get_steering_messages()
            if steering:
                steering_messages = steering
                # Skip remaining tool calls
                remaining_calls = tool_calls[index + 1:]
                for skipped in remaining_calls:
                    results.append(_skip_tool_call(skipped, stream))
                break

    return {"tool_results": results, "steering_messages": steering_messages}


def _skip_tool_call(
    tool_call: Dict[str, Any],
    stream: AgentStream,
) -> ToolResultMessage:
    """Skip a tool call due to steering messages."""
    tool_call_id = tool_call.get("id", "")
    tool_name = tool_call.get("name", "")
    args = tool_call.get("arguments", {})

    result = AgentToolResult(
        content=[TextContent(text="Skipped due to queued user message.")],
        details={},
    )

    stream.push({
        "type": "tool_execution_start",
        "tool_call_id": tool_call_id,
        "tool_name": tool_name,
        "args": args,
    })
    stream.push({
        "type": "tool_execution_end",
        "tool_call_id": tool_call_id,
        "tool_name": tool_name,
        "result": result,
        "is_error": True,
    })

    tool_result_message: ToolResultMessage = {
        "role": "toolResult",
        "tool_call_id": tool_call_id,
        "tool_name": tool_name,
        "content": result.content,
        "details": {},
        "is_error": True,
        "timestamp": int(asyncio.get_event_loop().time() * 1000),
    }

    stream.push({"type": "message_start", "message": tool_result_message})
    stream.push({"type": "message_end", "message": tool_result_message})

    return tool_result_message

