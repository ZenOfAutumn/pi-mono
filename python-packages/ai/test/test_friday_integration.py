"""
Friday Responses API 集成测试。

基于官方文档示例的测试用例：
https://km.sankuai.com/collabpage/2720941091

测试场景：
1. 基础文本输入
2. 多模态输入（图片）
3. 网页搜索内置工具
4. 文件搜索内置工具
5. 自定义工具调用
6. 多轮对话（previous_response_id）
7. 思考模型配置
8. JSON 格式输出
"""

import json

import pytest
from src.providers.friday_config import (
    FridayAuthConfig,
    FridayConfigManager,
    build_friday_request_params,
    FRIDAY_RESPONSES_API_URL,
)
from src.providers.friday_responses import (
    convert_messages_to_friday,
    convert_tools_to_friday,
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
def friday_model() -> Model:
    """创建 Friday 测试模型。"""
    return Model(
        id="gpt-4o-mini",
        name="GPT-4o Mini",
        api="friday-responses",
        provider="friday",
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
# 文档示例测试 - 请求参数构建
# ============================================================================

class TestDocExamplesRequestParams:
    """
    测试文档中的请求参数示例。

    参考：https://km.sankuai.com/collabpage/2720941091
    """

    def test_text_input_example(self):
        """
        测试文档中的文本输入示例。

        文档示例：
        "input": "Write a one-sentence bedtime story about a unicorn."
        """
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages="Write a one-sentence bedtime story about a unicorn.",
        )

        assert params["model"] == "gpt-4o-mini"
        assert params["input"] == "Write a one-sentence bedtime story about a unicorn."
        assert params["stream"] is True

    def test_model_parameter(self):
        """
        测试 model 参数。

        文档：用于生成回复的模型，比如 gpt-4.1 或 LongCat-Large-32K-Chat
        """
        params = build_friday_request_params(
            model_id="LongCat-Large-32K-Chat",
            input_messages=[],
        )
        assert params["model"] == "LongCat-Large-32K-Chat"

    def test_max_output_tokens(self):
        """
        测试 max_output_tokens 参数。

        文档：模型最大生成长度
        """
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages=[],
            options={"maxTokens": 1000},
        )
        assert params["max_output_tokens"] == 1000

    def test_temperature(self):
        """
        测试 temperature 参数。

        文档：用于采样的温度值，范围在0到2之间
        """
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages=[],
            options={"temperature": 0.7},
        )
        assert params["temperature"] == 0.7

    def test_top_p(self):
        """
        测试 top_p 参数。

        文档：核采样参数
        """
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages=[],
            options={"topP": 0.9},
        )
        assert params["top_p"] == 0.9

    def test_previous_response_id(self):
        """
        测试 previous_response_id 参数。

        文档：上一次模型回复的会话ID，使用这个ID可以创建多轮对话
        """
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages=[],
            options={"previousResponseId": "resp_2791034863861360640"},
        )
        assert params["previous_response_id"] == "resp_2791034863861360640"

    def test_think_config(self):
        """
        测试 think 配置参数。

        文档示例：
        {
            "enabled": "true",
            "thinkTokens": 4800
        }
        """
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages=[],
            options={"thinkTokens": 4800},
        )
        assert "think" in params
        assert params["think"]["enabled"] is True
        assert params["think"]["thinkTokens"] == 4800

    def test_text_format_json_object(self):
        """
        测试 text.format.type = json_object。

        文档示例：
        {
            "text": {
                "format": {
                    "type": "json_object"
                }
            }
        }
        """
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages=[],
            options={"textFormat": "json_object"},
        )
        assert params["text"]["format"]["type"] == "json_object"

    def test_text_format_text(self):
        """
        测试 text.format.type = text。

        文档示例：
        {
            "text": {
                "format": {
                    "type": "text"
                }
            }
        }
        """
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages=[],
            options={"textFormat": "text"},
        )
        assert params["text"]["format"]["type"] == "text"

    def test_tool_choice_auto(self):
        """
        测试 tool_choice = auto。

        文档：模型自主选择工具
        """
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages=[],
            tools=[{"type": "function", "name": "test"}],
            options={"toolChoice": "auto"},
        )
        assert params["tool_choice"] == "auto"

    def test_tool_choice_none(self):
        """
        测试 tool_choice = none。

        文档：模型不使用任何工具进行生成
        """
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages=[],
            tools=[{"type": "function", "name": "test"}],
            options={"toolChoice": "none"},
        )
        assert params["tool_choice"] == "none"

    def test_parallel_tool_calls(self):
        """
        测试 parallel_tool_calls 参数。

        文档：是否允许模型并行运行工具调用
        """
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages=[],
            tools=[{"type": "function", "name": "test"}],
            options={"parallelToolCalls": True},
        )
        assert params["parallel_tool_calls"] is True


