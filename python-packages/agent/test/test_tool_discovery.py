"""
工具自动发现功能的单元测试。
"""
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from src.types import AgentTool, AgentToolResult, TextContent
from src.config_loader import create_tool_registry_from_module, get_tool_names_from_config
from tools import discover_tools, create_registry_with_discovered_tools, get_discovered_tool_names


def create_test_tool_file(directory: Path, name: str, tool_name: str):
    """创建测试工具文件。"""
    tool_file = directory / f"{name}.py"
    content = f'''
"""Test tool module."""
from src.types import AgentTool, AgentToolResult, TextContent

def execute_{tool_name}(tool_call_id, params, signal, on_update):
    return AgentToolResult(
        content=[TextContent(text="test")],
        details={{}},
    )

{tool_name}_tool = AgentTool(
    name="{tool_name}",
    label="{tool_name.capitalize()}",
    description="Test tool {tool_name}",
    parameters={{}},
    execute=execute_{tool_name},
)
'''
    tool_file.write_text(content)


class TestDiscoverTools:
    """discover_tools 函数的测试。"""

    def test_discover_tools_in_default_package(self):
        """测试在默认包中发现工具。"""
        tools = discover_tools()

        # 应该至少发现 bash_tool
        tool_names = [t.name for t in tools]
        assert "bash" in tool_names

    def test_discover_tools_returns_agent_tool_instances(self):
        """测试发现的工具是 AgentTool 实例。"""
        tools = discover_tools()

        for tool in tools:
            assert isinstance(tool, AgentTool)
            assert tool.name


class TestCreateRegistryWithDiscoveredTools:
    """create_registry_with_discovered_tools 函数的测试。"""

    def test_create_registry_with_all_tools(self):
        """测试创建包含所有发现工具的注册表。"""
        registry = create_registry_with_discovered_tools()

        # 应该包含 bash 工具
        assert registry.has("bash")

    def test_create_registry_with_config_filter(self):
        """测试根据配置筛选工具。"""
        config = {"tools": ["bash"]}
        registry = create_registry_with_discovered_tools(config)

        assert registry.has("bash")
        assert len(registry) == 1

    def test_create_registry_with_empty_config(self):
        """测试空配置时注册所有工具。"""
        config = {}
        registry = create_registry_with_discovered_tools(config)

        # 应该包含所有发现的工具
        assert len(registry) >= 1


class TestGetDiscoveredToolNames:
    """get_discovered_tool_names 函数的测试。"""

    def test_get_discovered_tool_names(self):
        """测试获取发现的工具名称列表。"""
        names = get_discovered_tool_names()

        assert isinstance(names, list)
        assert "bash" in names


class TestCreateToolRegistryFromModule:
    """create_tool_registry_from_module 函数的测试。"""

    def test_create_registry_from_tools_module(self):
        """测试从 tools 模块创建注册表。"""
        registry = create_tool_registry_from_module("tools")

        assert registry.has("bash")

    def test_create_registry_from_module_with_config(self):
        """测试带配置从模块创建注册表。"""
        config = {"tools": ["bash"]}
        registry = create_tool_registry_from_module("tools", config)

        assert registry.has("bash")
        assert len(registry) == 1

    def test_create_registry_from_invalid_module_raises(self):
        """测试无效模块路径抛出异常。"""
        with pytest.raises(ImportError):
            create_tool_registry_from_module("nonexistent_module_xyz")


class TestIntegration:
    """集成测试。"""

    def test_full_workflow_with_config(self):
        """测试完整工作流：加载配置 -> 发现工具 -> 创建注册表 -> 设置到 agent。"""
        from src import load_agent_config
        from src.agent import Agent, AgentOptions

        # 创建临时配置文件
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "agent_config.json"
            config_content = '''
{
    "system_prompt": "You are a helpful assistant.",
    "model": {
        "api": "openai-chat",
        "provider": "openai",
        "id": "gpt-4o"
    },
    "tools": ["bash"]
}
'''
            config_file.write_text(config_content)

            # 1. 加载配置
            config = load_agent_config(config_file)

            # 2. 从配置获取工具名称
            tool_names = get_tool_names_from_config(config)
            assert tool_names == ["bash"]

            # 3. 从模块创建注册表（根据配置筛选）
            registry = create_tool_registry_from_module("tools", config)

            # 4. 获取工具列表
            tools = registry.get_all_tools()
            assert len(tools) == 1
            assert tools[0].name == "bash"

            # 5. 创建 agent 并设置工具
            agent = Agent(AgentOptions(initial_state={"system_prompt": config["system_prompt"]}))
            agent.set_tools(tools)

            # 验证 agent 有正确的工具
            assert len(agent.state.tools) == 1
            assert agent.state.tools[0].name == "bash"

