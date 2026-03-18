"""
工具注册表模块

提供 ToolRegistry 类用于统一管理工具的注册、读取和修改。
支持从配置中读取工具名称列表，并映射到实际的 AgentTool 实例。
"""
from __future__ import annotations

from typing import Dict, List, Optional, Any

from .types import AgentTool


class ToolRegistry:
    """
    工具注册表。

    统一管理工具的注册、读取和修改。支持从配置中的工具名称列表
    获取对应的 AgentTool 实例。

    使用示例:
        # 创建注册表
        registry = ToolRegistry()

        # 注册工具
        registry.register(calculate_tool)
        registry.register_many([read_tool, write_tool])

        # 从配置获取工具列表
        config = {"tools": ["calculate", "read_file"]}
        tools = registry.get_tools_from_config(config["tools"])

        # 获取单个工具
        tools = registry.get("calculate")

        # 检查工具是否存在
        if registry.has("calculate"):
            ...

        # 注销工具
        registry.unregister("calculate")

        # 获取所有已注册工具
        all_tools = registry.get_all_tools()

        # 获取所有工具名称
        all_names = registry.get_all_names()
    """

    def __init__(self):
        """初始化空的工具注册表。"""
        self._tools: Dict[str, AgentTool] = {}

    def register(self, tool: AgentTool) -> "ToolRegistry":
        """
        注册单个工具。

        Args:
            tool: 要注册的工具实例

        Returns:
            self，支持链式调用

        Raises:
            ValueError: 如果工具名称为空
        """
        if not tool.name:
            raise ValueError("Tool name cannot be empty")
        self._tools[tool.name] = tool
        return self

    def register_many(self, tools: List[AgentTool]) -> "ToolRegistry":
        """
        批量注册多个工具。

        Args:
            tools: 工具实例列表

        Returns:
            self，支持链式调用
        """
        for tool in tools:
            self.register(tool)
        return self

    def unregister(self, name: str) -> bool:
        """
        注销指定名称的工具。

        Args:
            name: 工具名称

        Returns:
            如果工具存在并被删除返回 True，否则返回 False
        """
        if name in self._tools:
            del self._tools[name]
            return True
        return False

    def get(self, name: str) -> Optional[AgentTool]:
        """
        获取指定名称的工具。

        Args:
            name: 工具名称

        Returns:
            工具实例，如果不存在返回 None
        """
        return self._tools.get(name)

    def has(self, name: str) -> bool:
        """
        检查指定名称的工具是否已注册。

        Args:
            name: 工具名称

        Returns:
            如果工具已注册返回 True，否则返回 False
        """
        return name in self._tools

    def get_all_tools(self) -> List[AgentTool]:
        """
        获取所有已注册的工具。

        Returns:
            工具实例列表
        """
        return list(self._tools.values())

    def get_all_names(self) -> List[str]:
        """
        获取所有已注册工具的名称。

        Returns:
            工具名称列表
        """
        return list(self._tools.keys())

    def get_tools_from_config(
        self, tool_names: List[str], skip_missing: bool = True
    ) -> List[AgentTool]:
        """
        根据配置中的工具名称列表获取对应的工具实例。

        Args:
            tool_names: 配置中的工具名称列表
            skip_missing: 如果为 True，跳过未注册的工具；
                         如果为 False，遇到未注册的工具时抛出 KeyError

        Returns:
            工具实例列表

        Raises:
            KeyError: 如果 skip_missing=False 且遇到未注册的工具
        """
        tools: List[AgentTool] = []
        for name in tool_names:
            tool = self.get(name)
            if tool:
                tools.append(tool)
            elif not skip_missing:
                raise KeyError(f"Tool '{name}' is not registered in the registry")
        return tools

    def clear(self) -> "ToolRegistry":
        """
        清空所有已注册的工具。

        Returns:
            self，支持链式调用
        """
        self._tools.clear()
        return self

    def __len__(self) -> int:
        """返回已注册工具的数量。"""
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        """检查指定名称的工具是否已注册。"""
        return self.has(name)

    def __getitem__(self, name: str) -> AgentTool:
        """
        通过名称获取工具。

        Raises:
            KeyError: 如果工具不存在
        """
        tool = self.get(name)
        if tool is None:
            raise KeyError(f"Tool '{name}' not found")
        return tool

    def __setitem__(self, name: str, tool: AgentTool) -> None:
        """注册工具（通过字典语法）。"""
        self.register(tool)

    def __delitem__(self, name: str) -> None:
        """
        注销工具（通过字典语法）。

        Raises:
            KeyError: 如果工具不存在
        """
        if not self.unregister(name):
            raise KeyError(f"Tool '{name}' not found")

    def __iter__(self):
        """迭代所有工具名称。"""
        return iter(self._tools)

    def __repr__(self) -> str:
        """返回注册表的字符串表示。"""
        return f"ToolRegistry(tools={list(self._tools.keys())})"


def create_tool_registry_from_config(
    config: Dict[str, Any], available_tools: List[AgentTool], skip_missing: bool = True
) -> ToolRegistry:
    """
    从配置和可用工具列表创建工具注册表。

    Args:
        config: 配置字典，包含 "tools" 键（工具名称列表）
        available_tools: 所有可用的工具实例列表
        skip_missing: 是否跳过配置中指定但未在 available_tools 中找到的工具

    Returns:
        配置好的 ToolRegistry 实例

    使用示例:
        # 定义所有可用工具
        all_tools = [read_tool, write_tool, calculate_tool]

        # 从配置创建注册表
        config = load_agent_config("config.json")
        registry = create_tool_registry_from_config(config, all_tools)

        # 获取配置中指定的工具
        tools = registry.get_all_tools()
        agent.set_tools(tools)
    """
    registry = ToolRegistry()

    # 注册所有可用工具
    registry.register_many(available_tools)

    # 从配置获取工具名称列表
    tool_names = config.get("tools", [])

    # 如果配置中有工具列表，过滤出配置指定的工具
    if tool_names:
        # 获取配置中指定的工具
        selected_tools = registry.get_tools_from_config(tool_names, skip_missing=skip_missing)

        # 清空并重新注册选中的工具
        registry.clear()
        registry.register_many(selected_tools)

    return registry