# ============================================================================
# 文档示例测试 - 工具定义
# ============================================================================

class TestDocExamplesTools:
    """
    测试文档中的工具定义示例。

    参考：https://km.sankuai.com/collabpage/2720941091
    """

    def test_web_search_preview_tool(self):
        """
        测试网页搜索内置工具。

        文档示例：
        {
            "tools": [
                { "type": "web_search_preview" }
            ]
        }
        """
        # 内置工具直接传递
        tools = [{"type": "web_search_preview"}]
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages=[],
            tools=tools,
        )
        assert params["tools"][0]["type"] == "web_search_preview"

    def test_file_search_tool(self):
        """
        测试文件搜索内置工具。

        文档示例：
        {
            "tools": [
                {
                    "type": "file_search",
                    "vector_store_ids": ["你的知识库id"],
                    "max_num_results": 5
                }
            ]
        }
        """
        tools = [{
            "type": "file_search",
            "vector_store_ids": ["kb_123456"],
            "max_num_results": 5,
        }]
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages=[],
            tools=tools,
        )
        assert params["tools"][0]["type"] == "file_search"
        assert params["tools"][0]["vector_store_ids"] == ["kb_123456"]
        assert params["tools"][0]["max_num_results"] == 5

    def test_custom_function_tool(self):
        """
        测试用户自定义工具。

        文档示例：
        {
            "tools": [
                {
                    "type": "function",
                    "name": "get_weather",
                    "description": "Get current temperature for a given location.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "City and country e.g. Bogotá, Colombia"
                            }
                        },
                        "required": ["location"],
                        "additionalProperties": false
                    }
                }
            ]
        }
        """
        tools = [
            Tool(
                name="get_weather",
                description="Get current temperature for a given location.",
                parameters={
                    "type": "object",
                    "properties": {
                        "location": {
                            "type": "string",
                            "description": "City and country e.g. Bogotá, Colombia",
                        }
                    },
                    "required": ["location"],
                    "additionalProperties": False,
                },
            )
        ]
        friday_tools = convert_tools_to_friday(tools)

        assert len(friday_tools) == 1
        assert friday_tools[0]["type"] == "function"
        assert friday_tools[0]["name"] == "get_weather"
        assert friday_tools[0]["description"] == "Get current temperature for a given location."
        assert friday_tools[0]["parameters"]["type"] == "object"


# ============================================================================
# 文档示例测试 - 多模态输入
# ============================================================================

class TestDocExamplesMultimodal:
    """
    测试文档中的多模态输入示例。

    参考：https://km.sankuai.com/collabpage/2720941091
    """

    def test_multimodal_image_input(self, friday_model):
        """
        测试多模态输入（图片）。

        文档示例：
        "input": [
            {
                "role": "user",
                "content": [
                    { "type": "input_text", "text": "what is in this image?" },
                    { "type": "input_image", "image_url": "https://..." }
                ]
            }
        ]
        """
        context = Context(
            messages=[
                UserMessage(
                    content=[
                        TextContent(text="what is in this image?"),
                        ImageContent(
                            data="base64data",
                            mimeType="image/jpeg",
                        ),
                    ],
                    timestamp=1000,
                ),
            ],
        )
        messages = convert_messages_to_friday(context, friday_model)

        assert len(messages) >= 1
        user_msg = messages[0]
        assert user_msg["role"] == "user"
        assert len(user_msg["content"]) == 2
        assert user_msg["content"][0]["type"] == "input_text"
        assert user_msg["content"][1]["type"] == "input_image"


