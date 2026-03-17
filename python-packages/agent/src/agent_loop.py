"""
Agent 循环模块

在整个循环中使用 AgentMessage，仅在 LLM 调用边界转换为 Message[]。
这是代理的核心执行引擎，负责：
- 管理 LLM 调用和工具执行的循环
- 处理 steering（中断）和 follow-up（后续）消息
- 发出事件通知 UI 更新

主要函数:
- agent_loop: 启动新的代理循环
- agent_loop_continue: 从现有上下文继续代理循环
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import (
    Any,
    Awaitable,
    Callable,
    Dict,
    List,
    Optional,
)

from .types import (
    AgentContext,
    AgentEvent,
    AgentLoopConfig,
    AgentMessage,
    AgentTool,
    AgentToolResult,
    Context,
    TextContent,
    ToolResultMessage,
    StreamFn,
)


# ============================================================================
# 事件流实现
# ============================================================================

@dataclass
class EventStream:
    """
    异步事件流。

    产出事件并返回最终结果。
    这是简化版的事件流实现，用于测试和演示。
    """
    events: List[AgentEvent]
    result: Any

    def __aiter__(self):
        """返回异步迭代器。"""
        return self

    async def __anext__(self) -> AgentEvent:
        """获取下一个事件。"""
        if not self.events:
            raise StopAsyncIteration
        return self.events.pop(0)


class AgentStream:
    """
    代理事件流。

    使用 asyncio.Queue 实现的异步事件流，
    支持实时推送事件和最终结果。

    使用方法:
        stream = AgentStream()
        stream.push({"type": "message_start", "message": msg})
        stream.end([final_message])

        async for event in stream:
            handle_event(event)
    """

    def __init__(self):
        """初始化事件流。"""
        self._queue: asyncio.Queue = asyncio.Queue()  # 事件队列
        self._result: Optional[List[AgentMessage]] = None  # 最终结果
        self._ended = asyncio.Event()  # 结束标志

    def push(self, event: AgentEvent):
        """
        推送事件到流中。

        Args:
            event: 要推送的事件
        """
        self._queue.put_nowait(event)

    def end(self, result: Optional[List[AgentMessage]] = None):
        """
        结束流并设置最终结果。

        Args:
            result: 最终的消息列表
        """
        self._result = result
        self._ended.set()

    async def __aiter__(self):
        """异步迭代事件。"""
        while True:
            # 尝试从队列获取事件
            try:
                event = self._queue.get_nowait()
                yield event
                continue
            except asyncio.QueueEmpty:
                pass

            # 检查流是否已结束
            if self._ended.is_set():
                return

            # 等待事件或结束信号
            done, pending = await asyncio.wait(
                [asyncio.create_task(self._queue.get()),
                 asyncio.create_task(self._ended.wait())],
                return_when=asyncio.FIRST_COMPLETED
            )

            # 取消未完成的任务
            for task in pending:
                task.cancel()

            # 如果已结束且队列为空，退出
            if self._ended.is_set() and self._queue.empty():
                return

            # 获取事件
            try:
                event = self._queue.get_nowait()
                yield event
            except asyncio.QueueEmpty:
                pass


# ============================================================================
# 公共 API 函数
# ============================================================================

def agent_loop(
    prompts: List[AgentMessage],
    context: AgentContext,
    config: AgentLoopConfig,
    signal: Optional[asyncio.Event] = None,
    stream_fn: Optional[StreamFn] = None,
) -> AgentStream:
    """
    启动代理循环，添加新的提示消息。

    提示会被添加到上下文中，并发出相应的事件。
    这是对外的主要入口点，用于开始新的对话轮次。

    Args:
        prompts: 要添加的提示消息列表
        context: 代理上下文（包含系统提示、消息历史和工具）
        config: 循环配置
        signal: 可选的中止信号
        stream_fn: 可选的流函数（默认使用 streamSimple）

    Returns:
        AgentStream 事件流

    事件序列:
        agent_start → turn_start → message_start/end (每个提示) → ...
    """
    stream = AgentStream()

    async def run():
        # 初始化新消息列表和当前上下文
        new_messages: List[AgentMessage] = [*prompts]
        current_context = AgentContext(
            system_prompt=context.system_prompt,
            messages=[*context.messages, *prompts],
            tools=context.tools,
        )

        # 发出开始事件
        stream.push({"type": "agent_start"})
        stream.push({"type": "turn_start"})

        # 发出提示消息的事件
        for prompt in prompts:
            stream.push({"type": "message_start", "message": prompt})
            stream.push({"type": "message_end", "message": prompt})

        # 运行主循环
        await _run_loop(current_context, new_messages, config, signal, stream, stream_fn)

    # 在后台任务中运行
    asyncio.create_task(run())
    return stream


def agent_loop_continue(
    context: AgentContext,
    config: AgentLoopConfig,
    signal: Optional[asyncio.Event] = None,
    stream_fn: Optional[StreamFn] = None,
) -> AgentStream:
    """
    从当前上下文继续代理循环，不添加新消息。

    用于重试场景 - 上下文已有用户消息或工具结果。

    重要：上下文中的最后一条消息必须通过 convert_to_llm
    转换为 user 或 toolResult 消息。如果是 assistant 消息，
    LLM 提供商会拒绝请求。

    Args:
        context: 代理上下文
        config: 循环配置
        signal: 可选的中止信号
        stream_fn: 可选的流函数

    Returns:
        AgentStream 事件流

    Raises:
        RuntimeError: 如果没有消息或最后一条是 assistant 消息
    """
    if not context.messages:
        raise RuntimeError("Cannot continue: no messages in context")

    if context.messages[-1].get("role") == "assistant":
        raise RuntimeError("Cannot continue from message role: assistant")

    stream = AgentStream()

    async def run():
        # 不添加新消息，继续现有上下文
        new_messages: List[AgentMessage] = []
        current_context = AgentContext(
            system_prompt=context.system_prompt,
            messages=context.messages.copy(),
            tools=context.tools,
        )

        # 发出开始事件
        stream.push({"type": "agent_start"})
        stream.push({"type": "turn_start"})

        # 运行主循环
        await _run_loop(current_context, new_messages, config, signal, stream, stream_fn)

    asyncio.create_task(run())
    return stream


# ============================================================================
# 内部实现函数
# ============================================================================

async def _run_loop(
    current_context: AgentContext,
    new_messages: List[AgentMessage],
    config: AgentLoopConfig,
    signal: Optional[asyncio.Event],
    stream: AgentStream,
    stream_fn: Optional[StreamFn],
) -> None:
    """
    主循环逻辑，被 agent_loop 和 agent_loop_continue 共享。

    循环结构:
    1. 外层 while(true): 处理 follow-up 消息
    2. 内层 while(hasMoreToolCalls): 处理工具调用和 steering 消息

    Args:
        current_context: 当前代理上下文
        new_messages: 本次循环产生的新消息列表
        config: 循环配置
        signal: 中止信号
        stream: 事件流
        stream_fn: 流函数
    """
    first_turn = True

    # 在开始时检查 steering 消息（用户可能在等待时输入）
    get_steering = config.get_steering_messages
    pending_messages: List[AgentMessage] = await get_steering() if get_steering else []

    # 外层循环: 当排队的 follow-up 消息到达时继续
    while True:
        has_more_tool_calls = True
        steering_after_tools: Optional[List[AgentMessage]] = None

        # 内层循环: 处理工具调用和 steering 消息
        while has_more_tool_calls or pending_messages:
            if not first_turn:
                stream.push({"type": "turn_start"})
            else:
                first_turn = False

            # 处理待处理的消息（steering 或 follow-up）
            if pending_messages:
                for message in pending_messages:
                    stream.push({"type": "message_start", "message": message})
                    stream.push({"type": "message_end", "message": message})
                    current_context.messages.append(message)
                    new_messages.append(message)
                pending_messages = []

            # 流式获取助手响应
            message = await _stream_assistant_response(
                current_context, config, signal, stream, stream_fn
            )
            new_messages.append(message)

            # 检查是否出错或中止
            if message.get("stop_reason") in ("error", "aborted"):
                stream.push({"type": "turn_end", "message": message, "tool_results": []})
                stream.push({"type": "agent_end", "messages": new_messages})
                stream.end(new_messages)
                return

            # 检查工具调用
            content = message.get("content", [])
            tool_calls = [c for c in content if c.get("type") == "toolCall"]
            has_more_tool_calls = len(tool_calls) > 0

            # 执行工具调用
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

                # 将工具结果添加到上下文
                for result in tool_results:
                    current_context.messages.append(result)
                    new_messages.append(result)

            # 发出轮次结束事件
            stream.push({"type": "turn_end", "message": message, "tool_results": tool_results})

            # 在轮次完成后获取 steering 消息
            if steering_after_tools:
                pending_messages = steering_after_tools
                steering_after_tools = None
            else:
                pending_messages = await get_steering() if get_steering else []

        # 检查 follow-up 消息
        get_follow_up = config.get_follow_up_messages
        follow_up_messages = await get_follow_up() if get_follow_up else []
        if follow_up_messages:
            # 设置为待处理，让内层循环处理
            pending_messages = follow_up_messages
            continue

        # 没有更多消息，退出
        break

    # 发出代理结束事件
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
    从 LLM 流式获取助手响应。

    这是 AgentMessage[] 转换为 Message[] 的边界，
    在调用 LLM 之前进行消息转换。

    流程:
    1. 应用 transform_context (可选)
    2. 调用 convert_to_llm (必需)
    3. 构建 LLM 上下文
    4. 解析 API 密钥
    5. 调用流函数
    6. 处理事件流

    Args:
        context: 代理上下文
        config: 循环配置
        signal: 中止信号
        stream: 事件流
        stream_fn: 流函数

    Returns:
        完整的助手消息
    """
    # 应用上下文转换（如果配置了）
    # 用于修剪旧消息或注入外部上下文
    messages = context.messages
    if config.transform_context:
        messages = await config.transform_context(messages, signal)

    # 转换为 LLM 兼容的消息格式
    # 这是必需的步骤，过滤和转换消息
    convert_fn = config.convert_to_llm
    if asyncio.iscoroutinefunction(convert_fn):
        llm_messages = await convert_fn(messages)
    else:
        llm_messages = convert_fn(messages)

    # 构建 LLM 上下文
    llm_context = Context(
        system_prompt=context.system_prompt,
        messages=llm_messages,
        tools=context.tools,
    )

    # 解析 API 密钥（支持动态刷新）
    resolved_api_key = None
    if config.get_api_key:
        get_key = config.get_api_key(config.model.provider)
        if asyncio.iscoroutine(get_key):
            resolved_api_key = await get_key
        else:
            resolved_api_key = get_key
    resolved_api_key = resolved_api_key or config.api_key

    # 构建选项字典
    options = {
        "temperature": config.temperature,
        "max_tokens": config.max_tokens,
        "reasoning": config.reasoning,
        "session_id": config.session_id,
        "api_key": resolved_api_key,
        "signal": signal,
        "thinking_budgets": config.thinking_budgets,
    }

    # 使用流函数或默认
    if stream_fn:
        response = await stream_fn(config.model, llm_context, options)
    else:
        # 需要从 pi-ai 导入 stream_simple
        raise NotImplementedError("No stream function provided. Import from pi-ai or provide custom stream_fn.")

    partial_message: Optional[Dict[str, Any]] = None
    added_partial = False

    # 处理响应事件流
    async for event in response:
        event_type = event.get("type")

        if event_type == "start":
            # 消息开始
            partial_message = event.get("partial", {})
            context.messages.append(partial_message)
            added_partial = True
            stream.push({"type": "message_start", "message": {**partial_message}})

        elif event_type in (
            "text_start", "text_delta", "text_end",
            "thinking_start", "thinking_delta", "thinking_end",
            "toolcall_start", "toolcall_delta", "toolcall_end"
        ):
            # 消息更新（文本、思考、工具调用）
            if partial_message:
                partial_message = event.get("partial", partial_message)
                context.messages[-1] = partial_message
                stream.push({
                    "type": "message_update",
                    "assistant_message_event": event,
                    "message": {**partial_message},
                })

        elif event_type in ("done", "error"):
            # 消息完成或出错
            final_message = event.get("partial", partial_message or {})
            if added_partial:
                context.messages[-1] = final_message
            else:
                context.messages.append(final_message)

            if not added_partial:
                stream.push({"type": "message_start", "message": {**final_message}})

            stream.push({"type": "message_end", "message": final_message})
            return final_message

    # 返回最终结果
    return partial_message or {}


