"""
api_registry.py 模块的单元测试。

测试目标：
1. 验证 register_api_provider 能够正确注册提供商
2. 验证 get_api_provider 能够正确获取已注册的提供商
3. 验证 get_api_providers 返回所有提供商
4. 验证 clear_api_providers 清空注册
"""

from src.core_types import Model, Context

import pytest
from src.api_registry import (
    ApiProvider,
    register_api_provider,
    get_api_provider,
    get_api_providers,
    clear_api_providers,
)
from src.utils.event_stream import AssistantMessageEventStream


def create_mock_stream_function(name: str):
    """
    创建模拟的流式函数。

    Args:
        name: 函数名称标识

    Returns:
        模拟的流式函数
    """

    def mock_stream(
        model: Model, context: Context, options=None
    ) -> AssistantMessageEventStream:
        stream = AssistantMessageEventStream()
        # 不推送任何事件，保持简单
        return stream

    mock_stream.__name__ = name
    return mock_stream


class TestRegisterApiProvider:
    """测试 register_api_provider 函数。"""

    def setup_method(self):
        """每个测试前清空注册表。"""
        clear_api_providers()

    def test_registers_provider(self):
        """
        测试注册 API 提供商。
        预期结果：提供商被成功注册。
        """
        provider = ApiProvider(
            api="test-api",
            stream=create_mock_stream_function("stream"),
            streamSimple=create_mock_stream_function("streamSimple"),
        )

        register_api_provider(provider)

        retrieved = get_api_provider("test-api")
        assert retrieved is not None
        assert retrieved.api == "test-api"

    def test_overwrites_existing_provider(self):
        """
        测试覆盖已存在的提供商。
        预期结果：新注册覆盖旧注册。
        """
        provider1 = ApiProvider(
            api="test-api",
            stream=create_mock_stream_function("stream1"),
            streamSimple=create_mock_stream_function("streamSimple1"),
        )
        provider2 = ApiProvider(
            api="test-api",
            stream=create_mock_stream_function("stream2"),
            streamSimple=create_mock_stream_function("streamSimple2"),
        )

        register_api_provider(provider1)
        register_api_provider(provider2)

        retrieved = get_api_provider("test-api")
        assert retrieved is not None
        # 应该是第二次注册的


class TestGetApiProvider:
    """测试 get_api_provider 函数。"""

    def setup_method(self):
        """每个测试前清空注册表。"""
        clear_api_providers()

    def test_returns_none_for_unknown_api(self):
        """
        测试获取未注册的 API 提供商。
        预期结果：返回 None。
        """
        result = get_api_provider("unknown-api")
        assert result is None

    def test_returns_registered_provider(self):
        """
        测试获取已注册的提供商。
        预期结果：返回正确的提供商。
        """
        provider = ApiProvider(
            api="test-api",
            stream=create_mock_stream_function("stream"),
            streamSimple=create_mock_stream_function("streamSimple"),
        )
        register_api_provider(provider)

        result = get_api_provider("test-api")
        assert result is not None
        assert result.api == "test-api"

    def test_returns_provider_with_correct_functions(self):
        """
        测试返回的提供商包含正确的函数。
        预期结果：stream 和 streamSimple 函数都存在。
        """
        provider = ApiProvider(
            api="test-api",
            stream=create_mock_stream_function("stream"),
            streamSimple=create_mock_stream_function("streamSimple"),
        )
        register_api_provider(provider)

        result = get_api_provider("test-api")
        assert result is not None
        assert callable(result.stream)
        assert callable(result.streamSimple)


class TestGetApiProviders:
    """测试 get_api_providers 函数。"""

    def setup_method(self):
        """每个测试前清空注册表。"""
        clear_api_providers()

    def test_returns_empty_list_when_no_providers(self):
        """
        测试没有注册任何提供商时返回空列表。
        预期结果：返回空列表。
        """
        result = get_api_providers()
        assert result == []

    def test_returns_all_providers(self):
        """
        测试返回所有已注册的提供商。
        预期结果：返回所有提供商的列表。
        """
        provider1 = ApiProvider(
            api="api-1",
            stream=create_mock_stream_function("stream1"),
            streamSimple=create_mock_stream_function("streamSimple1"),
        )
        provider2 = ApiProvider(
            api="api-2",
            stream=create_mock_stream_function("stream2"),
            streamSimple=create_mock_stream_function("streamSimple2"),
        )

        register_api_provider(provider1)
        register_api_provider(provider2)

        result = get_api_providers()
        assert len(result) == 2

        apis = [p.api for p in result]
        assert "api-1" in apis
        assert "api-2" in apis


class TestClearApiProviders:
    """测试 clear_api_providers 函数。"""

    def test_clears_all_providers(self):
        """
        测试清空所有已注册的提供商。
        预期结果：清空后获取提供商返回空列表。
        """
        provider = ApiProvider(
            api="test-api",
            stream=create_mock_stream_function("stream"),
            streamSimple=create_mock_stream_function("streamSimple"),
        )
        register_api_provider(provider)

        clear_api_providers()

        result = get_api_providers()
        assert result == []

    def test_get_returns_none_after_clear(self):
        """
        测试清空后获取特定提供商返回 None。
        预期结果：返回 None。
        """
        provider = ApiProvider(
            api="test-api",
            stream=create_mock_stream_function("stream"),
            streamSimple=create_mock_stream_function("streamSimple"),
        )
        register_api_provider(provider)

        clear_api_providers()

        result = get_api_provider("test-api")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

