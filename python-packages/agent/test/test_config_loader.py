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
)
from src.types import ThinkingLevel


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
            prompt_file = Path(tmpdir) / "system_prompt.txt"
            prompt_content = "从文件加载的系统提示词。"
            prompt_file.write_text(prompt_content, encoding="utf-8")

            # 创建配置文件
            config_file = Path(tmpdir) / "agent_config.json"
            config = {
                "system_prompt": "system_prompt.txt",
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

