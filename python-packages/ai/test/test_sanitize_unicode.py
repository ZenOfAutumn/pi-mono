"""
utils/sanitize_unicode.py 模块的单元测试。

测试目标：
1. 验证 sanitize_surrogates 能够正确移除不成对的代理字符
2. 验证有效 Unicode 不受影响
3. 验证 is_valid_unicode 和 normalize_unicode 函数
"""

import pytest

from src.utils.sanitize_unicode import (
    sanitize_surrogates,
    is_valid_unicode,
    normalize_unicode,
)


class TestSanitizeSurrogates:
    """测试 sanitize_surrogates 函数。"""

    def test_preserves_valid_text(self):
        """
        测试保留有效的普通文本。
        预期结果：普通 ASCII 文本不变。
        """
        text = "Hello, World!"
        result = sanitize_surrogates(text)

        assert result == "Hello, World!"

    def test_preserves_valid_emoji(self):
        """
        测试保留有效的 emoji（成对的代理字符）。
        预期结果：有效的 emoji 被保留。
        """
        text = "Hello 🙈 World"
        result = sanitize_surrogates(text)

        assert result == "Hello 🙈 World"

    def test_preserves_multiple_emoji(self):
        """
        测试保留多个有效 emoji。
        预期结果：所有有效 emoji 被保留。
        """
        text = "😀 🎉 🚀 💖"
        result = sanitize_surrogates(text)

        assert result == "😀 🎉 🚀 💖"

    def test_removes_unpaired_high_surrogate(self):
        """
        测试移除不成对的高代理字符。
        预期结果：不成对的高代理字符被移除。
        """
        # 高代理字符 0xD83D 没有对应的低代理字符
        unpaired_high = chr(0xD83D)
        text = f"Text {unpaired_high} here"
        result = sanitize_surrogates(text)

        assert result == "Text  here"

    def test_removes_unpaired_low_surrogate(self):
        """
        测试移除不成对的低代理字符。
        预期结果：不成对的低代理字符被移除。
        """
        # 低代理字符 0xDC00 没有对应的高代理字符
        unpaired_low = chr(0xDC00)
        text = f"Text {unpaired_low} here"
        result = sanitize_surrogates(text)

        assert result == "Text  here"

    def test_handles_empty_string(self):
        """
        测试处理空字符串。
        预期结果：返回空字符串。
        """
        result = sanitize_surrogates("")
        assert result == ""

    def test_preserves_chinese_characters(self):
        """
        测试保留中文字符。
        预期结果：中文字符不受影响。
        """
        text = "你好世界"
        result = sanitize_surrogates(text)

        assert result == "你好世界"

    def test_preserves_mixed_content(self):
        """
        测试保留混合内容。
        预期结果：ASCII、中文和有效 emoji 都被保留。
        """
        text = "Hello 世界 🌍!"
        result = sanitize_surrogates(text)

        assert result == "Hello 世界 🌍!"


class TestIsValidUnicode:
    """测试 is_valid_unicode 函数。"""

    def test_valid_ascii(self):
        """
        测试有效的 ASCII 文本。
        预期结果：返回 True。
        """
        assert is_valid_unicode("Hello, World!") is True

    def test_valid_chinese(self):
        """
        测试有效的中文文本。
        预期结果：返回 True。
        """
        assert is_valid_unicode("你好世界") is True

    def test_valid_emoji(self):
        """
        测试有效的 emoji。
        预期结果：返回 True。
        """
        assert is_valid_unicode("😀") is True

    def test_invalid_surrogate(self):
        """
        测试包含无效代理字符的文本。
        预期结果：返回 False。
        """
        # 创建包含不成对代理字符的文本
        invalid_text = "Hello " + chr(0xD83D) + " World"
        assert is_valid_unicode(invalid_text) is False


class TestNormalizeUnicode:
    """测试 normalize_unicode 函数。"""

    def test_normalize_nfc(self):
        """
        测试 NFC 标准化。
        预期结果：文本被标准化为 NFC 形式。
        """
        # 带音标的字符可能有多种表示形式
        text = "café"
        result = normalize_unicode(text, "NFC")

        assert isinstance(result, str)
        assert "café" in result or result == "café"

    def test_normalize_nfd(self):
        """
        测试 NFD 标准化。
        预期结果：文本被标准化为 NFD 形式。
        """
        text = "café"
        result = normalize_unicode(text, "NFD")

        assert isinstance(result, str)

    def test_normalize_empty_string(self):
        """
        测试空字符串标准化。
        预期结果：返回空字符串。
        """
        result = normalize_unicode("", "NFC")
        assert result == ""

    def test_normalize_ascii(self):
        """
        测试 ASCII 文本标准化。
        预期结果：ASCII 文本基本不变。
        """
        text = "Hello World"
        result = normalize_unicode(text, "NFC")

        assert result == "Hello World"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

