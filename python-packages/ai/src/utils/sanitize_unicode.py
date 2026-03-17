"""
Unicode 清理工具。

本模块提供移除不成对 Unicode 代理字符的功能，
这些字符会导致许多 API 提供商的 JSON 序列化错误。
"""

from __future__ import annotations

import re


def sanitize_surrogates(text: str) -> str:
    """
    移除字符串中不成对的 Unicode 代理字符。

    不成对的代理字符（高位代理 0xD800-0xDBFF 没有匹配的低位代理
    0xDC00-0xDFFF，或反之）会导致许多 API 提供商的 JSON 序列化错误。

    有效的 emoji 和其他基本多文种平面之外的字符使用正确配对的代理，
    不会受此函数影响。

    Args:
        text: 要清理的文本

    Returns:
        移除了不成对代理字符的清理后文本

    Examples:
        >>> sanitize_surrogates("Hello 🙈 World")
        'Hello 🙈 World'  # 有效的 emoji 被保留

        >>> unpaired = chr(0xD83D)  # 没有低位代理的高位代理
        >>> sanitize_surrogates(f"Text {unpaired} here")
        'Text  here'  # 不成对的代理被移除
    """
    # 替换不成对的高位代理（0xD800-0xDBFF 后面没有低位代理）
    # 替换不成对的低位代理（0xDC00-0xDFFF 前面没有高位代理）
    pattern = r"[\uD800-\uDBFF](?![\uDC00-\uDFFF])|(?<![\uD800-\uDBFF])[\uDC00-\uDFFF]"
    return re.sub(pattern, "", text)


def is_valid_unicode(text: str) -> bool:
    """
    检查字符串是否包含有效的 Unicode（没有不成对的代理字符）。

    Args:
        text: 要检查的文本

    Returns:
        如果字符串没有不成对的代理字符则返回 True
    """
    try:
        text.encode("utf-8", "strict")
        return True
    except UnicodeEncodeError:
        return False


def normalize_unicode(text: str, form: str = "NFC") -> str:
    """
    将 Unicode 规范化为标准形式。

    Args:
        text: 要规范化的文本
        form: 规范化形式（NFC, NFD, NFKC, NFKD）

    Returns:
        规范化后的文本
    """
    import unicodedata

    return unicodedata.normalize(form, text)

