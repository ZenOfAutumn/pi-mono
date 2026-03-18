"""
配置加载模块
支持从 JSON 文件加载 agent 配置，其中 system_prompt 可以是文件路径
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from .stream_fn_factory import create_stream_fn_from_config
from .tool_registry import ToolRegistry
from .types import AgentContext, AgentLoopConfig, AgentState, Model, ThinkingLevel, AgentTool, StreamFn


def load_system_prompt(prompt_value: str, config_dir: Optional[Path] = None) -> str:
    """
    加载系统提示词

    如果 prompt_value 是文件路径（以 .txt 结尾），则从文件读取内容
    否则直接返回 prompt_value 作为系统提示词

    Args:
        prompt_value: 系统提示词或文件路径
        config_dir: 配置文件所在目录（用于相对路径解析）

    Returns:
        系统提示词内容
    """
    # 检查是否是文件路径
    if prompt_value.endswith(".txt") or prompt_value.endswith(".md"):
        # 尝试解析为文件路径
        path = Path(prompt_value)

        # 如果是相对路径，基于 config_dir 解析
        if not path.is_absolute() and config_dir is not None:
            path = config_dir / path

        # 检查文件是否存在
        if path.exists() and path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()

    # 不是文件路径，直接返回
    return prompt_value


def load_agent_config(config_path: str | Path) -> Dict[str, Any]:
    """
    从 JSON 文件加载 agent 配置

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典，system_prompt 已解析为内容，llm_config_path 已解析为绝对路径
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    # 读取 JSON 配置
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    config_dir = config_path.parent

    # 解析 system_prompt
    if "system_prompt" in config:
        config["system_prompt"] = load_system_prompt(config["system_prompt"], config_dir)

    # 解析 llm_config_path 为绝对路径
    if "llm_config_path" in config:
        llm_config_path = Path(config["llm_config_path"])
        if not llm_config_path.is_absolute():
            llm_config_path = config_dir / llm_config_path
        # 规范化路径（解析 .. 等）
        config["llm_config_path"] = str(llm_config_path.resolve())

    return config


def create_agent_context_from_config(config: Dict[str, Any]) -> AgentContext:
    """
    从配置字典创建 AgentContext

    Args:
        config: 配置字典

    Returns:
        AgentContext 实例
    """
    return AgentContext(
        system_prompt=config.get("system_prompt", ""),
        messages=config.get("messages", []),
        tools=None,  # 工具需要单独注册
    )


def create_agent_state_from_config(
    config: Dict[str, Any],
    available_tools: Optional[List[AgentTool]] = None,
    tool_module_path: Optional[str] = None,
) -> AgentState:
    """
    从配置字典创建 AgentState

    Args:
        config: 配置字典，可包含 "tool_module_path" 键指定工具模块路径
        available_tools: 可选的可用工具列表，如果提供则从配置中筛选匹配的工具
        tool_module_path: 可选的工具模块路径（如 "tools"），如果提供则自动发现该模块中的工具
            注意：函数参数 tool_module_path 优先级高于 config 中的 tool_module_path

    Returns:
        AgentState 实例，tools 字段根据配置和提供的工具参数填充

    使用示例:
        # 方式 1: 基本用法（tools 为空列表）
        state = create_agent_state_from_config(config)

        # 方式 2: 在配置中指定工具模块路径
        config = {
            "tool_module_path": "tools",
            "tools": ["bash", "calculate"]
        }
        state = create_agent_state_from_config(config)

        # 方式 3: 提供可用工具列表，从配置筛选
        all_tools = [bash_tool, calculate_tool]
        state = create_agent_state_from_config(config, available_tools=all_tools)

        # 方式 4: 通过函数参数指定模块路径（优先级高于配置）
        state = create_agent_state_from_config(config, tool_module_path="tools")

        # 方式 5: 组合使用（函数参数 > available_tools > config.tool_module_path）
        state = create_agent_state_from_config(
            config,
            available_tools=all_tools,
            tool_module_path="tools"
        )
    """
    # 解析模型配置
    model_config = config.get("model", {})
    model = Model(
        api=model_config.get("api", ""),
        provider=model_config.get("provider", ""),
        id=model_config.get("id", ""),
    )

    # 解析思考级别
    thinking_level_str = config.get("thinking_level", "off")
    try:
        thinking_level = ThinkingLevel(thinking_level_str)
    except ValueError:
        thinking_level = ThinkingLevel.OFF

    # 解析工具模块路径（函数参数优先级高于配置）
    effective_tool_module_path = tool_module_path or config.get("tool_module_path")

    # 解析工具配置
    tools: List[AgentTool] = []
    tool_names = get_tool_names_from_config(config)

    if tool_names:
        # 配置中指定了工具名称
        if available_tools:
            # 从提供的工具列表中筛选
            tool_map = {tool.name: tool for tool in available_tools}
            tools = [tool_map[name] for name in tool_names if name in tool_map]
        elif effective_tool_module_path:
            # 从模块路径自动发现工具
            registry = create_tool_registry_from_module(effective_tool_module_path, config)
            tools = registry.get_all_tools()
    elif available_tools:
        # 配置未指定工具，但提供了可用工具列表，使用所有可用工具
        tools = available_tools
    elif effective_tool_module_path:
        # 配置未指定工具，但提供了模块路径，使用所有发现的工具
        registry = create_tool_registry_from_module(effective_tool_module_path)
        tools = registry.get_all_tools()

    return AgentState(
        system_prompt=config.get("system_prompt", ""),
        model=model,
        thinking_level=thinking_level,
        tools=tools,
        messages=config.get("messages", []),
    )