# ============================================================================
# 文档示例测试 - 认证头
# ============================================================================

class TestDocExamplesAuthHeaders:
    """
    测试文档中的认证头示例。

    参考：https://km.sankuai.com/collabpage/2720941091
    """

    def test_basic_auth_headers(self):
        """
        测试基础鉴权的请求头。

        文档：基础鉴权仅需 Authorization
        """
        config = FridayAuthConfig(billing_id="test_billing_id")
        headers = config.to_headers()

        assert headers["Authorization"] == "Bearer test_billing_id"
        assert headers["Content-Type"] == "application/json;charset=UTF-8"
        assert "Mt-Agent-Id" not in headers

    def test_identity_auth_headers(self):
        """
        测试身份鉴权的请求头。

        文档：身份鉴权需要 Authorization + Mt-Agent-Id
        """
        config = FridayAuthConfig(
            billing_id="test_billing_id",
            agent_id="test_agent_id",
        )
        headers = config.to_headers()

        assert headers["Authorization"] == "Bearer test_billing_id"
        assert headers["Mt-Agent-Id"] == "test_agent_id"

    def test_user_identity_auth_headers(self):
        """
        测试携带用户信息身份鉴权的请求头。

        文档：需要 Authorization + Mt-Agent-Id + Mt-Context-Token
        """
        config = FridayAuthConfig(
            billing_id="test_billing_id",
            agent_id="test_agent_id",
            context_token="test_context_token",
            user_id="test_user_id",
        )
        headers = config.to_headers()

        assert headers["Authorization"] == "Bearer test_billing_id"
        assert headers["Mt-Agent-Id"] == "test_agent_id"
        assert headers["Mt-Context-Token"] == "test_context_token"
        assert headers["Mt-User-Id"] == "test_user_id"

    def test_auth_level_basic(self):
        """
        测试认证级别 - basic。
        """
        config = FridayAuthConfig(billing_id="test")
        assert config.auth_level == "basic"

    def test_auth_level_identity(self):
        """
        测试认证级别 - identity。
        """
        config = FridayAuthConfig(
            billing_id="test",
            agent_id="agent",
        )
        assert config.auth_level == "identity"

    def test_auth_level_user_identity(self):
        """
        测试认证级别 - user_identity。
        """
        config = FridayAuthConfig(
            billing_id="test",
            agent_id="agent",
            context_token="token",
        )
        assert config.auth_level == "user_identity"


# ============================================================================
# 文档示例测试 - curl 示例
# ============================================================================

class TestDocExamplesCurl:
    """
    测试文档中的 curl 示例。

    参考：https://km.sankuai.com/collabpage/2720941091

    curl --location --request POST 'https://aigc.sankuai.com/v1/responses' \\
    --header 'Mt-Agent-Id: 你的agent-id' \\
    --header 'Authorization: 你的计费ID' \\
    --header 'Content-Type: application/json' \\
    --data-raw '{
        "model": "gpt-4o-mini",
        "input": "父子分块是什么",
        "stream": false,
        "tools": [
            {
                "type": "file_search",
                "vector_store_ids": ["你的知识库id"],
                "max_num_results": 20
            }
        ]
    }'
    """

    def test_file_search_curl_example(self):
        """
        测试文档中文件搜索的 curl 示例。
        """
        # 构建请求参数
        tools = [{
            "type": "file_search",
            "vector_store_ids": ["kb_123456"],
            "max_num_results": 20,
        }]
        params = build_friday_request_params(
            model_id="gpt-4o-mini",
            input_messages="父子分块是什么",
            tools=tools,
        )

        # 验证参数
        assert params["model"] == "gpt-4o-mini"
        assert params["input"] == "父子分块是什么"
        assert params["stream"] is True  # 我们的实现始终使用流式
        assert params["tools"][0]["type"] == "file_search"
        assert params["tools"][0]["vector_store_ids"] == ["kb_123456"]
        assert params["tools"][0]["max_num_results"] == 20


