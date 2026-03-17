"""
流式部分 JSON 解析工具。

本模块提供在流式传输过程中解析可能不完整 JSON 的功能，
适用于渐进式工具参数解析。
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional


def parse_streaming_json(partial_json: Optional[str]) -> Any:
    """
    尝试解析流式传输中可能不完整的 JSON。

    始终返回有效对象，即使 JSON 不完整。
    适用于渐进式解析工具调用参数。

    Args:
        partial_json: 来自流式传输的部分 JSON 字符串

    Returns:
        解析后的对象，解析失败则返回空对象
    """
    if not partial_json or not partial_json.strip():
        return {}

    # 首先尝试标准解析（完整 JSON 最快）
    try:
        return json.loads(partial_json)
    except json.JSONDecodeError:
        pass

    # 尝试修复不完整的 JSON
    try:
        fixed = _fix_incomplete_json(partial_json)
        return json.loads(fixed)
    except (json.JSONDecodeError, ValueError):
        pass

    # 所有解析尝试失败，返回空对象
    return {}


def _fix_incomplete_json(json_str: str) -> str:
    """
    通过添加缺失的闭合字符尝试修复不完整的 JSON。

    Args:
        json_str: 不完整的 JSON 字符串

    Returns:
        可能已修复的 JSON 字符串

    Raises:
        ValueError: 如果 JSON 无法修复
    """
    # 统计括号和大括号
    open_braces = json_str.count("{") - json_str.count("}")
    open_brackets = json_str.count("[") - json_str.count("]")
    open_quotes = json_str.count('"') % 2

    result = json_str

    # 闭合未闭合的字符串
    if open_quotes:
        result += '"'

    # 闭合未闭合的数组和对象
    # 需要根据上下文按正确顺序闭合
    # 为简化处理，直接添加闭合字符
    result += "]" * open_brackets + "}" * open_braces

    return result


def extract_partial_string_value(partial_json: str, key: str) -> Optional[str]:
    """
    从不完整的 JSON 中提取某个键的部分字符串值。

    适用于在流式传输中显示渐进式的文件路径或其他字符串。

    Args:
        partial_json: 部分 JSON 字符串
        key: 要提取的键

    Returns:
        部分字符串值或 None
    """
    # 匹配 "key": "value（可能不完整）的模式
    pattern = rf'"{key}"\s*:\s*"([^"]*)"'
    match = re.search(pattern, partial_json)
    if match:
        return match.group(1)

    # 尝试匹配不完整的字符串值
    pattern = rf'"{key}"\s*:\s*"([^"]*)$'
    match = re.search(pattern, partial_json)
    if match:
        return match.group(1)

    return None