def create_agent_loop_config_from_config(config: Dict[str, Any]) -> AgentLoopConfig:
    """
    从配置字典创建 AgentLoopConfig

    Args:
        config: 配置字典

    Returns:
        AgentLoopConfig 实例
    """
    # 解析模型配置
    model_config = config.get("model", {})
    model = Model(
        api=model_config.get("api", ""),
        provider=model_config.get("provider", ""),
        id=model_config.get("id", ""),
    )

    return AgentLoopConfig(
        model=model,
        temperature=config.get("temperature"),
        max_tokens=config.get("max_tokens"),
        reasoning=config.get("reasoning"),
        session_id=config.get("session_id"),
        api_key=config.get("api_key"),
        thinking_budgets=config.get("thinking_budgets"),
    )


def get_tool_names_from_config(config: Dict[str, Any]) -> List[str]:
    """
    从配置字典中获取工具名称列表。

    Args:
        config: 配置字典

    Returns:
        工具名称列表，如果配置中没有 tools 键则返回空列表

    使用示例:
        config = load_agent_config("config.json")
        tool_names = get_tool_names_from_config(config)
        # tool_names = ["calculate", "read_file", "write_file"]
    """
    tools = config.get("tools", [])
    if isinstance(tools, list):
        return [str(name) for name in tools if isinstance(name, str)]
    return []


def create_tool_registry_from_available_tools(
    available_tools: List[Any],
    config: Optional[Dict[str, Any]] = None,
) -> ToolRegistry:
    """
    从可用工具列表和可选的配置创建工具注册表。

    如果提供了配置且配置中包含 tools 列表，则只注册配置中指定的工具。
    如果未提供配置或配置中没有 tools 列表，则注册所有可用工具。

    Args:
        available_tools: 所有可用的工具实例列表（AgentTool 或其他具有 name 属性的对象）
        config: 可选的配置字典，包含 "tools" 键（工具名称列表）

    Returns:
        ToolRegistry 实例

    使用示例:
        # 定义所有可用工具
        all_tools = [read_tool, write_tool, calculate_tool]

        # 从配置创建注册表（只包含配置中指定的工具）
        config = load_agent_config("config.json")
        registry = create_tool_registry_from_available_tools(all_tools, config)

        # 或者创建包含所有工具的注册表
        registry = create_tool_registry_from_available_tools(all_tools)

        # 获取工具列表并设置到 agent
        agent.set_tools(registry.get_all_tools())
    """
    registry = ToolRegistry()

    # 获取配置中指定的工具名称列表
    tool_names = get_tool_names_from_config(config) if config else []

    if tool_names:
        # 只注册配置中指定的工具
        for tool in available_tools:
            if hasattr(tool, "name") and tool.name in tool_names:
                registry.register(tool)
    else:
        # 注册所有可用工具
        registry.register_many(available_tools)

    return registry


def create_tool_registry_from_module(
    module_path: str,
    config: Optional[Dict[str, Any]] = None,
) -> ToolRegistry:
    """
    从指定模块路径自动发现工具并创建注册表。

    扫描指定包路径下的所有模块，自动发现并注册 AgentTool 实例。
    如果提供了配置，则只注册配置中指定的工具。

    Args:
        module_path: 工具模块的包路径（如 "tools" 或 "my_package.tools"）
        config: 可选的配置字典，包含 "tools" 键（工具名称列表）

    Returns:
        ToolRegistry 实例

    使用示例:
        # 从默认 tools 包发现工具
        config = load_agent_config("config.json")
        registry = create_tool_registry_from_module("tools", config)

        # 从自定义包发现工具
        registry = create_tool_registry_from_module("my_app.custom_tools")

        # 获取工具列表并设置到 agent
        agent.set_tools(registry.get_all_tools())
    """
    import importlib
    import pkgutil
    from pathlib import Path

    registry = ToolRegistry()
    discovered_tools: List[AgentTool] = []

    try:
        # 导入包
        package = importlib.import_module(module_path)
        package_path = Path(package.__file__).parent

        # 遍历包中的所有模块
        for _, module_name, is_pkg in pkgutil.iter_modules([str(package_path)]):
            if is_pkg:
                continue

            try:
                # 导入模块
                full_module_name = f"{module_path}.{module_name}"
                module = importlib.import_module(full_module_name)

                # 查找模块中的 AgentTool 实例
                for attr_name in dir(module):
                    if attr_name.startswith("_"):
                        continue

                    attr = getattr(module, attr_name)
                    if isinstance(attr, AgentTool):
                        discovered_tools.append(attr)

            except Exception as e:
                # 导入失败时记录警告但继续
                print(f"Warning: Failed to import module {module_name}: {e}")
                continue

    except ImportError as e:
        raise ImportError(f"Failed to import module {module_path}: {e}")

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


def create_stream_fn_from_agent_config(config: Dict[str, Any]) -> Optional[StreamFn]:
    """
    从 agent 配置创建 stream_fn（便捷函数）。

    这是 stream_fn_factory.create_stream_fn_from_config 的包装，
    提供与 config_loader 其他函数一致的命名风格。

    Args:
        config: agent 配置字典

    Returns:
        配置对应的 stream_fn，如果无法创建则返回 None

    示例:
        config = load_agent_config("config/agent_config.json")
        stream_fn = create_stream_fn_from_agent_config(config)

        agent = Agent(AgentOptions(
            initial_state={
                "system_prompt": config["system_prompt"],
                "model": Model(**config["model"]),
            },
            stream_fn=stream_fn,
        ))
    """
    return create_stream_fn_from_config(config)

