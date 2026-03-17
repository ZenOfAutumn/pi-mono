"""
Friday Responses API 单元测试。

测试 Friday Responses API 提供商的实现，
包括认证配置、消息转换和流式处理。
"""

import os
from unittest.mock import AsyncMock, patch

import pytest
from src.providers.friday_config import (
    FRIDAY_RESPONSES_API_URL,
    DEFAULT_FRIDAY_MODEL,
    FridayAuthConfig,
    FridayResponsesOptions,
    build_friday_request_params,
)
from src.providers.friday_responses import (
    convert_messages_to_friday,
    convert_tools_to_friday,
    _split_tool_call_id,
    _map_stop_reason,
)
from src.core_types import (
    Context,
    Model,
    Tool,
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    TextContent,
    ImageContent,
    ToolCall,
)


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def basic_model() -> Model:
    """创建基础测试模型。"""
    return Model(
        id="gpt-4o-mini",
        name="GPT-4o Mini",
        api="friday-responses",
        provider="friday",
    )


@pytest.fixture
def basic_context() -> Context:
    """创建基础测试上下文。"""
    return Context(
        systemPrompt="你是一个有帮助的助手。",
        messages=[
            UserMessage(content="你好，请介绍一下自己。", timestamp=1000),
        ],
    )


@pytest.fixture
def tool_context() -> Context:
    """创建包含工具调用的测试上下文。"""
    return Context(
        systemPrompt="你是一个有帮助的助手。",
        messages=[
            UserMessage(content="北京今天天气怎么样？", timestamp=1000),
            AssistantMessage(
                content=[
                    ToolCall(
                        type="toolCall",
                        id="call_123|fc_456",
                        name="get_weather",
                        arguments={"city": "北京"},
                    )
                ],
                api="friday-responses",
                provider="friday",
                model="gpt-4o-mini",
                stopReason="toolUse",
                timestamp=2000,
            ),
            ToolResultMessage(
                toolCallId="call_123|fc_456",
                toolName="get_weather",
                content=[TextContent(text="北京今天晴，25°C")],
                timestamp=3000,
            ),
        ],
        tools=[
            Tool(
                name="get_weather",
                description="获取指定城市的天气信息",
                parameters={
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "城市名称"},
                    },
                    "required": ["city"],
                },
            )
        ],
    )


@pytest.fixture
def auth_config() -> FridayAuthConfig:
    """创建测试认证配置。"""
    return FridayAuthConfig(
        billing_id="test_billing_id",
        agent_id="test_agent_id",
        user_id="test_user_id",
    )


# ============================================================================
# 认证配置测试
# ============================================================================

class TestFridayAuthConfig:
    """FridayAuthConfig 测试类。"""

    def test_create_with_billing_id_only(self):
        """测试仅使用 billing_id 创建配置。"""
        config = FridayAuthConfig(billing_id="test_billing_id")

        assert config.billing_id == "test_billing_id"
        assert config.agent_id is None
        assert config.context_token is None
        assert config.user_id is None
        assert config.auth_level == "basic"

    def test_create_with_agent_id(self):
        """测试使用 agent_id 创建配置。"""
        config = FridayAuthConfig(
            billing_id="test_billing_id",
            agent_id="test_agent_id",
        )

        assert config.auth_level == "identity"

    def test_create_with_full_auth(self):
        """测试使用完整认证创建配置。"""
        config = FridayAuthConfig(
            billing_id="test_billing_id",
            agent_id="test_agent_id",
            context_token="test_token",
            user_id="test_user_id",
        )

        assert config.auth_level == "user_identity"

    def test_to_headers_basic(self):
        """测试基础鉴权的请求头生成。"""
        config = FridayAuthConfig(billing_id="test_billing_id")
        headers = config.to_headers()

        assert headers["Authorization"] == "Bearer test_billing_id"
        assert headers["Content-Type"] == "application/json;charset=UTF-8"
        assert "Mt-Agent-Id" not in headers

    def test_to_headers_with_agent_id(self):
        """测试身份鉴权的请求头生成。"""
        config = FridayAuthConfig(
            billing_id="test_billing_id",
            agent_id="test_agent_id",
        )
        headers = config.to_headers()

        assert headers["Authorization"] == "Bearer test_billing_id"
        assert headers["Mt-Agent-Id"] == "test_agent_id"

    def test_to_headers_full(self):
        """测试完整认证的请求头生成。"""
        config = FridayAuthConfig(
            billing_id="test_billing_id",
            agent_id="test_agent_id",
            context_token="test_token",
            user_id="test_user_id",
        )
        headers = config.to_headers()

        assert headers["Authorization"] == "Bearer test_billing_id"
        assert headers["Mt-Agent-Id"] == "test_agent_id"
        assert headers["Mt-Context-Token"] == "test_token"
        assert headers["Mt-User-Id"] == "test_user_id"

    def test_from_env(self, monkeypatch):
        """测试从环境变量创建配置。"""
        monkeypatch.setenv("FRIDAY_BILLING_ID", "env_billing_id")
        monkeypatch.setenv("FRIDAY_AGENT_ID", "env_agent_id")

        config = FridayAuthConfig.from_env()

        assert config is not None
        assert config.billing_id == "env_billing_id"
        assert config.agent_id == "env_agent_id"

    def test_from_env_missing_billing_id(self, monkeypatch):
        """测试环境变量缺失 billing_id 时返回 None。"""
        monkeypatch.delenv("FRIDAY_BILLING_ID", raising=False)

        config = FridayAuthConfig.from_env()

        assert config is None