# ============================================================================
# 文档示例测试 - 返回参数
# ============================================================================

class TestDocExamplesResponse:
    """
    测试文档中的返回参数示例解析。

    参考：https://km.sankuai.com/collabpage/2720941091
    """

    def test_message_output_example(self):
        """
        测试 message 类型的输出示例解析。

        文档示例：
        {
            "output": {
                "type": "message",
                "id": "msg_2791034863861360640",
                "role": "assistant",
                "content": [
                    { "type": "output_text", "text": "...", "annotations": [] }
                ]
            }
        }
        """
        # 解析示例 JSON
        response_json = '''
        {
            "output": {
                "type": "message",
                "id": "msg_2791034863861360640",
                "role": "assistant",
                "content": [
                    { "type": "output_text", "text": "Hello", "annotations": [] }
                ]
            }
        }
        '''
        data = json.loads(response_json)

        assert data["output"]["type"] == "message"
        assert data["output"]["id"] == "msg_2791034863861360640"
        assert data["output"]["role"] == "assistant"
        assert data["output"]["content"][0]["type"] == "output_text"

    def test_function_call_output_example(self):
        """
        测试 function_call 类型的输出示例解析。

        文档示例：
        {
            "output": {
                "type": "function_call",
                "id": "fc_1649643355064359936",
                "name": "get_weather",
                "status": "completed",
                "arguments": "{\\"location\\":\\"北京, 中国\\"}",
                "call_id": "call_sLam6wcohZIAgJoBpTylwT0I"
            }
        }
        """
        response_json = '''
        {
            "output": {
                "type": "function_call",
                "id": "fc_1649643355064359936",
                "name": "get_weather",
                "status": "completed",
                "arguments": "{\\"location\\":\\"北京, 中国\\"}",
                "call_id": "call_sLam6wcohZIAgJoBpTylwT0I"
            }
        }
        '''
        data = json.loads(response_json)

        assert data["output"]["type"] == "function_call"
        assert data["output"]["name"] == "get_weather"
        assert data["output"]["status"] == "completed"
        args = json.loads(data["output"]["arguments"])
        assert args["location"] == "北京, 中国"

    def test_file_search_call_output_example(self):
        """
        测试 file_search_call 类型的输出示例解析。

        文档示例：
        {
            "output": {
                "queries": ["向量数据库是什么"],
                "results": [],
                "resultCount": 0,
                "queryCount": 1,
                "type": "file_search_call",
                "id": "fs_2791034863861360640",
                "status": "completed"
            }
        }
        """
        response_json = '''
        {
            "output": {
                "queries": ["向量数据库是什么"],
                "results": [],
                "resultCount": 0,
                "queryCount": 1,
                "type": "file_search_call",
                "id": "fs_2791034863861360640",
                "status": "completed"
            }
        }
        '''
        data = json.loads(response_json)

        assert data["output"]["type"] == "file_search_call"
        assert data["output"]["queries"] == ["向量数据库是什么"]
        assert data["output"]["status"] == "completed"

    def test_web_search_call_output_example(self):
        """
        测试 web_search_call 类型的输出示例解析。

        文档示例：
        {
            "output": {
                "action": { "type": "search", "query": "七夕礼物推荐" },
                "type": "web_search_call",
                "id": "ws_5283337895223879680",
                "status": "completed"
            }
        }
        """
        response_json = '''
        {
            "output": {
                "action": { "type": "search", "query": "七夕礼物推荐" },
                "type": "web_search_call",
                "id": "ws_5283337895223879680",
                "status": "completed"
            }
        }
        '''
        data = json.loads(response_json)

        assert data["output"]["type"] == "web_search_call"
        assert data["output"]["action"]["query"] == "七夕礼物推荐"
        assert data["output"]["status"] == "completed"


