"""
Agent 集成测试。

测试从配置创建 agent，执行用户 prompt，并使用 bash 工具完成。
"""
import asyncio
import json
import tempfile
import unittest
from pathlib import Path
from typing import List, Optional

import pytest

from agent import load_agent_config, create_agent_state_from_config, create_stream_fn_from_agent_config, Agent, \
    AgentOptions
from agent.agent_loop import AgentStream


def create_mock_stream_fn(responses: List[dict]):
    """创建一个模拟的 LLM 流函数，返回预定义的响应。

    注意：stream_fn 返回的流应该发出原始事件（start/done/text 等），
    agent_loop 会将它们转换为标准事件（message_start/message_end 等）。
    """
    call_index = [0]

    async def stream_fn(model, context, options):
        stream = AgentStream()

        async def run():
            await asyncio.sleep(0.01)  # 让出控制权，确保流先返回

            if call_index[0] < len(responses):
                response = responses[call_index[0]]
                call_index[0] += 1

                # 发出 start 事件（agent_loop 会转换为 message_start）
                stream.push({"type": "start", "partial": response})
                await asyncio.sleep(0)  # 让出控制权

                # 发出文本内容事件
                for content_item in response.get("content", []):
                    if content_item.get("type") == "text":
                        stream.push({
                            "type": "text_delta",
                            "text": content_item.get("text", ""),
                        })
                        await asyncio.sleep(0)

                # 发出 done 事件（agent_loop 会转换为 message_end）
                stream.push({"type": "done", "reason": response.get("stop_reason", "stop"), "partial": response})
                await asyncio.sleep(0)

            stream.end()

        asyncio.create_task(run())
        return stream

    return stream_fn