# ============================================================================
# 请求参数构建测试
# ============================================================================

class TestBuildFridayRequestParams:
    """build_friday_request_params 测试类。"""

    def test_basic_params(self):
        """测试基本参数构建。"""
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages=[{"role": "user", "content": "你好"}],
        )

        assert params["model"] == "gpt-4o-mini"
        assert params["input"] == [{"role": "user", "content": "你好"}]
        assert params["stream"] is True

    def test_params_with_options(self):
        """测试带选项的参数构建。"""
        options: FridayResponsesOptions = {
            "maxTokens": 1000,
            "temperature": 0.7,
            "topP": 0.9,
        }
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages=[],
            options=options,
        )

        assert params["max_output_tokens"] == 1000
        assert params["temperature"] == 0.7
        assert params["top_p"] == 0.9

    def test_params_with_reasoning(self):
        """测试带思考配置的参数构建。"""
        options: FridayResponsesOptions = {
            "reasoning": "high",
            "thinkTokens": 8000,
        }
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages=[],
            options=options,
        )

        assert "think" in params
        assert params["think"]["enabled"] is True
        assert params["think"]["thinkTokens"] == 8000

    def test_params_with_tools(self):
        """测试带工具的参数构建。"""
        tools = [
            {
                "type": "function",
                "name": "get_weather",
                "description": "获取天气",
                "parameters": {"type": "object"},
            }
        ]
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages=[],
            tools=tools,
        )

        assert "tools" in params
        assert len(params["tools"]) == 1
        assert params["tools"][0]["name"] == "get_weather"

    def test_params_with_previous_response_id(self):
        """测试带上下文 ID 的参数构建。"""
        options: FridayResponsesOptions = {
            "previousResponseId": "resp_123",
        }
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages=[],
            options=options,
        )

        assert params["previous_response_id"] == "resp_123"


# ============================================================================
# 消息转换测试
# ============================================================================

class TestConvertMessagesToFriday:
    """convert_messages_to_friday 测试类。"""

    def test_convert_user_message_string(self, basic_model, basic_context):
        """测试字符串类型的用户消息转换。"""
        messages = convert_messages_to_friday(basic_context, basic_model)

        # 应包含系统提示和用户消息
        assert len(messages) >= 2
        # 系统提示
        assert messages[0]["role"] == "developer"
        # 用户消息
        assert messages[1]["role"] == "user"

    def test_convert_user_message_multimodal(self, basic_model):
        """测试多模态用户消息转换。"""
        context = Context(
            messages=[
                UserMessage(
                    content=[
                        TextContent(text="这张图片是什么？"),
                        ImageContent(data="base64data", mimeType="image/png"),
                    ],
                    timestamp=1000,
                ),
            ],
        )
        messages = convert_messages_to_friday(context, basic_model)

        user_msg = messages[0]
        assert user_msg["role"] == "user"
        assert len(user_msg["content"]) == 2
        assert user_msg["content"][0]["type"] == "input_text"
        assert user_msg["content"][1]["type"] == "input_image"

    def test_convert_tool_call(self, basic_model, tool_context):
        """测试工具调用消息转换。"""
        messages = convert_messages_to_friday(tool_context, basic_model)

        # 查找 function_call 类型的消息
        function_calls = [m for m in messages if m.get("type") == "function_call"]
        assert len(function_calls) == 1
        assert function_calls[0]["name"] == "get_weather"

    def test_convert_tool_result(self, basic_model, tool_context):
        """测试工具结果消息转换。"""
        messages = convert_messages_to_friday(tool_context, basic_model)

        # 查找 function_call_output 类型的消息
        outputs = [m for m in messages if m.get("type") == "function_call_output"]
        assert len(outputs) == 1
        assert "北京" in outputs[0]["output"]


