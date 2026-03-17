"""
Agent 类模块

提供高层 API 来管理代理的状态、消息和工具。
直接使用 agent-loop，无传输抽象层，通过循环调用 stream_simple。

主要功能:
- 状态管理：系统提示、模型、思考级别、工具配置
- 消息队列：steering（中断）和 follow-up（后续）消息
- 事件订阅：实时通知代理状态变化
- 流式处理：支持中断和恢复
"""
from __future__ import annotations

import asyncio
from dataclasses import dataclass
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

from .types import (
    AgentContext,
    AgentEvent,
    AgentLoopConfig,
    AgentMessage,
    AgentState,
    AgentTool,
    AssistantMessage,
    ImageContent,
    Model,
    TextContent,
    ThinkingLevel,
    ToolResultMessage,
    Usage,
    StreamFn,
    UserMessage,
)


# ============================================================================
# 默认转换函数
# ============================================================================

def default_convert_to_llm(messages: List[AgentMessage]) -> List[Union[UserMessage, AssistantMessage, ToolResultMessage]]:
    """
    默认的消息转换函数。

    过滤消息，只保留 LLM 兼容的消息类型：
    - user: 用户消息
    - assistant: 助手消息
    - toolResult: 工具结果消息

    自定义消息类型会被过滤掉，不会发送给 LLM。

    Args:
        messages: AgentMessage 列表

    Returns:
        过滤后的 LLM 兼容消息列表
    """
    return [
        m for m in messages
        if m.get("role") in ("user", "assistant", "toolResult")
    ]


# ============================================================================
# Agent 配置选项
# ============================================================================

@dataclass
class AgentOptions:
    """
    Agent 配置选项。

    主要配置项:
    - initial_state: 初始状态（系统提示、模型等）
    - convert_to_llm: 消息转换函数（处理自定义消息类型必需）
    - transform_context: 上下文转换函数（用于修剪、压缩）
    - steering_mode: 引导模式（一次性发送或逐个发送）
    - follow_up_mode: 跟进模式（一次性发送或逐个发送）
    - stream_fn: 自定义流函数（用于代理后端）
    """

    # 初始状态配置
    initial_state: Optional[Dict[str, Any]] = None

    # 将 AgentMessage[] 转换为 LLM 兼容的 Message[]
    # 在每次 LLM 调用前执行，过滤和转换消息
    convert_to_llm: Optional[Callable[[List[AgentMessage]], Union[List[Dict[str, Any]], Awaitable[List[Dict[str, Any]]]]]] = None

    # 可选的上下文转换函数
    # 在 convert_to_llm 之前执行，用于修剪旧消息或注入外部上下文
    transform_context: Optional[Callable[[List[AgentMessage], Optional[Any]], Awaitable[List[AgentMessage]]]] = None

    # 引导模式:
    # - "all": 一次性发送所有引导消息
    # - "one-at-a-time": 每轮发送一条引导消息（默认）
    steering_mode: Literal["all", "one-at-a-time"] = "one-at-a-time"

    # 跟进模式:
    # - "all": 一次性发送所有跟进消息
    # - "one-at-a-time": 每轮发送一条跟进消息（默认）
    follow_up_mode: Literal["all", "one-at-a-time"] = "one-at-a-time"

    # 自定义流函数（用于代理后端等场景）
    # 默认使用 streamSimple，可替换为 streamProxy
    stream_fn: Optional[StreamFn] = None

    # 会话 ID，转发给 LLM 提供商
    # 用于支持会话缓存的提供商（如 OpenAI Codex）
    session_id: Optional[str] = None

    # 动态 API 密钥解析函数
    # 适用于会过期的令牌（如 GitHub Copilot OAuth）
    get_api_key: Optional[Callable[[str], Union[Optional[str], Awaitable[Optional[str]]]]] = None

    # 请求载荷检查/替换回调
    # 在发送给提供商之前调用，可检查或修改请求
    on_payload: Optional[Callable[[Dict[str, Any]], None]] = None

    # 自定义思考级别 token 预算
    # 用于支持思考功能的模型
    thinking_budgets: Optional[Dict[str, int]] = None

    # 首选传输方式（sse, ws 等）
    transport: str = "sse"

    # 最大重试延迟（毫秒）
    # 当服务器请求较长等待时间时的上限
    max_retry_delay_ms: Optional[int] = None