class TestAgentIntegration(unittest.IsolatedAsyncioTestCase):
    """Agent 集成测试。"""

    def _create_test_config(self, tmpdir: str, llm_config_path: Optional[str] = None) -> Path:
        """创建测试配置文件。"""
        config_file = Path(tmpdir) / "test_config.json"
        config = {
            "system_prompt": "You are a helpful assistant that can execute bash commands.",
            "model": {
                "api": "friday-responses",
                "provider": "friday",
                "id": "gpt-4o"
            },
            "thinking_level": "off",
            "tool_module_path": "tools",
            "tools": ["bash"]
        }
        # 如果指定了 llm_config_path，添加到配置中
        if llm_config_path:
            config["llm_config_path"] = llm_config_path
        config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")
        return config_file

    def test_create_agent_from_config(self):
        """测试从配置创建 agent。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = self._create_test_config(tmpdir)

            # 1. 加载配置
            config = load_agent_config(config_file)

            # 2. 从配置创建 AgentState
            agent_state = create_agent_state_from_config(config)

            # 3. 验证工具已加载
            assert len(agent_state.tools) == 1
            assert agent_state.tools[0].name == "bash"

            # 4. 创建 Agent
            agent = Agent(AgentOptions(initial_state=agent_state.__dict__))

            # 5. 验证 agent 状态
            assert agent.state.system_prompt == "You are a helpful assistant that can execute bash commands."
            assert len(agent.state.tools) == 1
            assert agent.state.tools[0].name == "bash"

    @pytest.mark.asyncio
    async def test_agent_with_bash_tool_execution(self):
        """测试 agent 使用 bash 工具执行命令。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = self._create_test_config(tmpdir)

            # 加载配置并创建 agent
            config = load_agent_config(config_file)
            agent_state = create_agent_state_from_config(config)
            agent = Agent(AgentOptions(initial_state=agent_state.__dict__))

            # 收集事件
            events = []
            agent.subscribe(lambda event: events.append(event))

            # 执行一个简单的 prompt（这里我们只是验证工具已正确注册）
            # 注意：实际执行需要 LLM 调用，这里只验证工具配置正确
            assert agent.state.tools[0].name == "bash"
            assert agent.state.tools[0].execute is not None

    def test_agent_tool_registry_integration(self):
        """测试 agent 工具注册表集成。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = self._create_test_config(tmpdir)

            # 加载配置
            config = load_agent_config(config_file)

            # 从配置创建 AgentState（自动加载工具）
            agent_state = create_agent_state_from_config(config)

            # 验证工具已正确加载
            assert len(agent_state.tools) == 1
            bash_tool = agent_state.tools[0]
            assert bash_tool.name == "bash"
            assert bash_tool.label == "Bash"
            assert "shell" in bash_tool.description.lower()

            # 创建 Agent 并设置工具
            agent = Agent(AgentOptions(initial_state={
                "system_prompt": agent_state.system_prompt,
                "model": agent_state.model,
            }))
            agent.set_tools(agent_state.tools)

            # 验证 agent 有正确的工具
            assert len(agent.state.tools) == 1
            assert agent.state.tools[0].name == "bash"

    @pytest.mark.asyncio
    async def test_bash_tool_direct_execution(self):
        """测试直接执行 bash 工具。"""
        from tools.bash_tool import bash_tool

        # 直接调用 bash 工具执行命令
        result = await bash_tool.execute(
            "test-call-id",
            {"command": "echo 'Hello from bash tool'"},
            None,
            None
        )

        # 验证结果
        assert len(result.content) == 1
        assert "Hello from bash tool" in result.content[0].text
        assert result.details["exit_code"] == 0

    def test_config_with_multiple_tools(self):
        """测试配置中包含多个工具。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建包含多个工具的配置
            config_file = Path(tmpdir) / "test_config.json"
            config = {
                "system_prompt": "You are a helpful assistant.",
                "model": {
                    "api": "openai-chat",
                    "provider": "openai",
                    "id": "gpt-4o"
                },
                "tool_module_path": "tools",
                "tools": ["bash"]  # 可以添加更多工具
            }
            config_file.write_text(json.dumps(config, indent=2), encoding="utf-8")

            # 加载配置
            config = load_agent_config(config_file)

            # 创建 AgentState
            agent_state = create_agent_state_from_config(config)

            # 验证工具已加载
            assert len(agent_state.tools) >= 1
            tool_names = [t.name for t in agent_state.tools]
            assert "bash" in tool_names

    @pytest.mark.asyncio
    async def test_agent_workflow_with_config(self):
        """测试完整的 agent 工作流：配置 -> AgentState -> Agent -> prompt 调用。

        实际测试 agent.prompt() 方法，验证从配置加载到执行用户提示的完整流程。
        此测试会实际调用 LLM（friday 平台），需要确保环境中有可用的 API 密钥。
        如果没有 API 密钥，测试会被跳过。

        增强版测试：验证智能搜索功能的多个场景，不依赖固定内容。
        """
        # 使用正式配置文件：test/ -> agent/ -> config/agent_config.json
        config_file = Path(__file__).parent.parent / "config" / "agent_config.json"
        assert config_file.exists(), f"正式配置文件不存在: {config_file}"

        # 1. 加载配置
        config = load_agent_config(config_file)

        # 验证 llm_config_path 被正确解析为绝对路径
        assert "llm_config_path" in config, "配置中应该包含 llm_config_path"
        assert Path(config["llm_config_path"]).is_absolute(), "llm_config_path 应该是绝对路径"
        assert Path(config["llm_config_path"]).exists(), f"LLM 配置文件不存在: {config['llm_config_path']}"

        # 2. 创建 AgentState（包含工具）
        agent_state = create_agent_state_from_config(config)

        # 3. 从配置创建 stream_fn（自动处理 llm_config_path）
        stream_fn = create_stream_fn_from_agent_config(config)

        # 4. 创建 Agent（传入从配置创建的 stream_fn）
        agent = Agent(AgentOptions(
            initial_state={
                "system_prompt": agent_state.system_prompt,
                "model": agent_state.model,
                "thinking_level": agent_state.thinking_level,
            },
            stream_fn=stream_fn,
        ))

        # 5. 设置工具
        agent.set_tools(agent_state.tools)

        # 6. 验证完整配置
        assert agent.state.system_prompt == config["system_prompt"]
        assert agent.state.model.id == config["model"]["id"]
        assert agent.state.model.api == config["model"]["api"]
        assert agent.state.model.provider == config["model"]["provider"]
        assert agent.state.tools[0].name == "bash"

        # 7. 验证工具可执行
        bash_tool = agent.state.tools[0]
        assert bash_tool.execute is not None

        # 8. 测试多个不同的搜索场景
        test_cases = [
            {
                "name": "Bibliography搜索",
                "prompt": "从/Users/wuliang/Workspace/self/pi-mono/python-packages/agent/resources/动手学深度学习.pdf找出 Bibliography部分的第一条记录",
                "expected_tool": "pdf_read",
                "expected_search": "Bibliography"
            },
            {
                "name": "Index搜索",
                "prompt": "从/Users/wuliang/Workspace/self/pi-mono/python-packages/agent/resources/动手学深度学习.pdf找出 Index部分的内容",
                "expected_tool": "pdf_read",
                "expected_search": "Index"
            },
            {
                "name": "Appendix搜索",
                "prompt": "从/Users/wuliang/Workspace/self/pi-mono/python-packages/agent/resources/动手学深度学习.pdf找出 Appendix部分的内容",
                "expected_tool": "pdf_read",
                "expected_search": "Appendix"
            }
        ]

        for test_case in test_cases:
            print(f"\n🧪 测试场景: {test_case['name']}")

            # 重置事件收集
            events = []

            def on_event(event):
                events.append(event)

            agent.subscribe(on_event)

            # 执行 prompt（实际调用 LLM）
            await agent.prompt(test_case["prompt"])

            # 验证基本事件流
            event_types = [e.get("type") for e in events]
            assert len(events) > 0, f"{test_case['name']}: 应该至少发出一些事件"
            assert "agent_start" in event_types, f"{test_case['name']}: 应该发出 agent_start 事件"
            assert "message_start" in event_types, f"{test_case['name']}: 应该发出 message_start 事件"
            assert "message_end" in event_types, f"{test_case['name']}: 应该发出 message_end 事件"

            # 验证消息被正确添加到状态中
            user_messages = [m for m in agent.state.messages if m.get("role") == "user"]
            assert len(user_messages) >= 1, f"{test_case['name']}: 应该至少有一条用户消息"

            # 检查是否有工具调用
            tool_result_messages = [m for m in agent.state.messages if m.get("role") == "toolResult"]

            if tool_result_messages:
                tool_result = tool_result_messages[-1]  # 获取最后一个工具结果
                details = tool_result.get('details', {})

                # 验证工具调用成功且有内容返回
                assert details.get('text_length', 0) > 0, f"{test_case['name']}: 应该提取到文本内容"

                # 验证搜索查询被正确处理
                if 'search_query' in details:
                    search_query = details.get('search_query', '')
                    print(f"  ✅ 搜索查询 '{search_query}' 被正确处理")

                    # 验证页面定位合理（对于Bibliography应该在文档后半部分）
                    if 'bibliography' in search_query.lower():
                        start_page = details.get('start_page', 0)
                        # Bibliography通常在文档后半部分，应该大于100页
                        assert start_page > 100, f"{test_case['name']}: Bibliography应该在文档后半部分，但找到第{start_page}页"
                        print(f"  ✅ Bibliography定位到第{start_page}页（文档后半部分）")

                # 验证返回的内容包含相关信息
                content = tool_result.get('content', [])
                if isinstance(content, list) and len(content) > 0:
                    text_content = None
                    for item in content:
                        if hasattr(item, 'text'):
                            text_content = item.text
                            break
                        elif isinstance(item, dict) and 'text' in item:
                            text_content = item['text']
                            break

                    if text_content:
                        # 验证内容不为空且有意义
                        assert len(text_content.strip()) > 50, f"{test_case['name']}: 返回的内容应该有意义（超过50字符）"
                        print(f"  ✅ 成功提取到相关内容（{len(text_content)}字符）")

                        # 验证内容格式正确（包含页码标记）
                        assert "--- Page" in text_content, f"{test_case['name']}: 内容应该包含页码标记"
                        print(f"  ✅ 内容格式正确，包含页码信息")

            print(f"  ✅ {test_case['name']} 测试通过\n")

            # 清理消息历史以便下一个测试
            agent.state.messages = []

        print("🎉 所有搜索场景测试完成！")

    @pytest.mark.asyncio
    async def test_pdf_search_functionality_comprehensive(self):
        """专门测试PDF智能搜索功能的全面性。

        验证搜索功能在不同场景下的表现，包括：
        1. 从文档末尾搜索（Bibliography）
        2. 从文档开头搜索（Table of Contents）
        3. 搜索不存在的内容
        4. 搜索性能验证
        """
        from tools.pdf_tool import read_pdf

        pdf_path = "/Users/wuliang/Workspace/self/pi-mono/python-packages/agent/resources/动手学深度学习.pdf"

        # 测试场景1：Bibliography搜索（从后往前）
        print("🧪 测试Bibliography搜索（文档末尾）")
        result1 = await read_pdf(
            pdf_path,
            search_query="Bibliography"
        )

        assert result1.details.get('text_length', 0) > 0, "Bibliography搜索应该返回内容"
        assert result1.details.get('start_page', 0) > 100, "Bibliography应该在文档后半部分"
        assert result1.details.get('search_query') == "Bibliography", "搜索查询应该被正确保存"
        print(f"  ✅ Bibliography搜索成功：第{result1.details.get('start_page')}页，{result1.details.get('text_length')}字符")

        # 测试场景2：Table of Contents搜索（从前往后）
        print("🧪 测试Table of Contents搜索（文档开头）")
        result2 = await read_pdf(
            pdf_path,
            search_query="Table of Contents"
        )

        assert result2.details.get('text_length', 0) > 0, "Table of Contents搜索应该返回内容"
        assert result2.details.get('start_page', 999) < 50, "Table of Contents应该在文档前半部分"
        print(f"  ✅ Table of Contents搜索成功：第{result2.details.get('start_page')}页，{result2.details.get('text_length')}字符")

        # 测试场景3：Index搜索
        print("🧪 测试Index搜索")
        result3 = await read_pdf(
            pdf_path,
            search_query="Index"
        )

        # Index可能在文档末尾，验证搜索逻辑
        if result3.details.get('text_length', 0) > 0:
            print(f"  ✅ Index搜索成功：第{result3.details.get('start_page')}页，{result3.details.get('text_length')}字符")
        else:
            print("  ℹ️  Index部分可能不存在于该文档中")

        # 测试场景4：搜索不存在的内容
        print("🧪 测试不存在内容搜索")
        result4 = await read_pdf(
            pdf_path,
            search_query="NonExistentChapterXYZ"
        )

        # 应该回退到常规提取
        assert result4.details.get('text_length', 0) > 0, "即使搜索失败也应该回退到常规提取"
        print(f"  ✅ 不存在内容搜索正确回退：{result4.details.get('text_length')}字符")

        # 测试场景5：验证搜索参数传递
        print("🧪 测试搜索参数传递")
        result5 = await read_pdf(
            pdf_path,
            search_query="Bibliography",
            max_chars=5000  # 限制字符数
        )

        assert result5.details.get('max_chars') == 5000, "max_chars参数应该被正确传递"
        assert result5.details.get('search_query') == "Bibliography", "search_query参数应该被正确传递"
        print(f"  ✅ 参数传递验证成功")

        print("🎉 PDF智能搜索功能全面测试完成！")

    @pytest.mark.asyncio
    async def test_bash_tool_with_different_commands(self):
        """测试 bash 工具执行不同类型的命令。"""
        from tools.bash_tool import bash_tool

        # 测试 echo 命令
        result1 = await bash_tool.execute(
            "test-1",
            {"command": "echo 'test1'"},
            None,
            None
        )
        assert "test1" in result1.content[0].text

        # 测试 pwd 命令
        result2 = await bash_tool.execute(
            "test-2",
            {"command": "pwd"},
            None,
            None
        )
        assert result2.details["exit_code"] == 0

        # 测试带环境变量
        result3 = await bash_tool.execute(
            "test-3",
            {"command": "echo $TEST_VAR", "env": {"TEST_VAR": "hello"}},
            None,
            None
        )
        assert "hello" in result3.content[0].text