class TestConvertToolsToFriday:
    """convert_tools_to_friday 测试类。"""

    def test_convert_single_tool(self):
        """测试单个工具转换。"""
        tools = [
            Tool(
                name="get_weather",
                description="获取天气信息",
                parameters={
                    "type": "object",
                    "properties": {
                        "city": {"type": "string", "description": "城市名称"},
                    },
                    "required": ["city"],
                },
            )
        ]
        friday_tools = convert_tools_to_friday(tools)

        assert len(friday_tools) == 1
        assert friday_tools[0]["type"] == "function"
        assert friday_tools[0]["name"] == "get_weather"
        assert friday_tools[0]["description"] == "获取天气信息"

    def test_convert_multiple_tools(self):
        """测试多个工具转换。"""
        tools = [
            Tool(name="tool1", description="工具1", parameters={"type": "object"}),
            Tool(name="tool2", description="工具2", parameters={"type": "object"}),
        ]
        friday_tools = convert_tools_to_friday(tools)

        assert len(friday_tools) == 2


# ============================================================================
# 工具函数测试
# ============================================================================

class TestSplitToolCallId:
    """_split_tool_call_id 测试类。"""

    def test_split_with_separator(self):
        """测试带分隔符的 ID 分割。"""
        call_id, item_id = _split_tool_call_id("call_123|fc_456")

        assert call_id == "call_123"
        assert item_id == "fc_456"

    def test_split_without_separator(self):
        """测试不带分隔符的 ID。"""
        call_id, item_id = _split_tool_call_id("call_123")

        assert call_id == "call_123"
        assert item_id is None


class TestMapStopReason:
    """_map_stop_reason 测试类。"""

    def test_completed(self):
        """测试 completed 状态映射。"""
        assert _map_stop_reason("completed") == "stop"

    def test_incomplete(self):
        """测试 incomplete 状态映射。"""
        assert _map_stop_reason("incomplete") == "length"

    def test_failed(self):
        """测试 failed 状态映射。"""
        assert _map_stop_reason("failed") == "error"

    def test_cancelled(self):
        """测试 cancelled 状态映射。"""
        assert _map_stop_reason("cancelled") == "error"

    def test_unknown(self):
        """测试未知状态映射。"""
        assert _map_stop_reason("unknown") == "stop"


# ============================================================================
# 常量测试
# ============================================================================

class TestConstants:
    """常量测试类。"""

    def test_api_url(self):
        """测试 API URL 常量。"""
        assert FRIDAY_RESPONSES_API_URL == "https://aigc.sankuai.com/v1/responses"

    def test_default_model(self):
        """测试默认模型常量。"""
        assert DEFAULT_FRIDAY_MODEL == "gpt-4o-mini"


# ============================================================================
# 配置管理器测试
# ============================================================================

