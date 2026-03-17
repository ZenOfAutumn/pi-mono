"""
使用 JSON Schema 进行工具参数验证。

本模块提供针对工具调用参数的验证功能，
根据其 JSON Schema 定义进行验证。
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any, List

if TYPE_CHECKING:
    from ..core_types import Tool, ToolCall


def validate_tool_call(tools: List["Tool"], tool_call: "ToolCall") -> Any:
    """
    根据名称查找工具并验证工具调用参数。

    Args:
        tools: 工具定义数组
        tool_call: 来自 LLM 的工具调用

    Returns:
        验证后的参数

    Raises:
        ValueError: 如果工具未找到或验证失败
    """
    tool = next((t for t in tools if t.name == tool_call.name), None)
    if not tool:
        raise ValueError(f'Tool "{tool_call.name}" not found')
    return validate_tool_arguments(tool, tool_call)


def validate_tool_arguments(tool: "Tool", tool_call: "ToolCall") -> Any:
    """
    根据工具的 JSON Schema 验证工具调用参数。

    Args:
        tool: 带有 JSON Schema 的工具定义
        tool_call: 来自 LLM 的工具调用

    Returns:
        验证后（可能经过类型转换）的参数

    Raises:
        ValueError: 验证失败时返回格式化的错误消息
    """
    try:
        import jsonschema
        from jsonschema import validate, ValidationError
    except ImportError:
        # jsonschema 未安装，跳过验证
        return tool_call.arguments

    # 克隆参数，避免验证器修改原始数据
    args = dict(tool_call.arguments)

    try:
        validate(instance=args, schema=tool.parameters)
        return args
    except ValidationError as e:
        # 格式化验证错误信息
        path = ".".join(str(p) for p in e.absolute_path) if e.absolute_path else "root"
        error_msg = f"  - {path}: {e.message}"

        full_error_msg = (
            f'Validation failed for tool "{tool_call.name}":\n'
            f"{error_msg}\n\n"
            f"Received arguments:\n{json.dumps(tool_call.arguments, indent=2)}"
        )

        raise ValueError(full_error_msg)

