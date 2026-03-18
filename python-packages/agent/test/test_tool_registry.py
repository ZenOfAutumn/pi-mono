"""
tool_registry.py 模块的单元测试。
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from src.tool_registry import ToolRegistry, create_tool_registry_from_config
from src.types import AgentTool, AgentToolResult, TextContent


def create_test_tool(name: str, description: str = "") -> AgentTool:
    """创建测试工具。"""
    return AgentTool(
        name=name,
        description=description or f"Test tools {name}",
        parameters={"type": "object", "properties": {}},
        label=name.capitalize(),
    )


class TestToolRegistry:
    """ToolRegistry 类的测试。"""

    def test_create_empty_registry(self):
        """测试创建空的注册表。"""
        registry = ToolRegistry()
        assert len(registry) == 0
        assert registry.get_all_tools() == []
        assert registry.get_all_names() == []

    def test_register_single_tool(self):
        """测试注册单个工具。"""
        registry = ToolRegistry()
        tool = create_test_tool("test")

        result = registry.register(tool)

        assert result is registry  # 支持链式调用
        assert len(registry) == 1
        assert registry.has("test")
        assert registry.get("test") == tool

    def test_register_tool_without_name_raises(self):
        """测试注册没有名称的工具时抛出异常。"""
        registry = ToolRegistry()
        tool = create_test_tool("")

        with pytest.raises(ValueError, match="Tool name cannot be empty"):
            registry.register(tool)

    def test_register_many_tools(self):
        """测试批量注册多个工具。"""
        registry = ToolRegistry()
        tools = [
            create_test_tool("tool1"),
            create_test_tool("tool2"),
            create_test_tool("tool3"),
        ]

        result = registry.register_many(tools)

        assert result is registry
        assert len(registry) == 3
        assert registry.has("tool1")
        assert registry.has("tool2")
        assert registry.has("tool3")

    def test_unregister_tool(self):
        """测试注销工具。"""
        registry = ToolRegistry()
        tool = create_test_tool("test")
        registry.register(tool)

        result = registry.unregister("test")

        assert result is True
        assert len(registry) == 0
        assert not registry.has("test")

    def test_unregister_nonexistent_tool(self):
        """测试注销不存在的工具。"""
        registry = ToolRegistry()

        result = registry.unregister("nonexistent")

        assert result is False

    def test_get_nonexistent_tool(self):
        """测试获取不存在的工具。"""
        registry = ToolRegistry()

        result = registry.get("nonexistent")

        assert result is None

    def test_get_all_tools(self):
        """测试获取所有工具。"""
        registry = ToolRegistry()
        tool1 = create_test_tool("tool1")
        tool2 = create_test_tool("tool2")
        registry.register(tool1)
        registry.register(tool2)

        result = registry.get_all_tools()

        assert len(result) == 2
        assert tool1 in result
        assert tool2 in result

    def test_get_all_names(self):
        """测试获取所有工具名称。"""
        registry = ToolRegistry()
        registry.register(create_test_tool("tool1"))
        registry.register(create_test_tool("tool2"))

        result = registry.get_all_names()

        assert sorted(result) == ["tool1", "tool2"]

    def test_clear_registry(self):
        """测试清空注册表。"""
        registry = ToolRegistry()
        registry.register(create_test_tool("tool1"))
        registry.register(create_test_tool("tool2"))

        result = registry.clear()

        assert result is registry
        assert len(registry) == 0

    def test_contains_operator(self):
        """测试 contains 操作符。"""
        registry = ToolRegistry()
        registry.register(create_test_tool("test"))

        assert "test" in registry
        assert "nonexistent" not in registry

    def test_getitem_operator(self):
        """测试 getitem 操作符。"""
        registry = ToolRegistry()
        tool = create_test_tool("test")
        registry.register(tool)

        result = registry["test"]

        assert result == tool

    def test_getitem_nonexistent_raises(self):
        """测试获取不存在的工具时抛出 KeyError。"""
        registry = ToolRegistry()

        with pytest.raises(KeyError, match="Tool 'nonexistent' not found"):
            _ = registry["nonexistent"]

    def test_setitem_operator(self):
        """测试 setitem 操作符。"""
        registry = ToolRegistry()
        tool = create_test_tool("test")

        registry["test"] = tool

        assert registry.get("test") == tool

    def test_delitem_operator(self):
        """测试 delitem 操作符。"""
        registry = ToolRegistry()
        registry.register(create_test_tool("test"))

        del registry["test"]

        assert not registry.has("test")

    def test_delitem_nonexistent_raises(self):
        """测试删除不存在的工具时抛出 KeyError。"""
        registry = ToolRegistry()

        with pytest.raises(KeyError, match="Tool 'nonexistent' not found"):
            del registry["nonexistent"]

    def test_iter_operator(self):
        """测试迭代操作符。"""
        registry = ToolRegistry()
        registry.register(create_test_tool("tool1"))
        registry.register(create_test_tool("tool2"))

        names = list(registry)

        assert sorted(names) == ["tool1", "tool2"]

    def test_repr(self):
        """测试 repr 输出。"""
        registry = ToolRegistry()
        registry.register(create_test_tool("tool1"))
        registry.register(create_test_tool("tool2"))

        result = repr(registry)

        assert "ToolRegistry" in result
        assert "tool1" in result
        assert "tool2" in result


class TestGetToolsFromConfig:
    """get_tools_from_config 方法的测试。"""

    def test_get_tools_from_config(self):
        """测试从配置获取工具列表。"""
        registry = ToolRegistry()
        tool1 = create_test_tool("calculate")
        tool2 = create_test_tool("read_file")
        tool3 = create_test_tool("write_file")
        registry.register(tool1)
        registry.register(tool2)
        registry.register(tool3)

        result = registry.get_tools_from_config(["calculate", "read_file"])

        assert len(result) == 2
        assert tool1 in result
        assert tool2 in result
        assert tool3 not in result

    def test_get_tools_from_config_skip_missing(self):
        """测试跳过未注册的工具。"""
        registry = ToolRegistry()
        tool = create_test_tool("calculate")
        registry.register(tool)

        result = registry.get_tools_from_config(["calculate", "nonexistent"])

        assert len(result) == 1
        assert tool in result

    def test_get_tools_from_config_raise_on_missing(self):
        """测试遇到未注册工具时抛出异常。"""
        registry = ToolRegistry()
        registry.register(create_test_tool("calculate"))

        with pytest.raises(KeyError, match="Tool 'nonexistent' is not registered"):
            registry.get_tools_from_config(["calculate", "nonexistent"], skip_missing=False)

    def test_get_tools_from_config_empty_list(self):
        """测试空列表返回空结果。"""
        registry = ToolRegistry()
        registry.register(create_test_tool("calculate"))

        result = registry.get_tools_from_config([])

        assert result == []


class TestCreateToolRegistryFromConfig:
    """create_tool_registry_from_config 函数的测试。"""

    def test_create_registry_with_tool_selection(self):
        """测试从配置创建注册表（选择特定工具）。"""
        tool1 = create_test_tool("calculate")
        tool2 = create_test_tool("read_file")
        tool3 = create_test_tool("write_file")
        all_tools = [tool1, tool2, tool3]

        config = {"tools": ["calculate", "read_file"]}
        registry = create_tool_registry_from_config(config, all_tools)

        assert len(registry) == 2
        assert registry.has("calculate")
        assert registry.has("read_file")
        assert not registry.has("write_file")

    def test_create_registry_without_tools_key(self):
        """测试配置中没有 tools 键时注册所有工具。"""
        tool1 = create_test_tool("calculate")
        tool2 = create_test_tool("read_file")
        all_tools = [tool1, tool2]

        config = {"model": {}}  # 没有 tools 键
        registry = create_tool_registry_from_config(config, all_tools)

        assert len(registry) == 2
        assert registry.has("calculate")
        assert registry.has("read_file")

    def test_create_registry_with_empty_config(self):
        """测试空配置时注册所有工具。"""
        tool1 = create_test_tool("calculate")
        all_tools = [tool1]

        config = {}
        registry = create_tool_registry_from_config(config, all_tools)

        assert len(registry) == 1
        assert registry.has("calculate")

    def test_create_registry_skip_missing_tools(self):
        """测试跳过配置中指定但未提供的工具。"""
        tool = create_test_tool("calculate")
        all_tools = [tool]

        config = {"tools": ["calculate", "nonexistent"]}
        registry = create_tool_registry_from_config(config, all_tools, skip_missing=True)

        assert len(registry) == 1
        assert registry.has("calculate")

    def test_create_registry_raise_on_missing_tools(self):
        """测试遇到缺失工具时抛出异常。"""
        tool = create_test_tool("calculate")
        all_tools = [tool]

        config = {"tools": ["calculate", "nonexistent"]}

        with pytest.raises(KeyError, match="Tool 'nonexistent' is not registered"):
            create_tool_registry_from_config(config, all_tools, skip_missing=False)