# ============================================================================
# Agent 主类
# ============================================================================

class Agent:
    """
    Agent 类。

    提供高层 API 来管理代理的状态、消息和工具。
    直接使用 agent-loop，无传输抽象层。

    主要功能:
    - 状态管理：系统提示、模型、思考级别、工具配置
    - 消息队列：steering（中断）和 follow-up（后续）消息
    - 事件订阅：实时通知代理状态变化
    - 流式处理：支持中断和恢复

    使用示例:
        agent = Agent({
            "initial_state": {
                "system_prompt": "You are helpful.",
                "model": Model(api="openai-chat", provider="openai", id="gpt-4o"),
            }
        })

        agent.subscribe(lambda event: print(event["type"]))
        await agent.prompt("Hello!")
    """

    def __init__(self, opts: Optional[AgentOptions] = None):
        """
        初始化 Agent 实例。

        Args:
            opts: Agent 配置选项
        """
        opts = opts or AgentOptions()

        # 初始化默认状态
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

        # 用初始状态覆盖默认值
        if opts.initial_state:
            for key, value in opts.initial_state.items():
                if hasattr(self._state, key):
                    setattr(self._state, key, value)

        # 配置回调
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

        # 内部状态
        self._listeners: Set[Callable[[AgentEvent], None]] = set()  # 事件监听器
        self._abort_event: Optional[asyncio.Event] = None  # 中止事件
        self._steering_queue: List[AgentMessage] = []  # 引导消息队列
        self._follow_up_queue: List[AgentMessage] = []  # 跟进消息队列
        self._running_task: Optional[asyncio.Task] = None  # 当前运行的任务

    # ========================================================================
    # 属性访问器
    # ========================================================================

    @property
    def state(self) -> AgentState:
        """获取当前代理状态。"""
        return self._state

    @property
    def session_id(self) -> Optional[str]:
        """获取当前会话 ID。"""
        return self._session_id

    @session_id.setter
    def session_id(self, value: Optional[str]):
        """设置会话 ID，用于提供商缓存。"""
        self._session_id = value

    @property
    def thinking_budgets(self) -> Optional[Dict[str, int]]:
        """获取当前思考预算配置。"""
        return self._thinking_budgets

    @thinking_budgets.setter
    def thinking_budgets(self, value: Optional[Dict[str, int]]):
        """设置思考级别的 token 预算，用于支持思考功能的模型。"""
        self._thinking_budgets = value

    @property
    def transport(self) -> str:
        """获取当前首选传输方式。"""
        return self._transport

    def set_transport(self, value: str):
        """设置首选传输方式。"""
        self._transport = value

    @property
    def max_retry_delay_ms(self) -> Optional[int]:
        """获取当前最大重试延迟。"""
        return self._max_retry_delay_ms

    @max_retry_delay_ms.setter
    def max_retry_delay_ms(self, value: Optional[int]):
        """设置服务器请求重试的最大等待延迟。设为 0 禁用上限。"""
        self._max_retry_delay_ms = value

    # ========================================================================
    # 事件订阅
    # ========================================================================

    def subscribe(self, fn: Callable[[AgentEvent], None]) -> Callable[[], None]:
        """
        订阅代理事件。

        事件类型包括:
        - agent_start / agent_end: 代理生命周期
        - turn_start / turn_end: 轮次生命周期
        - message_start / message_update / message_end: 消息生命周期
        - tool_execution_start / tool_execution_update / tool_execution_end: 工具执行生命周期

        Args:
            fn: 事件处理函数

        Returns:
            取消订阅函数
        """
        self._listeners.add(fn)
        return lambda: self._listeners.discard(fn)

    # ========================================================================
    # 状态修改器
    # ========================================================================

    def set_system_prompt(self, value: str):
        """设置系统提示词。"""
        self._state.system_prompt = value

    def set_model(self, model: Model):
        """设置 LLM 模型。"""
        self._state.model = model

    def set_thinking_level(self, level: ThinkingLevel):
        """设置思考级别。"""
        self._state.thinking_level = level

    def set_steering_mode(self, mode: Literal["all", "one-at-a-time"]):
        """设置引导模式。"""
        self._steering_mode = mode

    def get_steering_mode(self) -> Literal["all", "one-at-a-time"]:
        """获取引导模式。"""
        return self._steering_mode

    def set_follow_up_mode(self, mode: Literal["all", "one-at-a-time"]):
        """设置跟进模式。"""
        self._follow_up_mode = mode

    def get_follow_up_mode(self) -> Literal["all", "one-at-a-time"]:
        """获取跟进模式。"""
        return self._follow_up_mode

    def set_tools(self, tools: List[AgentTool]):
        """设置可用工具列表。"""
        self._state.tools = tools

    def replace_messages(self, messages: List[AgentMessage]):
        """替换所有消息。"""
        self._state.messages = messages.copy()

    def append_message(self, message: AgentMessage):
        """追加一条消息到会话历史。"""
        self._state.messages = [*self._state.messages, message]

    # ========================================================================
    # 消息队列管理
    # ========================================================================

    def steer(self, message: AgentMessage):
        """
        排队一条引导消息以中断代理运行。

        引导消息会在当前工具执行完成后发送，
        并跳过剩余的工具调用。用于在代理工作时进行干预。

        Args:
            message: 引导消息（通常是用户消息）
        """
        self._steering_queue.append(message)

    def follow_up(self, message: AgentMessage):
        """
        排队一条跟进消息，在代理完成后处理。

        跟进消息仅在代理没有更多工具调用和引导消息时发送。
        用于在代理停止后继续工作。

        Args:
            message: 跟进消息（通常是用户消息）
        """
        self._follow_up_queue.append(message)

    def clear_steering_queue(self):
        """清空引导消息队列。"""
        self._steering_queue = []

    def clear_follow_up_queue(self):
        """清空跟进消息队列。"""
        self._follow_up_queue = []

    def clear_all_queues(self):
        """清空所有消息队列。"""
        self._steering_queue = []
        self._follow_up_queue = []

    def has_queued_messages(self) -> bool:
        """检查是否有排队的消息。"""
        return len(self._steering_queue) > 0 or len(self._follow_up_queue) > 0

    def _dequeue_steering_messages(self) -> List[AgentMessage]:
        """
        根据模式出队引导消息。

        模式:
        - one-at-a-time: 每次返回一条消息
        - all: 返回所有消息并清空队列
        """
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
        """
        根据模式出队跟进消息。

        模式:
        - one-at-a-time: 每次返回一条消息
        - all: 返回所有消息并清空队列
        """
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
        """清空所有消息历史。"""
        self._state.messages = []

    # ========================================================================
    # 控制方法
    # ========================================================================

    def abort(self):
        """中止当前操作。"""
        if self._abort_event:
            self._abort_event.set()

    async def wait_for_idle(self) -> None:
        """等待代理变为空闲状态。"""
        if self._running_task:
            await self._running_task

    def reset(self):
        """
        重置代理状态。

        清空所有消息、队列和错误状态，
        但保留系统提示、模型和工具配置。
        """
        self._state.messages = []
        self._state.is_streaming = False
        self._state.stream_message = None
        self._state.pending_tool_calls = set()
        self._state.error = None
        self._steering_queue = []
        self._follow_up_queue = []

    # ========================================================================
    # 主要交互方法
    # ========================================================================

    async def prompt(
        self,
        input: Union[str, AgentMessage, List[AgentMessage]],
        images: Optional[List[ImageContent]] = None,
    ) -> None:
        """
        发送提示给代理。

        支持多种输入格式:
        - 字符串: 自动包装为用户消息
        - 单个 AgentMessage: 直接使用
        - AgentMessage 列表: 直接使用

        Args:
            input: 提示内容
            images: 可选的图片列表（仅当 input 为字符串时有效）

        Raises:
            RuntimeError: 如果代理正在处理或未配置模型
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
            # 直接使用消息列表
            msgs = input
        elif isinstance(input, str):
            # 字符串包装为用户消息
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
            # 单个消息对象
            msgs = [input]

        await self._run_loop(msgs)

    async def continue_(self) -> None:
        """
        从当前上下文继续。

        用于错误后的重试或处理排队的消息。
        上下文中的最后一条消息必须是 user 或 toolResult（不能是 assistant）。

        Raises:
            RuntimeError: 如果代理正在处理、无消息可继续、或最后一条是 assistant 消息
        """
        if self._state.is_streaming:
            raise RuntimeError("Agent is already processing. Wait for completion before continuing.")

        messages = self._state.messages
        if not messages:
            raise RuntimeError("No messages to continue from")

        if messages[-1].get("role") == "assistant":
            # 如果最后一条是 assistant 消息，检查是否有排队消息
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

    # ========================================================================
    # 内部方法
    # ========================================================================

    async def _run_loop(
        self,
        messages: Optional[List[AgentMessage]] = None,
        skip_initial_steering_poll: bool = False,
    ) -> None:
        """
        运行代理循环。

        如果提供了 messages，开始新的会话轮次。
        否则，从现有上下文继续。

        Args:
            messages: 可选的新消息
            skip_initial_steering_poll: 是否跳过初始引导消息轮询
        """
        from .agent_loop import agent_loop, agent_loop_continue

        model = self._state.model
        if not model:
            raise RuntimeError("No model configured")

        # 设置中止事件和状态
        self._abort_event = asyncio.Event()
        self._state.is_streaming = True
        self._state.stream_message = None
        self._state.error = None

        # 获取思考级别
        reasoning = None if self._state.thinking_level == ThinkingLevel.OFF else self._state.thinking_level.value

        # 构建上下文
        context = AgentContext(
            system_prompt=self._state.system_prompt,
            messages=self._state.messages.copy(),
            tools=self._state.tools,
        )

        # 构建循环配置
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
            # 启动循环
            if messages:
                stream = agent_loop(messages, context, config, self._abort_event, self._stream_fn)
            else:
                stream = agent_loop_continue(context, config, self._abort_event, self._stream_fn)

            # 处理事件流
            async for event in stream:
                event_type = event["type"]

                # 根据事件类型更新内部状态
                if event_type == "message_start":
                    partial = event["message"]
                    self._state.stream_message = event["message"]

                elif event_type == "message_update":
                    partial = event["message"]
                    self._state.stream_message = event["message"]

                elif event_type == "message_end":
                    partial = None
                    self._state.stream_message = None
                    self.append_message(event["message"])

                elif event_type == "tool_execution_start":
                    self._state.pending_tool_calls.add(event["tool_call_id"])

                elif event_type == "tool_execution_end":
                    self._state.pending_tool_calls.discard(event["tool_call_id"])

                elif event_type == "turn_end":
                    if event["message"].get("role") == "assistant" and event["message"].get("error_message"):
                        self._state.error = event["message"]["error_message"]

                elif event_type == "agent_end":
                    self._state.is_streaming = False
                    self._state.stream_message = None

                # 发送事件给监听器
                self._emit(event)

            # 处理可能残留的部分消息
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
            # 创建错误消息
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
            # 清理状态
            self._state.is_streaming = False
            self._state.stream_message = None
            self._state.pending_tool_calls = set()
            self._abort_event = None

    def _emit(self, event: AgentEvent):
        """发送事件给所有监听器。"""
        for listener in self._listeners:
            listener(event)

