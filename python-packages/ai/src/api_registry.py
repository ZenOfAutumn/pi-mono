"""
API 提供商注册中心。

本模块提供 API 提供商的注册管理功能，
支持动态注册和获取不同 LLM API 的流函数。
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable, Dict, List, Optional, TypeVar

if TYPE_CHECKING:
    from .core_types import AssistantMessageEventStream, Context, Model, SimpleStreamOptions, StreamOptions

# 类型变量：API 标识符（受 str 约束）
TApi = TypeVar("TApi", bound=str)
# 类型变量：流选项（受 StreamOptions 约束）
TOptions = TypeVar("TOptions", bound="StreamOptions")


@dataclass
class ApiProvider:
    """API 提供商配置。"""

    api: str  # API 标识符，如 "openai-completions"
    stream: Callable[
        ["Model", "Context", Optional["StreamOptions"]],
        "AssistantMessageEventStream",
    ]  # 流式调用函数
    streamSimple: Callable[
        ["Model", "Context", Optional["SimpleStreamOptions"]],
        "AssistantMessageEventStream",
    ]  # 简化流式调用函数（支持 reasoning 参数）


# 全局 API 提供商注册表：api -> ApiProvider
_api_provider_registry: Dict[str, ApiProvider] = {}


def register_api_provider(
    provider: ApiProvider,
    source_id: Optional[str] = None,
) -> None:
    """
    注册 API 提供商。

    Args:
        provider: 要注册的 API 提供商
        source_id: 可选的来源标识符，用于追踪注册来源
    """
    _api_provider_registry[provider.api] = provider


def get_api_provider(api: str) -> Optional[ApiProvider]:
    """
    根据 API 标识符获取提供商。

    Args:
        api: API 标识符

    Returns:
        找到则返回 ApiProvider，否则返回 None
    """
    return _api_provider_registry.get(api)


def get_api_providers() -> List[ApiProvider]:
    """
    获取所有已注册的 API 提供商。

    Returns:
        所有已注册的 ApiProvider 列表
    """
    return list(_api_provider_registry.values())


def unregister_api_providers(source_id: str) -> None:
    """
    注销来自特定来源的所有 API 提供商。

    Args:
        source_id: 要注销的来源标识符

    Note:
        当前实现未支持 source_id 追踪，此函数为空操作。
    """
    # 注意：Python 中需要单独追踪 source_id
    # 为简化实现，当前不支持 source_id 追踪
    pass


def clear_api_providers() -> None:
    """清空所有已注册的 API 提供商。"""
    _api_provider_registry.clear()

