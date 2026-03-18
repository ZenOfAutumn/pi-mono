"""
Stream 函数工厂模块测试

测试 stream_fn_factory 的功能，包括：
- 从配置创建 stream_fn
- 提供商注册机制
- Friday 提供商的特殊处理
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from src.stream_fn_factory import (
    create_stream_fn_from_config,
    create_stream_fn_with_options,
    register_stream_fn_creator,
    unregister_stream_fn_creator,
    get_registered_providers,
)

# 检查 pi-ai 是否可用
try:
    import pi_ai
    PI_AI_AVAILABLE = True
except ImportError:
    PI_AI_AVAILABLE = False


class TestStreamFnFactory:
    """测试 stream_fn 工厂功能。"""

    @pytest.mark.skipif(not PI_AI_AVAILABLE, reason="pi-ai module not available")
    def test_create_stream_fn_unknown_provider(self):
        """测试未知提供商使用默认实现。"""
        config = {"model": {"provider": "unknown_provider"}}
        stream_fn = create_stream_fn_from_config(config)

        # 未知提供商应该返回默认实现
        assert stream_fn is not None

    @pytest.mark.skipif(not PI_AI_AVAILABLE, reason="pi-ai module not available")
    def test_create_stream_fn_no_provider(self):
        """测试没有提供商配置时使用默认实现。"""
        config = {"model": {}}
        stream_fn = create_stream_fn_from_config(config)

        # 没有提供商应该返回默认实现
        assert stream_fn is not None

    def test_friday_provider_registration(self):
        """测试 Friday 提供商已注册。"""
        providers = get_registered_providers()
        assert "friday" in providers

    def test_register_unregister_stream_fn_creator(self):
        """测试注册和注销 stream_fn 创建函数。"""

        def mock_creator(config):
            return lambda model, context, options: None

        # 注册
        register_stream_fn_creator("test_provider", mock_creator)
        assert "test_provider" in get_registered_providers()

        # 注销
        unregister_stream_fn_creator("test_provider")
        assert "test_provider" not in get_registered_providers()

    @pytest.mark.skipif(not PI_AI_AVAILABLE, reason="pi-ai module not available")
    def test_create_stream_fn_with_llm_config_path(self):
        """测试从配置创建 stream_fn 时包含 llm_config_path。"""
        config = {
            "model": {"provider": "friday"},
            "llm_config_path": "/path/to/config.json"
        }

        # 应该能创建 stream_fn 而不报错
        stream_fn = create_stream_fn_from_config(config)
        assert stream_fn is not None


class TestStreamFnWithOptions:
    """测试带默认选项的 stream_fn 创建。"""

    @pytest.mark.skipif(not PI_AI_AVAILABLE, reason="pi-ai module not available")
    def test_create_stream_fn_with_default_options(self):
        """测试创建带默认选项的 stream_fn。"""
        config = {"model": {"provider": "friday"}}
        default_options = {"temperature": 0.5}

        stream_fn = create_stream_fn_with_options(config, default_options)
        assert stream_fn is not None

    @pytest.mark.skipif(not PI_AI_AVAILABLE, reason="pi-ai module not available")
    def test_create_stream_fn_without_default_options(self):
        """测试创建不带默认选项的 stream_fn。"""
        config = {"model": {"provider": "friday"}}

        stream_fn = create_stream_fn_with_options(config)
        assert stream_fn is not None


class TestIntegrationWithConfigLoader:
    """测试与 config_loader 的集成。"""

    @pytest.mark.skipif(not PI_AI_AVAILABLE, reason="pi-ai module not available")
    def test_create_stream_fn_from_agent_config(self):
        """测试通过 config_loader 创建 stream_fn。"""
        from src.config_loader import create_stream_fn_from_agent_config

        config = {
            "model": {"provider": "friday"},
            "llm_config_path": "/path/to/config.json"
        }

        stream_fn = create_stream_fn_from_agent_config(config)
        assert stream_fn is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