async def _execute_tool_calls(
    tools: Optional[List[AgentTool]],
    assistant_message: Dict[str, Any],
    signal: Optional[asyncio.Event],
    stream: AgentStream,
    get_steering_messages: Optional[Callable[[], Awaitable[List[AgentMessage]]]],
) -> Dict[str, Any]:
    """
    执行助手消息中的工具调用。

    流程:
    1. 提取工具调用列表
    2. 遍历每个工具调用
    3. 查找对应的工具定义
    4. 验证参数
    5. 执行工具
    6. 检查 steering 消息（如有则跳过剩余工具）
    7. 返回工具结果

    Args:
        tools: 可用工具列表
        assistant_message: 包含工具调用的助手消息
        signal: 中止信号
        stream: 事件流
        get_steering_messages: 获取 steering 消息的回调

    Returns:
        包含 tool_results 和可能的 steering_messages 的字典
    """
    content = assistant_message.get("content", [])
    tool_calls = [c for c in content if c.get("type") == "toolCall"]

    results: List[ToolResultMessage] = []
    steering_messages: Optional[List[AgentMessage]] = None

    for index, tool_call in enumerate(tool_calls):
        tool_call_id = tool_call.get("id", "")
        tool_name = tool_call.get("name", "")
        args = tool_call.get("arguments", {})

        # 查找工具定义
        tool = None
        if tools:
            tool = next((t for t in tools if t.name == tool_name), None)

        # 发出工具执行开始事件
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

            # 验证参数（简化版）
            validated_args = args

            # 获取执行函数
            execute_fn = tool.execute
            if execute_fn is None:
                raise RuntimeError(f"Tool {tool_name} has no execute function")

            # 进度更新回调
            def on_update(partial_result: AgentToolResult):
                """工具执行进度更新回调。"""
                stream.push({
                    "type": "tool_execution_update",
                    "tool_call_id": tool_call_id,
                    "tool_name": tool_name,
                    "args": args,
                    "partial_result": partial_result,
                })

            # 执行工具
            if asyncio.iscoroutinefunction(execute_fn):
                result = await execute_fn(tool_call_id, validated_args, signal, on_update)
            else:
                result = execute_fn(tool_call_id, validated_args, signal, on_update)

        except Exception as e:
            # 工具执行出错
            result = AgentToolResult(
                content=[TextContent(text=str(e))],
                details={},
            )
            is_error = True

        # 发出工具执行结束事件
        stream.push({
            "type": "tool_execution_end",
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "result": result,
            "is_error": is_error,
        })

        # 构建工具结果消息
        tool_result_message: ToolResultMessage = {
            "role": "toolResult",
            "tool_call_id": tool_call_id,
            "tool_name": tool_name,
            "content": result.content,
            "details": result.details,
            "is_error": is_error,
            "timestamp": int(time.time() * 1000),
        }

        results.append(tool_result_message)
        stream.push({"type": "message_start", "message": tool_result_message})
        stream.push({"type": "message_end", "message": tool_result_message})

        # 检查 steering 消息
        if get_steering_messages:
            steering = await get_steering_messages()
            if steering:
                steering_messages = steering
                # 跳过剩余的工具调用
                remaining_calls = tool_calls[index + 1:]
                for skipped in remaining_calls:
                    results.append(_skip_tool_call(skipped, stream))
                break

    return {"tool_results": results, "steering_messages": steering_messages}


def _skip_tool_call(
    tool_call: Dict[str, Any],
    stream: AgentStream,
) -> ToolResultMessage:
    """
    跳过工具调用（由于 steering 消息）。

    当检测到 steering 消息时，剩余的工具调用会被跳过，
    返回一个表示被跳过的工具结果。

    Args:
        tool_call: 要跳过的工具调用
        stream: 事件流

    Returns:
        表示被跳过的工具结果消息
    """
    tool_call_id = tool_call.get("id", "")
    tool_name = tool_call.get("name", "")
    args = tool_call.get("arguments", {})

    # 创建跳过结果
    result = AgentToolResult(
        content=[TextContent(text="Skipped due to queued user message.")],
        details={},
    )

    # 发出事件
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

    # 构建工具结果消息
    tool_result_message: ToolResultMessage = {
        "role": "toolResult",
        "tool_call_id": tool_call_id,
        "tool_name": tool_name,
        "content": result.content,
        "details": {},
        "is_error": True,
        "timestamp": int(__import__("time").time() * 1000),
    }

    stream.push({"type": "message_start", "message": tool_result_message})
    stream.push({"type": "message_end", "message": tool_result_message})

    return tool_result_message