class TestFridayConfigManager:
    """FridayConfigManager 测试类。"""

    def test_config_manager_create_temp(self, tmp_path, monkeypatch):
        """测试配置管理器使用临时目录。"""
        from src.providers.friday_config import FridayConfigManager, set_config_path

        config_file = tmp_path / "config.json"
        manager = FridayConfigManager(config_file)

        # 设置配置
        manager.set_billing_id("test_billing")
        assert manager.get_billing_id() == "test_billing"

        # 验证文件已创建
        assert config_file.exists()

    def test_config_manager_get_set(self, tmp_path):
        """测试配置的读取和设置。"""
        from src.providers.friday_config import FridayConfigManager

        config_file = tmp_path / "config.json"
        manager = FridayConfigManager(config_file)

        # 设置各项配置
        manager.set_billing_id("billing_123")
        manager.set_agent_id("agent_456")
        manager.set_user_id("user_789")

        # 验证读取
        assert manager.get_billing_id() == "billing_123"
        assert manager.get_agent_id() == "agent_456"
        assert manager.get_user_id() == "user_789"

    def test_config_manager_delete(self, tmp_path):
        """测试配置删除。"""
        from src.providers.friday_config import FridayConfigManager

        config_file = tmp_path / "config.json"
        manager = FridayConfigManager(config_file)

        manager.set_billing_id("to_delete")
        assert manager.get_billing_id() == "to_delete"

        # 删除
        result = manager.delete("billing_id")
        assert result is True
        assert manager.get_billing_id() is None

    def test_config_manager_clear(self, tmp_path):
        """测试清空配置。"""
        from src.providers.friday_config import FridayConfigManager

        config_file = tmp_path / "config.json"
        manager = FridayConfigManager(config_file)

        manager.set_billing_id("billing")
        manager.set_agent_id("agent")

        manager.clear()

        assert manager.get_billing_id() is None
        assert manager.get_agent_id() is None

    def test_auth_config_from_config_file(self, tmp_path):
        """测试从配置文件创建认证配置。"""
        from src.providers.friday_config import FridayConfigManager, FridayAuthConfig

        config_file = tmp_path / "config.json"
        manager = FridayConfigManager(config_file)
        manager.set_billing_id("config_billing")
        manager.set_agent_id("config_agent")

        auth = FridayAuthConfig.from_config(manager)
        assert auth is not None
        assert auth.billing_id == "config_billing"
        assert auth.agent_id == "config_agent"

    def test_config_fallback_to_env(self, tmp_path, monkeypatch):
        """测试配置文件缺失时回退到环境变量。"""
        from src.providers.friday_config import FridayConfigManager

        # 设置环境变量
        monkeypatch.setenv("FRIDAY_BILLING_ID", "env_billing")

        # 使用空配置文件
        config_file = tmp_path / "empty_config.json"
        manager = FridayConfigManager(config_file)

        # 应从环境变量读取
        assert manager.get_billing_id() == "env_billing"


# ============================================================================
# 集成测试（Mock）
# ============================================================================

class TestStreamFridayResponses:
    """stream_friday_responses 集成测试类。"""

    @pytest.mark.asyncio
    async def test_stream_without_auth_returns_error_event(self, basic_model, basic_context):
        """测试无认证时返回错误事件。"""
        from src.providers.friday_responses import stream_friday_responses

        # 清除环境变量
        with patch.dict(os.environ, {}, clear=True):
            stream = stream_friday_responses(basic_model, basic_context)
            # 由于错误发生在异步任务中，需要等待
            import asyncio
            await asyncio.sleep(0.1)

            # 验证 stream 已结束
            assert stream._done is True

    @pytest.mark.asyncio
    async def test_stream_with_mock_response(self, basic_model, basic_context, auth_config):
        """测试带 Mock 响应的流式调用。"""
        from src.providers.friday_responses import stream_friday_responses
        from src.utils.event_stream import AssistantMessageEventStream

        # Mock aiohttp 响应
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_response.content = self._create_mock_stream()

        mock_session = AsyncMock()
        mock_session.post.return_value.__aenter__.return_value = mock_response

        with patch("aiohttp.ClientSession", return_value=mock_session):
            with patch.dict(os.environ, {
                "FRIDAY_BILLING_ID": auth_config.billing_id,
                "FRIDAY_AGENT_ID": auth_config.agent_id or "",
            }):
                stream = stream_friday_responses(basic_model, basic_context)

                assert isinstance(stream, AssistantMessageEventStream)

    def _create_mock_stream(self):
        """创建 Mock 流式响应数据。"""
        events = [
            b'data: {"type": "response.created", "response": {}}\n',
            b'data: {"type": "response.output_item.added", "item": {"type": "message"}}\n',
            'data: {"type": "response.output_text.delta", "delta": "Hello"}\n'.encode('utf-8'),
            'data: {"type": "response.output_item.done", "item": {"type": "message", "content": [{"type": "output_text", "text": "Hello"}]}}\n'.encode('utf-8'),
            b'data: {"type": "response.completed", "response": {"status": "completed", "usage": {"input_tokens": 10, "output_tokens": 5, "total_tokens": 15}}}\n',
            b'data: [DONE]\n',
        ]

        async def async_generator():
            for event in events:
                yield event

        return async_generator()


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

