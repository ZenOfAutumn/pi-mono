"""
stream.py 模块的单元测试。

测试目标：
1. 验证 stream 和 complete 函数能够正确路由到提供商
2. 验证错误处理（未知 API 提供商）
3. 验证 stream_simple 和 complete_simple 函数
"""

import pytest
from src.api_registry import register_api_provider, clear_api_providers, ApiProvider
from src.stream import stream, complete, stream_simple, complete_simple
from src.core_types import Model, Context, AssistantMessage, TextContent, DoneEvent
from src.utils.event_stream import AssistantMessageEventStream


def create_mock_provider(api_name: str):
    """
    创建模拟的 API 提供商。

    Args:
        api_name: API 名称

    Returns:
        模拟的 ApiProvider
    """

    def mock_stream(model, context, options=None) -> AssistantMessageEventStream:
        s = AssistantMessageEventStream()
        # 模拟立即完成
        msg = AssistantMessage(
            content=[TextContent(text=f"Response from {api_name}")],
            api=model.api,
            provider=model.provider,
            model=model.id,
        )
        s.push(DoneEvent(reason="stop", message=msg))
        return s

    def mock_stream_simple(model, context, options=None) -> AssistantMessageEventStream:
        return mock_stream(model, context, options)

    return ApiProvider(
        api=api_name,
        stream=mock_stream,
        streamSimple=mock_stream_simple,
    )


class TestStream:
    """测试 stream 函数。"""

    def setup_method(self):
        """每个测试前清空注册表。"""
        clear_api_providers()

    @pytest.mark.asyncio
    async def test_routes_to_correct_provider(self):
        """
        测试路由到正确的提供商。
        预期结果：使用正确 API 的提供商处理请求。
        """
        register_api_provider(create_mock_provider("test-api"))

        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
        )
        context = Context()

        s = stream(model, context)

        # 收集事件
        events = []
        async for event in s:
            events.append(event)

        assert len(events) == 1
        assert events[0].type == "done"
        assert "test-api" in events[0].message.content[0].text

    def test_raises_for_unknown_api(self):
        """
        测试未知 API 抛出错误。
        预期结果：抛出 ValueError。
        """
        model = Model(
            id="test-model",
            name="Test Model",
            api="unknown-api",
            provider="test-provider",
        )
        context = Context()

        with pytest.raises(ValueError) as exc_info:
            stream(model, context)

        assert "No API provider registered" in str(exc_info.value)


class TestComplete:
    """测试 complete 函数。"""

    def setup_method(self):
        """每个测试前清空注册表。"""
        clear_api_providers()

    @pytest.mark.asyncio
    async def test_returns_assistant_message(self):
        """
        测试返回助手消息。
        预期结果：返回完整的 AssistantMessage。
        """
        register_api_provider(create_mock_provider("test-api"))

        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
        )
        context = Context()

        result = await complete(model, context)

        assert isinstance(result, AssistantMessage)
        assert len(result.content) == 1
        assert result.content[0].type == "text"


class TestStreamSimple:
    """测试 stream_simple 函数。"""

    def setup_method(self):
        """每个测试前清空注册表。"""
        clear_api_providers()

    @pytest.mark.asyncio
    async def test_uses_stream_simple_function(self):
        """
        测试使用 streamSimple 函数。
        预期结果：使用提供商的 streamSimple 函数。
        """
        register_api_provider(create_mock_provider("test-api"))

        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
        )
        context = Context()

        s = stream_simple(model, context)

        events = []
        async for event in s:
            events.append(event)

        assert len(events) == 1
        assert events[0].type == "done"


class TestCompleteSimple:
    """测试 complete_simple 函数。"""

    def setup_method(self):
        """每个测试前清空注册表。"""
        clear_api_providers()

    @pytest.mark.asyncio
    async def test_returns_assistant_message(self):
        """
        测试返回助手消息。
        预期结果：返回完整的 AssistantMessage。
        """
        register_api_provider(create_mock_provider("test-api"))

        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
        )
        context = Context()

        result = await complete_simple(model, context)

        assert isinstance(result, AssistantMessage)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

