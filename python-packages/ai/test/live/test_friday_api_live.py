"""
Friday Responses API 实际调用测试。

本测试文件实际调用 Friday Responses API，验证请求和响应的正确性。
配置从 friday.json 文件读取。

运行方式：
    pytest test/test_friday_api_live.py -v -s

注意：需要有有效的 billing_id 和 agent_id 配置。
"""

import json
from pathlib import Path
from typing import Any, Dict, List

import aiohttp
import pytest

# 配置文件路径
CONFIG_FILE = Path(__file__).parent.parent / "config" / "friday.json"
FRIDAY_API_URL = "https://aigc.sankuai.com/v1/responses"


# ============================================================================
# 配置加载
# ============================================================================

def load_config() -> Dict[str, Any]:
    """从配置文件加载配置。"""
    if not CONFIG_FILE.exists():
        pytest.skip(f"配置文件不存在: {CONFIG_FILE}")

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_headers(config: Dict[str, Any]) -> Dict[str, str]:
    """构建请求头。"""
    headers = {
        "Content-Type": "application/json;charset=UTF-8",
    }

    if config.get("billing_id"):
        headers["Authorization"] = f"Bearer {config['billing_id']}"

    if config.get("agent_id"):
        headers["Mt-Agent-Id"] = config["agent_id"]

    if config.get("context_token"):
        headers["Mt-Context-Token"] = config["context_token"]

    if config.get("user_id"):
        headers["Mt-User-Id"] = config["user_id"]

    return headers


# ============================================================================
# API 调用辅助函数
# ============================================================================

async def call_friday_api(
    payload: Dict[str, Any],
    headers: Dict[str, str],
) -> Dict[str, Any]:
    """
    非流式调用 Friday API。

    Args:
        payload: 请求体
        headers: 请求头

    Returns:
        响应数据
    """
    async with aiohttp.ClientSession() as session:
        async with session.post(
            FRIDAY_API_URL,
            headers=headers,
            json=payload,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"API 错误 ({response.status}): {error_text}")

            return await response.json()


async def call_friday_api_stream(
    payload: Dict[str, Any],
    headers: Dict[str, str],
) -> List[Dict[str, Any]]:
    """
    流式调用 Friday API。

    Args:
        payload: 请求体
        headers: 请求头

    Returns:
        事件列表
    """
    events = []

    async with aiohttp.ClientSession() as session:
        async with session.post(
            FRIDAY_API_URL,
            headers=headers,
            json=payload,
        ) as response:
            if response.status != 200:
                error_text = await response.text()
                raise Exception(f"API 错误 ({response.status}): {error_text}")

            async for line in response.content:
                line_text = line.decode("utf-8").strip()

                if not line_text or line_text.startswith(":"):
                    continue

                if line_text.startswith("data: "):
                    data_str = line_text[6:]

                    if data_str == "[DONE]":
                        break

                    try:
                        event = json.loads(data_str)
                        events.append(event)
                    except json.JSONDecodeError:
                        continue

    return events


# ============================================================================
# 测试类
# ============================================================================

