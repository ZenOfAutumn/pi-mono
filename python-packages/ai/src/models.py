"""
模型注册和管理函数。

本模块提供查询和管理 LLM 模型的功能，
包括成本计算。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Dict, List, Optional, TypeVar

if TYPE_CHECKING:
    from .core_types import Model, Usage

# 类型变量：API 标识符（受 str 约束）
TApi = TypeVar("TApi", bound=str)


# 全局模型注册表：provider -> model_id -> Model
_model_registry: Dict[str, Dict[str, "Model"]] = {}


def register_models(models: Dict[str, Dict[str, "Model"]]) -> None:
    """
    从模型字典注册模型。

    Args:
        models: 字典，映射提供商名称到模型字典
                格式：{ "provider": { "model_id": Model, ... }, ... }
    """
    global _model_registry
    for provider, provider_models in models.items():
        if provider not in _model_registry:
            _model_registry[provider] = {}
        _model_registry[provider].update(provider_models)


def get_model(provider: str, model_id: str) -> Optional["Model"]:
    """
    根据提供商和模型 ID 获取模型。

    Args:
        provider: 提供商名称
        model_id: 模型 ID

    Returns:
        找到则返回 Model，否则返回 None
    """
    provider_models = _model_registry.get(provider)
    if provider_models:
        return provider_models.get(model_id)
    return None


def get_providers() -> List[str]:
    """
    获取所有已注册的提供商名称。

    Returns:
        提供商名称列表
    """
    return list(_model_registry.keys())


def get_models(provider: str) -> List["Model"]:
    """
    获取指定提供商的所有模型。

    Args:
        provider: 提供商名称

    Returns:
        该提供商的模型列表
    """
    provider_models = _model_registry.get(provider)
    return list(provider_models.values()) if provider_models else []


def calculate_cost(model: "Model", usage: "Usage") -> "Usage":
    """
    根据模型定价和使用量计算成本。

    Args:
        model: 包含定价信息的模型
        usage: 要计算成本的使用量信息

    Returns:
        更新了成本信息的使用量对象
    """
    # 成本单位：$/百万 token
    usage.cost.input = (model.cost.input / 1000000) * usage.input
    usage.cost.output = (model.cost.output / 1000000) * usage.output
    usage.cost.cacheRead = (model.cost.cacheRead / 1000000) * usage.cacheRead
    usage.cost.cacheWrite = (model.cost.cacheWrite / 1000000) * usage.cacheWrite
    usage.cost.total = (
        usage.cost.input
        + usage.cost.output
        + usage.cost.cacheRead
        + usage.cost.cacheWrite
    )
    return usage.cost


def supports_xhigh(model: "Model") -> bool:
    """
    检查模型是否支持 xhigh 思考级别。

    当前支持的模型：
    - GPT-5.2 / GPT-5.3 / GPT-5.4 模型系列
    - Anthropic Messages API Opus 4.6 模型（xhigh 映射到 adaptive effort "max"）

    Args:
        model: 要检查的模型

    Returns:
        如果支持 xhigh 思考级别则返回 True
    """
    if "gpt-5.2" in model.id or "gpt-5.3" in model.id or "gpt-5.4" in model.id:
        return True

    if model.api == "anthropic-messages":
        return "opus-4-6" in model.id or "opus-4.6" in model.id

    return False


def models_are_equal(
    a: Optional["Model"],
    b: Optional["Model"],
) -> bool:
    """
    通过比较 id 和 provider 判断两个模型是否相等。

    Args:
        a: 第一个模型
        b: 第二个模型

    Returns:
        如果模型相等返回 True，任一为 None 返回 False
    """
    if not a or not b:
        return False
    return a.id == b.id and a.provider == b.provider

