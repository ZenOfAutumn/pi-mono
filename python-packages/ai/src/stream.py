"""
LLM API 流式调用接口。

本模块提供主要的流式和完成函数，
用于通过已注册的提供商与 LLM API 交互。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional

from .api_registry import get_api_provider

if TYPE_CHECKING:
    from .core_types import (
        AssistantMessage,
        AssistantMessageEventStream,
        Context,
        Model,
        ProviderStreamOptions,
        SimpleStreamOptions,
    )


def _resolve_api_provider(api: str):
    """
    解析并返回指定 API 标识符对应的提供商。

    Args:
        api: API 标识符

    Returns:
        API 提供商

    Raises:
        ValueError: 如果没有为该 API 注册提供商
    """
    provider = get_api_provider(api)
    if not provider:
        raise ValueError(f"No API provider registered for api: {api}")
    return provider


def stream(
    model: "Model",
    context: "Context",
    options: Optional["ProviderStreamOptions"] = None,
) -> "AssistantMessageEventStream":
    """
    流式调用 LLM API。

    这是主要的流式接口，根据模型的 API 类型路由到相应的提供商。

    Args:
        model: 要使用的模型
        context: 对话上下文
        options: 可选的流式选项

    Returns:
        产生助手消息事件的事件流
    """
    provider = _resolve_api_provider(model.api)
    return provider.stream(model, context, options)


async def complete(
    model: "Model",
    context: "Context",
    options: Optional["ProviderStreamOptions"] = None,
) -> "AssistantMessage":
    """
    完成请求并返回完整的助手消息。

    这是一个便捷函数，内部使用流式调用，
    等待流完成后返回最终的助手消息。

    Args:
        model: 要使用的模型
        context: 对话上下文
        options: 可选的流式选项

    Returns:
        完整的助手消息
    """
    s = stream(model, context, options)
    return await s.result()


def stream_simple(
    model: "Model",
    context: "Context",
    options: Optional["SimpleStreamOptions"] = None,
) -> "AssistantMessageEventStream":
    """
    使用简化选项进行流式调用。

    这是简化的流式接口，接受统一的 reasoning 选项，
    而不是提供商特定的选项。

    Args:
        model: 要使用的模型
        context: 对话上下文
        options: 可选的简化流式选项（包含 reasoning 参数）

    Returns:
        产生助手消息事件的事件流
    """
    provider = _resolve_api_provider(model.api)
    return provider.streamSimple(model, context, options)


async def complete_simple(
    model: "Model",
    context: "Context",
    options: Optional["SimpleStreamOptions"] = None,
) -> "AssistantMessage":
    """
    使用简化选项完成请求并返回完整的助手消息。

    这是一个便捷函数，内部使用简化流式调用，
    等待流完成后返回最终的助手消息。

    Args:
        model: 要使用的模型
        context: 对话上下文
        options: 可选的简化流式选项（包含 reasoning 参数）

    Returns:
        完整的助手消息
    """
    s = stream_simple(model, context, options)
    return await s.result()

