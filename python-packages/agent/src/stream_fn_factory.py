"""
Stream 函数工厂模块

根据 agent 配置创建合适的 stream_fn，支持多种 LLM 提供商。
本模块提供配置驱动的 stream_fn 创建，实现与 Agent 创建的解耦。
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, Optional, Callable

if TYPE_CHECKING:
    from .types import StreamFn
    StreamFnCreator = Callable[[Dict[str, Any]], "StreamFn"]
else:
    StreamFnCreator = Callable[[Dict[str, Any]], Any]


# 全局注册的提供商创建函数
_stream_fn_creators: Dict[str, StreamFnCreator] = {}


def register_stream_fn_creator(provider: str, creator: StreamFnCreator) -> None:
    """
    注册提供商特定的 stream_fn 创建函数。

    用于扩展支持新的 LLM 提供商。

    Args:
        provider: 提供商名称（如 "friday", "openai", "anthropic"）
        creator: 创建 stream_fn 的函数，接收配置字典返回 StreamFn

    示例:
        def create_my_provider_stream_fn(config: Dict[str, Any]) -> StreamFn:
            from pi_ai import stream_simple
            def stream_fn(model, context, options):
                # 自定义逻辑
                return stream_simple(model, context, options)
            return stream_fn

        register_stream_fn_creator("my_provider", create_my_provider_stream_fn)
    """
    _stream_fn_creators[provider] = creator


def unregister_stream_fn_creator(provider: str) -> None:
    """
    注销提供商的 stream_fn 创建函数。

    Args:
        provider: 提供商名称
    """
    _stream_fn_creators.pop(provider, None)


def get_registered_providers() -> list[str]:
    """
    获取所有已注册的提供商名称。

    Returns:
        提供商名称列表
    """
    return list(_stream_fn_creators.keys())


def _create_friday_stream_fn(config: Dict[str, Any]) -> "StreamFn":
    """
    创建 Friday 提供商的 stream_fn。

    Args:
        config: agent 配置字典，应包含 llm_config_path

    Returns:
        Friday 专用的 stream_fn
    """
    try:
        from pi_ai import stream_simple
    except ImportError:
        raise ImportError(
            "pi-ai module is required for Friday provider. "
            "Please install it: pip install pi-ai"
        )

    llm_config_path = config.get("llm_config_path")

    async def friday_stream_fn(model, context, options):
        """
        Friday 专用的 stream 函数。

        自动注入 llm_config_path 到 options 中，用于 Friday 认证。
        """
        if options is None:
            options = {}
        else:
            # 复制避免修改原对象
            options = dict(options)

        # 注入 configPath 供 Friday provider 使用
        if llm_config_path and "configPath" not in options:
            options["configPath"] = llm_config_path

        return await stream_simple(model, context, options)

    return friday_stream_fn


def _create_default_stream_fn(config: Dict[str, Any]) -> "StreamFn":
    """
    创建默认的 stream_fn（使用 pi_ai.stream_simple）。

    适用于大多数标准提供商（openai, anthropic, google 等）。

    Args:
        config: agent 配置字典

    Returns:
        默认的 stream_fn
    """
    try:
        from pi_ai import stream_simple
    except ImportError:
        raise ImportError(
            "pi-ai module is required. "
            "Please install it: pip install pi-ai"
        )

    # 直接返回 pi_ai.stream_simple，无需包装
    return stream_simple


# 注册内置的提供商创建函数
register_stream_fn_creator("friday", _create_friday_stream_fn)


def create_stream_fn_from_config(config: Dict[str, Any]) -> Optional["StreamFn"]:
    """
    根据 agent 配置创建 stream_fn。

    这是主要的工厂函数，根据配置中的 model.provider 选择合适的创建逻辑。

    Args:
        config: agent 配置字典，应包含:
            - model.provider: 提供商名称
            - llm_config_path: 可选，LLM 配置文件路径（Friday 需要）

    Returns:
        配置对应的 stream_fn，如果无法创建则返回 None

    示例:
        config = load_agent_config("config/agent_config.json")
        stream_fn = create_stream_fn_from_config(config)

        agent = Agent(AgentOptions(
            initial_state={...},
            stream_fn=stream_fn,
        ))
    """
    model_config = config.get("model", {})
    provider = model_config.get("provider", "").lower()

    if not provider:
        # 没有指定提供商，返回默认 stream_fn
        return _create_default_stream_fn(config)

    # 查找注册的创建函数
    creator = _stream_fn_creators.get(provider)

    if creator:
        # 使用提供商特定的创建函数
        return creator(config)

    # 未找到特定提供商的实现，使用默认实现
    return _create_default_stream_fn(config)


def create_stream_fn_with_options(
    config: Dict[str, Any],
    default_options: Optional[Dict[str, Any]] = None,
) -> "StreamFn":
    """
    创建支持默认选项的 stream_fn。

    与 create_stream_fn_from_config 类似，但允许注入默认选项，
    这些选项会在每次调用时合并到请求中。

    Args:
        config: agent 配置字典
        default_options: 默认选项，会在每次调用时合并

    Returns:
        包装后的 stream_fn

    示例:
        config = load_agent_config("config/agent_config.json")
        stream_fn = create_stream_fn_with_options(
            config,
            default_options={"temperature": 0.5}
        )
    """
    base_stream_fn = create_stream_fn_from_config(config)

    if base_stream_fn is None:
        raise ValueError("Failed to create base stream_fn from config")

    if not default_options:
        return base_stream_fn

    async def wrapped_stream_fn(model, context, options):
        """包装函数，合并默认选项。"""
        merged_options = {}
        if default_options:
            merged_options.update(default_options)
        if options:
            merged_options.update(options)

        return await base_stream_fn(model, context, merged_options)

    return wrapped_stream_fn

