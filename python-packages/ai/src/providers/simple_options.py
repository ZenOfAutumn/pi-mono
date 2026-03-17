"""
统一推理接口的简化选项工具。

本模块提供构建和映射简化流式选项到
提供商特定选项的功能。
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Tuple, cast

if TYPE_CHECKING:
    from ..core_types import Model, SimpleStreamOptions, StreamOptions, ThinkingBudgets, ThinkingLevel


def build_base_options(
    model: "Model",
    options: Optional["SimpleStreamOptions"] = None,
    api_key: Optional[str] = None,
) -> "StreamOptions":
    """
    从简化选项构建基础流式选项。

    Args:
        model: 使用的模型
        options: 可选的简化流式选项
        api_key: 可选的 API 密钥

    Returns:
        流式选项字典
    """
    result: "StreamOptions" = {}

    if options:
        if "temperature" in options:
            result["temperature"] = options["temperature"]
        if "maxTokens" in options:
            result["maxTokens"] = options["maxTokens"]
        elif model.maxTokens > 0:
            # 如果未指定 maxTokens，使用模型默认值（最大 32000）
            result["maxTokens"] = min(model.maxTokens, 32000)
        if "signal" in options:
            result["signal"] = options["signal"]
        if "cacheRetention" in options:
            result["cacheRetention"] = options["cacheRetention"]
        if "sessionId" in options:
            result["sessionId"] = options["sessionId"]
        if "headers" in options:
            result["headers"] = options["headers"]
        if "onPayload" in options:
            result["onPayload"] = options["onPayload"]
        if "maxRetryDelayMs" in options:
            result["maxRetryDelayMs"] = options["maxRetryDelayMs"]
        if "metadata" in options:
            result["metadata"] = options["metadata"]

    if api_key or (options and "apiKey" in options):
        result["apiKey"] = api_key or (options.get("apiKey") if options else None)

    return result


def clamp_reasoning(
    effort: Optional["ThinkingLevel"],
) -> Optional[str]:
    """
    限制推理级别，将 xhigh 转换为 high。

    Args:
        effort: 推理级别

    Returns:
        限制后的推理级别
    """
    if effort is None:
        return None
    return "high" if effort == "xhigh" else effort


def adjust_max_tokens_for_thinking(
    base_max_tokens: int,
    model_max_tokens: int,
    reasoning_level: "ThinkingLevel",
    custom_budgets: Optional["ThinkingBudgets"] = None,
) -> Tuple[int, int]:
    """
    调整 max tokens 以考虑思考预算。

    Args:
        base_max_tokens: 输出的基础最大 token 数
        model_max_tokens: 模型的最大 token 限制
        reasoning_level: 推理级别
        custom_budgets: 可选的自定义思考 token 预算

    Returns:
        元组 (调整后的 max_tokens, 思考预算)
    """
    # 默认思考预算配置
    default_budgets: "ThinkingBudgets" = {
        "minimal": 1024,
        "low": 2048,
        "medium": 8192,
        "high": 16384,
    }

    budgets = {**default_budgets, **(custom_budgets or {})}

    min_output_tokens = 1024
    level = cast(str, clamp_reasoning(reasoning_level))

    thinking_budget = budgets.get(level, 8192)  # type: ignore
    max_tokens = min(base_max_tokens + thinking_budget, model_max_tokens)

    # 如果总 token 不足以分配思考预算，减少思考预算
    if max_tokens <= thinking_budget:
        thinking_budget = max(0, max_tokens - min_output_tokens)

    return max_tokens, thinking_budget

