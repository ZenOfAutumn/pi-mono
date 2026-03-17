"""
utils/event_stream.py 模块的单元测试。

测试目标：
1. 验证 EventStream 能够正确地推送和消费事件
2. 验证 AssistantMessageEventStream 能够正确识别完成事件
3. 验证异步迭代器行为
4. 验证 result() 方法能够正确返回最终结果
"""

import asyncio
from src.core_types import (
    AssistantMessage,
    TextContent,
    DoneEvent,
    ErrorEvent,
    StartEvent,
)

import pytest
from src.utils.event_stream import (
    EventStream,
    AssistantMessageEventStream,
    create_assistant_message_event_stream,
)


class TestEventStream:
    """测试 EventStream 基类。"""

    @pytest.mark.asyncio
    async def test_push_and_iterate(self):
        """
        测试推送事件并迭代消费。
        预期结果：按推送顺序接收到所有事件。
        """
        # 创建一个简单的事件流，字符串事件，最终结果也是字符串
        stream = EventStream[str, str](
            is_complete=lambda e: e == "done",
            extract_result=lambda e: e,
        )

        # 推送事件
        stream.push("event1")
        stream.push("event2")
        stream.push("done")

        # 收集事件
        events = []
        async for event in stream:
            events.append(event)

        assert events == ["event1", "event2", "done"]

    @pytest.mark.asyncio
    async def test_result_waits_for_completion(self):
        """
        测试 result() 方法等待完成事件。
        预期结果：result() 返回完成事件的提取结果。
        """
        stream = EventStream[str, str](
            is_complete=lambda e: e.startswith("result:"),
            extract_result=lambda e: e.replace("result:", ""),
        )

        async def push_events():
            await asyncio.sleep(0.01)
            stream.push("event1")
            stream.push("event2")
            stream.push("result:final")

        # 启动推送任务
        asyncio.create_task(push_events())

        # 等待结果
        result = await stream.result()
        assert result == "final"

    @pytest.mark.asyncio
    async def test_end_terminates_stream(self):
        """
        测试 end() 方法终止流。
        预期结果：调用 end() 后，迭代器停止。
        """
        stream = EventStream[str, str](
            is_complete=lambda e: False,
            extract_result=lambda e: e,
        )

        stream.push("event1")
        stream.end("final_result")

        events = []
        async for event in stream:
            events.append(event)

        assert events == ["event1"]
        result = await stream.result()
        assert result == "final_result"

    @pytest.mark.asyncio
    async def test_push_after_done_ignored(self):
        """
        测试在完成后推送事件被忽略。
        预期结果：完成事件后推送的事件不会被添加到队列。
        """
        stream = EventStream[str, str](
            is_complete=lambda e: e == "done",
            extract_result=lambda e: "final",
        )

        stream.push("event1")
        stream.push("done")
        stream.push("event2")  # 应该被忽略

        events = []
        async for event in stream:
            events.append(event)

        assert events == ["event1", "done"]


class TestAssistantMessageEventStream:
    """测试 AssistantMessageEventStream。"""

    @pytest.mark.asyncio
    async def test_done_event_completes_stream(self):
        """
        测试 DoneEvent 完成流。
        预期结果：收到 DoneEvent 后，result() 返回关联的消息。
        """
        stream = AssistantMessageEventStream()

        message = AssistantMessage(
            content=[TextContent(text="Hello!")],
            api="openai-responses",
            provider="openai",
            model="gpt-4",
        )

        stream.push(StartEvent())
        stream.push(DoneEvent(reason="stop", message=message))

        result = await stream.result()
        assert result.content[0].text == "Hello!"
        assert result.stopReason == "stop"

    @pytest.mark.asyncio
    async def test_error_event_completes_stream(self):
        """
        测试 ErrorEvent 完成流。
        预期结果：收到 ErrorEvent 后，result() 返回错误消息。
        """
        stream = AssistantMessageEventStream()

        error_message = AssistantMessage(
            content=[TextContent(text="Partial")],
            stopReason="error",
            errorMessage="Connection failed",
        )

        stream.push(ErrorEvent(reason="error", error=error_message))

        result = await stream.result()
        assert result.stopReason == "error"
        assert result.errorMessage == "Connection failed"

    @pytest.mark.asyncio
    async def test_iterate_multiple_events(self):
        """
        测试迭代多个事件。
        预期结果：按顺序接收到所有事件，包括开始、增量和完成事件。
        """
        stream = AssistantMessageEventStream()

        # 构建消息
        partial = AssistantMessage(content=[])
        final = AssistantMessage(content=[TextContent(text="Hello World")])

        # 推送事件序列
        from src.core_types import TextStartEvent, TextDeltaEvent, TextEndEvent

        stream.push(StartEvent(partial=partial))
        stream.push(TextStartEvent(contentIndex=0, partial=partial))
        stream.push(TextDeltaEvent(contentIndex=0, delta="Hello ", partial=partial))
        stream.push(TextDeltaEvent(contentIndex=0, delta="World", partial=partial))
        stream.push(TextEndEvent(contentIndex=0, content="Hello World", partial=partial))
        stream.push(DoneEvent(reason="stop", message=final))

        # 收集事件
        events = []
        async for event in stream:
            events.append(event)

        assert len(events) == 6
        assert events[0].type == "start"
        assert events[1].type == "text_start"
        assert events[2].type == "text_delta"
        assert events[2].delta == "Hello "
        assert events[-1].type == "done"

    @pytest.mark.asyncio
    async def test_aborted_event(self):
        """
        测试 aborted 事件完成流。
        预期结果：收到 aborted ErrorEvent 后正确返回。
        """
        stream = AssistantMessageEventStream()

        aborted_message = AssistantMessage(
            content=[TextContent(text="Partial response")],
            stopReason="aborted",
        )

        stream.push(ErrorEvent(reason="aborted", error=aborted_message))

        result = await stream.result()
        assert result.stopReason == "aborted"


class TestCreateAssistantMessageEventStream:
    """测试工厂函数。"""

    def test_creates_stream(self):
        """
        测试工厂函数创建 AssistantMessageEventStream。
        预期结果：返回 AssistantMessageEventStream 实例。
        """
        stream = create_assistant_message_event_stream()
        assert isinstance(stream, AssistantMessageEventStream)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