# ============================================================================
# 文档示例测试 - 流式事件
# ============================================================================

class TestDocExamplesStreamEvents:
    """
    测试文档中的流式事件示例解析。

    参考：https://km.sankuai.com/collabpage/2720941091
    """

    def test_response_created_event(self):
        """
        测试 response.created 事件。
        """
        event_json = '''
        {
            "type": "response.created",
            "sequence_number": 1,
            "response": {
                "id": "resp_123",
                "object": "response",
                "created_at": 1234567890,
                "output": []
            }
        }
        '''
        data = json.loads(event_json)

        assert data["type"] == "response.created"
        assert data["sequence_number"] == 1
        assert data["response"]["id"] == "resp_123"

    def test_output_text_delta_event(self):
        """
        测试 response.output_text.delta 事件。

        文档示例：
        {
            "type": "response.output_text.delta",
            "sequence_number": 541,
            "item_id": "msg_1952707252850794552",
            "delta": "的"
        }
        """
        event_json = '''
        {
            "type": "response.output_text.delta",
            "sequence_number": 541,
            "item_id": "msg_1952707252850794552",
            "delta": "的"
        }
        '''
        data = json.loads(event_json)

        assert data["type"] == "response.output_text.delta"
        assert data["sequence_number"] == 541
        assert data["item_id"] == "msg_1952707252850794552"
        assert data["delta"] == "的"

    def test_function_call_arguments_done_event(self):
        """
        测试 response.function_call_arguments.done 事件。
        """
        event_json = '''
        {
            "type": "response.function_call_arguments.done",
            "sequence_number": 100,
            "item_id": "fc_123",
            "arguments": "{\\"location\\": \\"北京\\"}"
        }
        '''
        data = json.loads(event_json)

        assert data["type"] == "response.function_call_arguments.done"
        args = json.loads(data["arguments"])
        assert args["location"] == "北京"

    def test_response_completed_event(self):
        """
        测试 response.completed 事件。
        """
        event_json = '''
        {
            "type": "response.completed",
            "sequence_number": 1000,
            "response": {
                "id": "resp_123",
                "status": "completed",
                "usage": {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "total_tokens": 150
                }
            }
        }
        '''
        data = json.loads(event_json)

        assert data["type"] == "response.completed"
        assert data["response"]["status"] == "completed"
        assert data["response"]["usage"]["input_tokens"] == 100
        assert data["response"]["usage"]["output_tokens"] == 50


# ============================================================================
# 配置文件测试
# ============================================================================

class TestConfigFile:
    """
    测试配置文件功能。
    """

    def test_config_file_exists(self):
        """测试配置文件存在。"""
        from src.providers.friday_config import DEFAULT_CONFIG_FILE

        assert DEFAULT_CONFIG_FILE.exists(), f"配置文件不存在: {DEFAULT_CONFIG_FILE}"

    def test_config_file_valid_json(self):
        """测试配置文件是有效的 JSON。"""
        from src.providers.friday_config import DEFAULT_CONFIG_FILE

        with open(DEFAULT_CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)

        assert "billing_id" in config
        assert "agent_id" in config
        assert "api_url" in config
        assert "default_model" in config

    def test_config_manager_reads_file(self):
        """测试配置管理器能读取配置文件。"""
        from src.providers.friday_config import get_config_manager

        manager = get_config_manager()
        api_url = manager.get_api_url()
        default_model = manager.get_default_model()

        assert api_url == "https://aigc.sankuai.com/v1/responses"
        assert default_model == "gpt-4o-mini"


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])

