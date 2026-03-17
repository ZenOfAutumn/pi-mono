"""
异步迭代事件流实现。

本模块提供支持异步迭代和结果等待的通用事件流类，
用于流式 LLM 响应。
"""

from __future__ import annotations

import asyncio
from typing import AsyncIterator, Callable, Generic, Optional, TypeVar

T = TypeVar("T")  # 事件类型
R = TypeVar("R")  # 结果类型


class EventStream(Generic[T, R], AsyncIterator[T]):
    """
    用于异步迭代的通用事件流类。

    此类提供基于队列的事件流，可以异步迭代。
    支持推送事件、结束流和等待最终结果。

    类型参数:
        T: 流产生的事件类型
        R: 最终结果的类型
    """

    def __init__(
        self,
        is_complete: Callable[[T], bool],
        extract_result: Callable[[T], R],
    ):
        """
        初始化事件流。

        Args:
            is_complete: 检查事件是否为完成事件的函数
            extract_result: 从完成事件提取结果的函数
        """
        self._queue: asyncio.Queue[Optional[T]] = asyncio.Queue()
        self._done = False                          # 流是否已结束
        self._final_result: Optional[R] = None      # 最终结果缓存
        self._result_future: asyncio.Future[R] = asyncio.get_event_loop().create_future()
        self._is_complete = is_complete
        self._extract_result = extract_result

    def push(self, event: T) -> None:
        """
        推送事件到流。

        如果事件是完成事件，流将被标记为结束并解析结果。

        Args:
            event: 要推送的事件
        """
        if self._done:
            return

        if self._is_complete(event):
            self._done = True
            result = self._extract_result(event)
            self._final_result = result
            if not self._result_future.done():
                self._result_future.set_result(result)

        self._queue.put_nowait(event)

    def end(self, result: Optional[R] = None) -> None:
        """
        结束流。

        标记流为结束，如果提供了结果则解析结果 future。

        Args:
            result: 可选的结果
        """
        self._done = True
        if result is not None and not self._result_future.done():
            self._result_future.set_result(result)
        # 发送迭代结束信号
        self._queue.put_nowait(None)

    def __aiter__(self) -> AsyncIterator[T]:
        """返回 self 作为异步迭代器。"""
        return self

    async def __anext__(self) -> T:
        """
        从流获取下一个事件。

        Returns:
            下一个事件

        Raises:
            StopAsyncIteration: 当流结束时
        """
        if self._done and self._queue.empty():
            raise StopAsyncIteration

        event = await self._queue.get()

        if event is None:
            raise StopAsyncIteration

        return event

    async def result(self) -> R:
        """
        等待并返回最终结果。

        Returns:
            流的最终结果
        """
        return await self._result_future


class AssistantMessageEventStream(EventStream["AssistantMessageEvent", "AssistantMessage"]):
    """
    助手消息事件流。

    这是专门处理 AssistantMessageEvent 事件并返回 AssistantMessage
    作为最终结果的事件流特化版本。
    """

    def __init__(self) -> None:
        """初始化助手消息事件流。"""
        from ..core_types import AssistantMessage, AssistantMessageEvent

        def is_complete(event: AssistantMessageEvent) -> bool:
            """检查是否为完成事件（done 或 error）。"""
            return event.type in ("done", "error")

        def extract_result(event: AssistantMessageEvent) -> AssistantMessage:
            """从完成事件提取助手消息。"""
            if event.type == "done":
                return event.message
            elif event.type == "error":
                return event.error
            raise ValueError(f"Unexpected event type for final result: {event.type}")

        super().__init__(is_complete, extract_result)


# 类型提示的前向引用
AssistantMessageEvent = "AssistantMessageEvent"


def create_assistant_message_event_stream() -> AssistantMessageEventStream:
    """
    AssistantMessageEventStream 的工厂函数。

    Returns:
        新的 AssistantMessageEventStream 实例
    """
    return AssistantMessageEventStream()

