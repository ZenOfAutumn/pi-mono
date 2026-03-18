"""
config_loader.py 模块的单元测试。
"""
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from src.config_loader import (
    load_agent_config,
    load_system_prompt,
    create_agent_context_from_config,
    create_agent_state_from_config,
    create_agent_loop_config_from_config,
    get_tool_names_from_config,
    create_tool_registry_from_available_tools,
)
from src.types import ThinkingLevel, AgentTool


class TestLoadSystemPrompt:
    """load_system_prompt 函数的测试。"""

    def test_load_from_text_file(self):
        """测试从 .txt 文件加载系统提示词。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            prompt_file = Path(tmpdir) / "test_prompt.txt"
            prompt_content = "你是一个测试助手。"
            prompt_file.write_text(prompt_content, encoding="utf-8")

            # 加载提示词
            result = load_system_prompt(str(prompt_file))
            assert result == prompt_content

    def test_load_from_markdown_file(self):
        """测试从 .md 文件加载系统提示词。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            prompt_file = Path(tmpdir) / "test_prompt.md"
            prompt_content = "# 系统提示词\n\n你是一个助手。"
            prompt_file.write_text(prompt_content, encoding="utf-8")

            # 加载提示词
            result = load_system_prompt(str(prompt_file))
            assert result == prompt_content

    def test_load_direct_text(self):
        """测试直接返回非文件路径的提示词。"""
        prompt = "你是一个有帮助的助手。"
        result = load_system_prompt(prompt)
        assert result == prompt

    def test_load_with_relative_path(self):
        """测试使用相对路径加载。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建测试文件
            prompt_file = Path(tmpdir) / "prompts" / "system.txt"
            prompt_file.parent.mkdir(exist_ok=True)
            prompt_content = "相对路径测试。"
            prompt_file.write_text(prompt_content, encoding="utf-8")

            # 使用相对路径加载
            result = load_system_prompt("prompts/system.txt", Path(tmpdir))
            assert result == prompt_content

    def test_load_nonexistent_file(self):
        """测试加载不存在的文件时返回原值。"""
        prompt = "config/prompts/nonexistent.txt"
        result = load_system_prompt(prompt)
        # 文件不存在，返回原值
        assert result == prompt


class TestLoadAgentConfig:
    """load_agent_config 函数的测试。"""

    def test_load_basic_config(self):
        """测试加载基本配置。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            config_file = Path(tmpdir) / "agent_config.json"
            config = {
                "system_prompt": "直接设置的提示词",
                "model": {
                    "api": "openai-chat",
                    "provider": "openai",
                    "id": "gpt-4o"
                },
                "temperature": 0.7,
                "max_tokens": 2048
            }
            config_file.write_text(json.dumps(config), encoding="utf-8")

            # 加载配置
            loaded = load_agent_config(config_file)
            assert loaded["system_prompt"] == "直接设置的提示词"
            assert loaded["model"]["api"] == "openai-chat"
            assert loaded["temperature"] == 0.7

    def test_load_config_with_prompt_file(self):
        """测试从文件路径加载 system_prompt。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建提示词文件
            prompt_file = Path(tmpdir) / "system_prompt.md"
            prompt_content = "从文件加载的系统提示词。"
            prompt_file.write_text(prompt_content, encoding="utf-8")

            # 创建配置文件
            config_file = Path(tmpdir) / "agent_config.json"
            config = {
                "system_prompt": "system_prompt.md",
                "model": {"api": "openai-chat", "provider": "openai", "id": "gpt-4o"}
            }
            config_file.write_text(json.dumps(config), encoding="utf-8")

            # 加载配置
            loaded = load_agent_config(config_file)
            assert loaded["system_prompt"] == prompt_content

    def test_load_config_with_nested_prompt_path(self):
        """测试从嵌套路径加载 system_prompt。"""
        with tempfile.TemporaryDirectory() as tmpdir:
            # 创建提示词目录和文件
            prompts_dir = Path(tmpdir) / "prompts"
            prompts_dir.mkdir()
            prompt_file = prompts_dir / "custom.txt"
            prompt_content = "自定义提示词内容。"
            prompt_file.write_text(prompt_content, encoding="utf-8")

            # 创建配置文件
            config_file = Path(tmpdir) / "agent_config.json"
            config = {
                "system_prompt": "prompts/custom.txt",
                "model": {"api": "openai-chat", "provider": "openai", "id": "gpt-4o"}
            }
            config_file.write_text(json.dumps(config), encoding="utf-8")

            # 加载配置
            loaded = load_agent_config(config_file)
            assert loaded["system_prompt"] == prompt_content

    def test_load_config_not_found(self):
        """测试配置文件不存在时抛出异常。"""
        with pytest.raises(FileNotFoundError):
            load_agent_config("/nonexistent/path/config.json")


class TestCreateAgentContextFromConfig:
    """create_agent_context_from_config 函数的测试。"""

    def test_create_context_from_config(self):
        """测试从配置字典创建 AgentContext。"""
        config = {
            "system_prompt": "测试系统提示词",
            "messages": [{"role": "user", "content": "你好"}],
        }

        context = create_agent_context_from_config(config)
        assert context.system_prompt == "测试系统提示词"
        assert len(context.messages) == 1
        assert context.tools is None

    def test_create_context_with_empty_config(self):
        """测试从空配置创建 AgentContext。"""
        config = {}

        context = create_agent_context_from_config(config)
        assert context.system_prompt == ""
        assert context.messages == []
        assert context.tools is None


class TestCreateAgentStateFromConfig:
    """create_agent_state_from_config 函数的测试。"""

    def test_create_state_from_config(self):
        """测试从配置字典创建 AgentState。"""
        config = {
            "system_prompt": "测试系统提示词",
            "model": {
                "api": "openai-chat",
                "provider": "openai",
                "id": "gpt-4o"
            },
            "thinking_level": "high",
        }

        state = create_agent_state_from_config(config)
        assert state.system_prompt == "测试系统提示词"
        assert state.model.api == "openai-chat"
        assert state.thinking_level == ThinkingLevel.HIGH

    def test_create_state_with_invalid_thinking_level(self):
        """测试使用无效的思考级别时默认为 OFF。"""
        config = {
            "system_prompt": "提示词",
            "thinking_level": "invalid",
        }

        state = create_agent_state_from_config(config)
        assert state.thinking_level == ThinkingLevel.OFF

    def test_create_state_with_empty_config(self):
        """测试从空配置创建 AgentState。"""
        config = {}

        state = create_agent_state_from_config(config)
        assert state.system_prompt == ""
        assert state.thinking_level == ThinkingLevel.OFF

    def test_create_state_with_available_tools(self):
        """测试提供可用工具列表时从配置筛选工具。"""
        config = {
            "system_prompt": "测试",
            "tools": ["tool1", "tool2"],
        }

        # 创建测试工具
        tool1 = AgentTool(name="tool1", description="Test tool 1", parameters={}, label="Tool1")
        tool2 = AgentTool(name="tool2", description="Test tool 2", parameters={}, label="Tool2")
        tool3 = AgentTool(name="tool3", description="Test tool 3", parameters={}, label="Tool3")
        available_tools = [tool1, tool2, tool3]

        state = create_agent_state_from_config(config, available_tools=available_tools)

        assert len(state.tools) == 2
        assert tool1 in state.tools
        assert tool2 in state.tools
        assert tool3 not in state.tools

    def test_create_state_with_available_tools_no_config_tools(self):
        """测试提供可用工具但配置未指定工具时使用所有可用工具。"""
        config = {"system_prompt": "测试"}

        tool1 = AgentTool(name="tool1", description="Test tool 1", parameters={}, label="Tool1")
        tool2 = AgentTool(name="tool2", description="Test tool 2", parameters={}, label="Tool2")
        available_tools = [tool1, tool2]

        state = create_agent_state_from_config(config, available_tools=available_tools)

        assert len(state.tools) == 2
        assert tool1 in state.tools
        assert tool2 in state.tools

    def test_create_state_with_tool_module_path(self):
        """测试从模块路径自动发现工具。"""
        config = {
            "system_prompt": "测试",
            "tools": ["bash"],
        }

        state = create_agent_state_from_config(config, tool_module_path="tools")

        assert len(state.tools) == 1
        assert state.tools[0].name == "bash"

    def test_create_state_with_tool_module_path_no_config_tools(self):
        """测试从模块路径发现所有工具（配置未指定）。"""
        config = {"system_prompt": "测试"}

        state = create_agent_state_from_config(config, tool_module_path="tools")

        # 应该包含 bash 工具
        tool_names = [t.name for t in state.tools]
        assert "bash" in tool_names

    def test_create_state_tools_priority_available_tools_over_module(self):
        """测试 available_tools 优先级高于 tool_module_path。"""
        config = {
            "system_prompt": "测试",
            "tools": ["custom_tool"],
        }

        custom_tool = AgentTool(
            name="custom_tool",
            description="Custom tool",
            parameters={},
            label="Custom"
        )
        available_tools = [custom_tool]

        # 同时提供 available_tools 和 tool_module_path，应该优先使用 available_tools
        state = create_agent_state_from_config(
            config,
            available_tools=available_tools,
            tool_module_path="tools"
        )

        assert len(state.tools) == 1
        assert state.tools[0].name == "custom_tool"

    def test_create_state_with_tool_module_path_in_config(self):
        """测试从配置中读取 tool_module_path。"""
        config = {
            "system_prompt": "测试",
            "tool_module_path": "tools",
            "tools": ["bash"],
        }

        state = create_agent_state_from_config(config)

        assert len(state.tools) == 1
        assert state.tools[0].name == "bash"

    def test_create_state_tool_module_path_param_overrides_config(self):
        """测试函数参数 tool_module_path 优先级高于配置。"""
        config = {
            "system_prompt": "测试",
            "tool_module_path": "nonexistent_module",
            "tools": ["bash"],
        }

        # 函数参数应该覆盖配置中的值
        state = create_agent_state_from_config(
            config,
            tool_module_path="tools"
        )

        assert len(state.tools) == 1
        assert state.tools[0].name == "bash"

    def test_create_state_with_tool_module_path_in_config_no_tools(self):
        """测试配置中有 tool_module_path 但没有 tools 列表时使用所有工具。"""
        config = {
            "system_prompt": "测试",
            "tool_module_path": "tools",
        }

        state = create_agent_state_from_config(config)

        # 应该包含 bash 工具
        tool_names = [t.name for t in state.tools]
        assert "bash" in tool_names

    def test_create_state_with_no_tools_params(self):
        """测试不提供工具参数时 tools 为空列表。"""
        config = {"system_prompt": "测试"}

        state = create_agent_state_from_config(config)

        assert state.tools == []

    def test_create_state_with_config_tools_not_found(self):
        """测试配置中的工具在可用工具中找不到时跳过。"""
        config = {
            "system_prompt": "测试",
            "tools": ["nonexistent_tool"],
        }

        tool1 = AgentTool(name="tool1", description="Test tool 1", parameters={}, label="Tool1")
        available_tools = [tool1]

        state = create_agent_state_from_config(config, available_tools=available_tools)

        # 找不到的工具应该被跳过
        assert state.tools == []


class TestCreateAgentLoopConfigFromConfig:
    """create_agent_loop_config_from_config 函数的测试。"""

    def test_create_loop_config_from_config(self):
        """测试从配置字典创建 AgentLoopConfig。"""
        config = {
            "model": {
                "api": "anthropic-messages",
                "provider": "anthropic",
                "id": "claude-opus"
            },
            "temperature": 0.5,
            "max_tokens": 4096,
            "session_id": "session-123"
        }

        loop_config = create_agent_loop_config_from_config(config)
        assert loop_config.model.api == "anthropic-messages"
        assert loop_config.temperature == 0.5
        assert loop_config.max_tokens == 4096
        assert loop_config.session_id == "session-123"

    def test_create_loop_config_with_empty_config(self):
        """测试从空配置创建 AgentLoopConfig。"""
        config = {}

        loop_config = create_agent_loop_config_from_config(config)
        assert loop_config.model.api == ""
        assert loop_config.temperature is None
        assert loop_config.max_tokens is None


class TestGetToolNamesFromConfig:
    """get_tool_names_from_config 函数的测试。"""

    def test_get_tool_names_from_config(self):
        """测试从配置获取工具名称列表。"""
        config = {"tools": ["calculate", "read_file", "write_file"]}

        result = get_tool_names_from_config(config)

        assert result == ["calculate", "read_file", "write_file"]

    def test_get_tool_names_empty_list(self):
        """测试配置中 tools 为空列表。"""
        config = {"tools": []}

        result = get_tool_names_from_config(config)

        assert result == []

    def test_get_tool_names_missing_key(self):
        """测试配置中没有 tools 键。"""
        config = {"model": {}}

        result = get_tool_names_from_config(config)

        assert result == []

    def test_get_tool_names_non_list_value(self):
        """测试 tools 值为非列表类型。"""
        config = {"tools": "not_a_list"}

        result = get_tool_names_from_config(config)

        assert result == []

    def test_get_tool_names_filters_non_strings(self):
        """测试过滤非字符串的工具名称。"""
        config = {"tools": ["calculate", 123, None, "read_file"]}

        result = get_tool_names_from_config(config)

        assert result == ["calculate", "read_file"]


class TestCreateToolRegistryFromAvailableTools:
    """create_tool_registry_from_available_tools 函数的测试。"""

    def _create_test_tool(self, name: str) -> AgentTool:
        """创建测试工具。"""
        return AgentTool(
            name=name,
            description=f"Test tool {name}",
            parameters={},
            label=name.capitalize(),
        )

    def test_create_registry_with_config_tools(self):
        """测试根据配置创建注册表（选择特定工具）。"""
        tool1 = self._create_test_tool("calculate")
        tool2 = self._create_test_tool("read_file")
        tool3 = self._create_test_tool("write_file")
        all_tools = [tool1, tool2, tool3]

        config = {"tools": ["calculate", "read_file"]}
        registry = create_tool_registry_from_available_tools(all_tools, config)

        assert len(registry) == 2
        assert registry.has("calculate")
        assert registry.has("read_file")
        assert not registry.has("write_file")

    def test_create_registry_without_config(self):
        """测试不提供配置时注册所有工具。"""
        tool1 = self._create_test_tool("calculate")
        tool2 = self._create_test_tool("read_file")
        all_tools = [tool1, tool2]

        registry = create_tool_registry_from_available_tools(all_tools)

        assert len(registry) == 2
        assert registry.has("calculate")
        assert registry.has("read_file")

    def test_create_registry_with_empty_config(self):
        """测试空配置时注册所有工具。"""
        tool1 = self._create_test_tool("calculate")
        all_tools = [tool1]

        config = {}
        registry = create_tool_registry_from_available_tools(all_tools, config)

        assert len(registry) == 1
        assert registry.has("calculate")

    def test_create_registry_skips_missing_tools(self):
        """测试跳过配置中存在但可用工具中不存在的工具。"""
        tool = self._create_test_tool("calculate")
        all_tools = [tool]

        config = {"tools": ["calculate", "nonexistent"]}
        registry = create_tool_registry_from_available_tools(all_tools, config)

        assert len(registry) == 1
        assert registry.has("calculate")

