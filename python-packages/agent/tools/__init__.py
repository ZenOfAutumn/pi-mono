"""
工具包模块。

提供工具插件化自动发现和注册功能。

使用示例:
    # 自动发现并注册所有工具
    from tools import discover_tools, create_registry_with_discovered_tools

    # 方式 1: 获取所有发现的工具列表
    tools = discover_tools()

    # 方式 2: 创建已注册所有发现工具的注册表
    registry = create_registry_with_discovered_tools()

    # 方式 3: 根据配置筛选发现的工具
    config = {"tools": ["bash", "calculate"]}
    registry = create_registry_with_discovered_tools(config)
"""
from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# 添加父目录到路径以支持导入
_current_dir = Path(__file__).parent
_parent_dir = _current_dir.parent
if str(_parent_dir) not in sys.path:
    sys.path.insert(0, str(_parent_dir))

from src.types import AgentTool
from src.tool_registry import ToolRegistry


def discover_tools(package_path: Optional[str] = None) -> List[AgentTool]:
    """
    自动发现指定包中的所有 AgentTool 实例。

    扫描指定包下的所有模块，查找导出的 AgentTool 实例。
    工具实例的变量名应该以 "_tool" 结尾或者是全大写的工具名。

    Args:
        package_path: 要扫描的包路径，默认为当前 tools 包

    Returns:
        发现的 AgentTool 实例列表

    使用示例:
        # 发现当前包中的所有工具
        tools = discover_tools()

        # 发现指定包中的工具
        tools = discover_tools("/path/to/custom/tools")
    """
    tools: List[AgentTool] = []

    if package_path is None:
        # 使用当前包路径
        package_path = str(Path(__file__).parent)

    # 获取包名
    package_name = __name__

    # 遍历包中的所有模块
    for _, module_name, is_pkg in pkgutil.iter_modules([package_path]):
        if is_pkg:
            continue  # 跳过子包

        try:
            # 导入模块
            full_module_name = f"{package_name}.{module_name}"
            module = importlib.import_module(full_module_name)

            # 查找模块中的 AgentTool 实例
            for attr_name in dir(module):
                # 跳过私有属性
                if attr_name.startswith("_"):
                    continue

                attr = getattr(module, attr_name)

                # 检查是否是 AgentTool 实例
                if isinstance(attr, AgentTool):
                    tools.append(attr)

        except Exception as e:
            # 导入失败时记录错误但继续处理其他模块
            print(f"Warning: Failed to import module {module_name}: {e}")
            continue

    return tools


def create_registry_with_discovered_tools(
    config: Optional[Dict[str, Any]] = None,
    package_path: Optional[str] = None,
) -> ToolRegistry:
    """
    自动发现工具并创建注册表。

    根据配置筛选工具（如果提供了配置），否则注册所有发现的工具。

    Args:
        config: 可选的配置字典，包含 "tools" 键（工具名称列表）
        package_path: 要扫描的包路径，默认为当前 tools 包

    Returns:
        包含发现工具的 ToolRegistry 实例

    使用示例:
        # 注册所有发现的工具
        registry = create_registry_with_discovered_tools()

        # 根据配置注册特定工具
        config = {"tools": ["bash", "calculate"]}
        registry = create_registry_with_discovered_tools(config)

        # 设置到 agent
        agent.set_tools(registry.get_all_tools())
    """
    # 导入 config_loader 中的函数
    from src.config_loader import get_tool_names_from_config

    # 发现所有工具
    discovered_tools = discover_tools(package_path)

    # 创建注册表
    registry = ToolRegistry()

    # 获取配置中指定的工具名称
    tool_names = get_tool_names_from_config(config) if config else []

    if tool_names:
        # 只注册配置中指定的工具
        for tool in discovered_tools:
            if tool.name in tool_names:
                registry.register(tool)
    else:
        # 注册所有发现的工具
        registry.register_many(discovered_tools)

    return registry


def get_discovered_tool_names(package_path: Optional[str] = None) -> List[str]:
    """
    获取所有发现的工具名称列表。

    Args:
        package_path: 要扫描的包路径，默认为当前 tools 包

    Returns:
        工具名称列表
    """
    tools = discover_tools(package_path)
    return [tool.name for tool in tools]


# 导出默认工具（向后兼容）
from .bash_tool import bash_tool

__all__ = [
    "discover_tools",
    "create_registry_with_discovered_tools",
    "get_discovered_tool_names",
    "bash_tool",
]