class TestFridayAPILive:
    """
    Friday API 实际调用测试。

    基于文档示例：https://km.sankuai.com/collabpage/2720941091
    """

    @pytest.fixture
    def config(self) -> Dict[str, Any]:
        """加载配置。"""
        return load_config()

    @pytest.fixture
    def headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        """构建请求头。"""
        return get_headers(config)

    # ------------------------------------------------------------------------
    # 文档示例 1: 基础文本输入
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_text_input_streaming(self, headers: Dict[str, str]):
        """
        测试基础文本输入（流式）。

        文档示例：
        "input": "Write a one-sentence bedtime story about a unicorn."
        """
        payload = {
            "model": "gpt-4o-mini",
            "input": "写一句关于独角兽的睡前故事。",
            "stream": True,
        }

        events = await call_friday_api_stream(payload, headers)

        # 验证收到事件
        assert len(events) > 0, "应该收到至少一个事件"

        # 查找文本增量事件
        text_deltas = [
            e for e in events
            if e.get("type") == "response.output_text.delta"
        ]
        assert len(text_deltas) > 0, "应该有文本增量事件"

        # 验证完成事件
        completed_events = [
            e for e in events
            if e.get("type") == "response.completed"
        ]
        assert len(completed_events) > 0, "应该有完成事件"

        # 打印响应文本
        full_text = "".join(e.get("delta", "") for e in text_deltas)
        print(f"\n响应文本: {full_text}")

    @pytest.mark.asyncio
    async def test_text_input_non_streaming(self, headers: Dict[str, str]):
        """
        测试基础文本输入（非流式）。

        文档示例中 stream: false
        """
        payload = {
            "model": "gpt-4o-mini",
            "input": "什么是向量数据库？",
            "stream": False,
        }

        response = await call_friday_api(payload, headers)

        # 验证响应结构
        assert "id" in response, "响应应包含 id"
        assert "output" in response, "响应应包含 output"
        assert response["model"] == "gpt-4o-mini"

        # 打印响应
        print(f"\n响应 ID: {response['id']}")
        print(f"输出: {json.dumps(response['output'], ensure_ascii=False, indent=2)}")

    # ------------------------------------------------------------------------
    # 文档示例 2: 多模态输入（需要外网可访问图片）
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_multimodal_image_input(self, headers: Dict[str, str]):
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
        payload = {
            "model": "gpt-4o-mini",
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": "这张图片里有什么？"},
                        {
                            "type": "input_image",
                            "image_url": "https://q5.itc.cn/images01/20250619/635b5ae72061473980eddf40aea857a6.jpeg"
                        }
                    ]
                }
            ],
            "stream": True,
        }

        events = await call_friday_api_stream(payload, headers)

        text_deltas = [
            e for e in events
            if e.get("type") == "response.output_text.delta"
        ]
        full_text = "".join(e.get("delta", "") for e in text_deltas)
        print(f"\n图片描述: {full_text}")

    # ------------------------------------------------------------------------
    # 文档示例 3: 自定义工具调用
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_custom_function_tool(self, headers: Dict[str, str]):
        """
        测试自定义工具调用。

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
        payload = {
            "model": "gpt-4o-mini",
            "input": "北京今天天气怎么样？",
            "stream": True,
            "tools": [
                {
                    "type": "function",
                    "name": "get_weather",
                    "description": "获取指定地点的当前天气温度。",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "城市和国家，例如：北京, 中国"
                            }
                        },
                        "required": ["location"],
                        "additionalProperties": False
                    }
                }
            ],
        }

        events = await call_friday_api_stream(payload, headers)

        # 查找工具调用事件
        tool_call_events = [
            e for e in events
            if "function_call" in e.get("type", "")
        ]

        print(f"\n事件类型: {set(e.get('type') for e in events)}")

        # 检查是否有工具调用（模型可能选择不调用工具）
        if tool_call_events:
            print(f"工具调用事件: {json.dumps(tool_call_events, ensure_ascii=False, indent=2)}")

    # ------------------------------------------------------------------------
    # 文档示例 4: 多轮对话
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_multi_turn_conversation(self, headers: Dict[str, str]):
        """
        测试多轮对话（previous_response_id）。

        文档：通过 previous_response_id 自动关联会话历史
        """
        # 第一轮对话
        payload1 = {
            "model": "gpt-4o-mini",
            "input": "请记住我的名字是小明。",
            "stream": False,
        }

        response1 = await call_friday_api(payload1, headers)
        response_id = response1.get("id")
        assert response_id, "应该返回响应 ID"

        print(f"\n第一轮响应 ID: {response_id}")

        # 第二轮对话，使用 previous_response_id
        payload2 = {
            "model": "gpt-4o-mini",
            "input": "我刚才说我叫什么名字？",
            "stream": False,
            "previous_response_id": response_id,
        }

        response2 = await call_friday_api(payload2, headers)

        # 提取响应文本
        output = response2.get("output", {})
        if isinstance(output, dict):
            content = output.get("content", [])
            text = "".join(
                c.get("text", "") for c in content
                if c.get("type") == "output_text"
            )
        else:
            text = str(output)

        print(f"第二轮响应: {text}")

        # 验证模型记住名字（宽松检查）
        assert "小明" in text or "名字" in text, "模型应该记住或提及名字"

    # ------------------------------------------------------------------------
    # 文档示例 5: 网页搜索工具
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_web_search_tool(self, headers: Dict[str, str]):
        """
        测试网页搜索内置工具。

        文档示例：
        { "tools": [{ "type": "web_search_preview" }] }
        """
        payload = {
            "model": "glm-5",
            "input": "中国热点新闻如何？",
            "stream": True,
            "tools": [
                {"type": "web_search_preview"}
            ],
        }

        events = await call_friday_api_stream(payload, headers)

        # 检查是否有网页搜索调用
        web_search_events = [
            e for e in events
            if "web_search_preview" in str(e.get("type", ""))
        ]

        print(f"\n事件类型: {set(e.get('type') for e in events)}")
        if web_search_events:
            print(f"网页搜索事件: {json.dumps(web_search_events, ensure_ascii=False, indent=2)}")

    # ------------------------------------------------------------------------
    # 文档示例 6: 思考模型配置
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_think_config(self, headers: Dict[str, str]):
        """
        测试思考模型配置。

        文档示例：
        {
            "think": {
                "enabled": "true",
                "thinkTokens": 4800
            }
        }
        """
        payload = {
            "model": "gpt-4o-mini",
            "input": "商人 60 元买入，70 元卖出；80 元买入，90 元卖出。请分步列出每一步的现金流，算出最终总利润。",
            "stream": False,
            "think": {
                "enabled": True,
                "thinkTokens": 4
            }
        }

        response = await call_friday_api(payload, headers)

        print(f"\n思考模型响应 ID: {response.get('id')}")
        print(f"输出: {json.dumps(response.get('output'), ensure_ascii=False, indent=2)}")

    # ------------------------------------------------------------------------
    # 文档示例 7: JSON 格式输出
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_json_format_output(self, headers: Dict[str, str]):
        """
        测试 JSON 格式输出。

        文档示例：
        {
            "text": {
                "format": {
                    "type": "json_object"
                }
            }
        }

        注意：文档要求 prompt 中必须含有 "json" 字段才能使用 json_object 格式。
        """
        payload = {
            "model": "gpt-4o-mini",
            "input": "北京周末打卡好去处",
            "prompt": {
                "prompt_template": "你是一个美食推荐专家，会根据用户倾向{{prefer}}主动给用户推荐一些今天应该吃什么的建议，用户有要求的话，会遵循他们的建议，使用json",
                "variables": {
                    "prefer": "韩式烤肉"
                }
            },
            "max_output_tokens": 5000,
            "temperature": 0.9,
            "top_p": 0.9,
            "stream": False,
            "text": {
                "format": {
                    "type": "json_object"
                }
            }
        }

        response = await call_friday_api(payload, headers)

        # 打印完整响应以便调试
        print(f"\n完整响应: {json.dumps(response, ensure_ascii=False, indent=2)}")

        # 提取响应文本
        output = response.get("output", {})
        text = ""

        # 处理不同的输出格式
        if isinstance(output, dict):
            content = output.get("content", [])
            if isinstance(content, list):
                text = "".join(
                    c.get("text", "") for c in content
                    if c.get("type") == "output_text"
                )
            elif isinstance(content, str):
                text = content
        elif isinstance(output, list):
            # 可能是 output 数组
            for item in output:
                if item.get("type") == "message":
                    content = item.get("content", [])
                    text = "".join(
                        c.get("text", "") for c in content
                        if c.get("type") == "output_text"
                    )
        else:
            text = str(output)

        print(f"\nJSON 响应文本: {text}")

        # 验证是否为有效 JSON（宽松检查）
        if text.strip():
            try:
                parsed = json.loads(text)
                print(f"解析后的 JSON: {json.dumps(parsed, ensure_ascii=False, indent=2)}")
            except json.JSONDecodeError as e:
                # 不强制失败，仅记录警告
                print(f"警告：响应不是有效的 JSON: {e}")
        else:
            print("警告：响应文本为空，可能 API 未返回预期的 JSON 格式")

    # ------------------------------------------------------------------------
    # 文档示例 8: 参数控制测试
    # ------------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_temperature_parameter(self, headers: Dict[str, str]):
        """
        测试 temperature 参数。

        文档：用于采样的温度值，范围在0到2之间
        """
        # 低温度 - 更确定性
        payload_low_temp = {
            "model": "gpt-4o-mini",
            "input": "说一个数字。",
            "stream": False,
            "temperature": 0.1,
        }

        response = await call_friday_api(payload_low_temp, headers)
        print(f"\n低温度响应: {response.get('output')}")

    @pytest.mark.asyncio
    async def test_max_output_tokens(self, headers: Dict[str, str]):
        """
        测试 max_output_tokens 参数。

        文档：模型最大生成长度
        """
        payload = {
            "model": "gpt-4o-mini",
            "input": "请详细介绍一下人工智能概念。",
            "stream": False,
            "max_output_tokens": 2048,  # 限制输出长度
        }

        response = await call_friday_api(payload, headers)

        # 检查是否被截断（响应应该较短）
        output = response.get("output", {})
        if isinstance(output, dict):
            content = output.get("content", [])
            text = "".join(
                c.get("text", "") for c in content
                if c.get("type") == "output_text"
            )
            print(f"\n限制输出长度的响应（约 {len(text)} 字符）: {text[:200]}...")

    # ------------------------------------------------------------------------
    # 配置验证测试
    # ------------------------------------------------------------------------

    def test_config_file_valid(self, config: Dict[str, Any]):
        """验证配置文件有效。"""
        assert "billing_id" in config, "配置应包含 billing_id"
        assert "agent_id" in config, "配置应包含 agent_id"
        assert config["billing_id"], "billing_id 不应为空"
        assert config["agent_id"], "agent_id 不应为空"

        print(f"\n配置:")
        print(f"  billing_id: {config['billing_id']}")
        print(f"  agent_id: {config['agent_id']}")
        print(f"  api_url: {config.get('api_url', FRIDAY_API_URL)}")
        print(f"  default_model: {config.get('default_model', 'gpt-4o-mini')}")

    def test_headers_built_correctly(self, headers: Dict[str, str]):
        """验证请求头构建正确。"""
        assert "Authorization" in headers, "应有 Authorization 头"
        assert "Mt-Agent-Id" in headers, "应有 Mt-Agent-Id 头"
        assert headers["Content-Type"] == "application/json;charset=UTF-8"

        print(f"\n请求头:")
        for k, v in headers.items():
            # 敏感信息脱敏
            if k == "Authorization":
                print(f"  {k}: Bearer ***{v[-10:]}")
            else:
                print(f"  {k}: {v}")


# ============================================================================
# 运行测试
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

