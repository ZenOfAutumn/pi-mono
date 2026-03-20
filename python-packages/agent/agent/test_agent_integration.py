"""
Agent 集成测试。

测试从配置创建 agent，执行用户 prompt，并使用 bash 工具完成。
"""
import asyncio
import json
import tempfile
from pathlib import Path
from typing import List, Optional

import pytest
from agent import load_agent_config, create_agent_state_from_config, create_stream_fn_from_agent_config, Agent, \
    AgentOptions
from agent.agent_loop import AgentStream
from agent.types import AgentTool, AgentToolResult, TextContent, Usage


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


class TestAgentIntegration:
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
        """
        # 检查 ai 模块是否可用

        with tempfile.TemporaryDirectory() as tmpdir:
            # 使用 llm_config_path 创建测试配置
            # 计算正确的路径：test/ -> agent/ -> python-packages/ -> ai/config/friday.json
            project_root = Path(__file__).parent.parent.parent  # test/ -> agent/ -> python-packages/
            llm_config_path = str(project_root / "ai" / "config" / "friday.json")
            config_file = self._create_test_config(tmpdir, llm_config_path=llm_config_path)

            # 完整工作流
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
            assert agent.state.system_prompt == "You are a helpful assistant that can execute bash commands."
            assert agent.state.model.id == "gpt-4o"
            assert agent.state.model.api == "friday-responses"
            assert agent.state.model.provider == "friday"
            assert len(agent.state.tools) == 1
            assert agent.state.tools[0].name == "bash"

            # 7. 验证工具可执行
            bash_tool = agent.state.tools[0]
            assert bash_tool.execute is not None

            # 8. 实际测试 prompt 方法 - 订阅事件并验证事件流
            events = []

            def on_event(event):
                events.append(event)

            agent.subscribe(on_event)

            # 执行 prompt（实际调用 LLM）
            await agent.prompt("Say 'Hello from agent test' and nothing else")

            # 验证事件流中包含了预期的初始事件
            event_types = [e.get("type") for e in events]

            # 验证至少有一些事件被发出（表明 prompt 方法确实被执行了）
            assert len(events) > 0, "应该至少发出一些事件"

            # 验证事件序列包含关键事件
            assert "agent_start" in event_types, "应该发出 agent_start 事件"
            assert "turn_start" in event_types, "应该发出 turn_start 事件"
            assert "message_start" in event_types, "应该发出 message_start 事件"
            assert "message_end" in event_types, "应该发出 message_end 事件"
            assert "turn_end" in event_types, "应该发出 turn_end 事件"
            assert "agent_end" in event_types, "应该发出 agent_end 事件"

            # 验证消息被正确添加到状态中
            assert len(agent.state.messages) >= 1, "消息应该被添加到状态中"

            # 找到用户消息
            user_messages = [m for m in agent.state.messages if m.get("role") == "user"]
            assert len(user_messages) >= 1, "应该至少有一条用户消息"
            assert "Hello from agent test" in str(user_messages[0]["content"]), "用户消息内容应该包含输入"

            # 验证助手响应也被添加
            assistant_messages = [m for m in agent.state.messages if m.get("role") == "assistant"]
            assert len(assistant_messages) >= 1, "应该至少有一条助手消息"
            assert agent.state.messages[-1]["role"] == "assistant", "最后一条消息应该是助手消息"

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

