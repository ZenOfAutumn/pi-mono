"""
utils/json_parse.py 模块的单元测试。

测试目标：
1. 验证 parse_streaming_json 能够解析完整的 JSON
2. 验证能够解析部分 JSON（流式场景）
3. 验证无效 JSON 返回空对象
"""

import pytest

from src.utils.json_parse import (
    parse_streaming_json,
    extract_partial_string_value,
)


class TestParseStreamingJson:
    """测试 parse_streaming_json 函数。"""

    def test_parses_complete_json(self):
        """
        测试解析完整的 JSON 字符串。
        预期结果：返回正确解析的对象。
        """
        json_str = '{"name": "Alice", "age": 30}'
        result = parse_streaming_json(json_str)

        assert result == {"name": "Alice", "age": 30}

    def test_parses_empty_string(self):
        """
        测试解析空字符串。
        预期结果：返回空对象。
        """
        result = parse_streaming_json("")
        assert result == {}

    def test_parses_none(self):
        """
        测试解析 None。
        预期结果：返回空对象。
        """
        result = parse_streaming_json(None)
        assert result == {}

    def test_parses_whitespace_only(self):
        """
        测试解析仅包含空白字符的字符串。
        预期结果：返回空对象。
        """
        result = parse_streaming_json("   \n\t  ")
        assert result == {}

    def test_parses_incomplete_object(self):
        """
        测试解析不完整的 JSON 对象。
        预期结果：返回已解析的部分或空对象。
        """
        # 只有开始没有结束
        json_str = '{"name": "Alice"'
        result = parse_streaming_json(json_str)
        # 应该返回某种对象（可能是空的，也可能是部分解析的）
        assert isinstance(result, dict)

    def test_parses_incomplete_string_value(self):
        """
        测试解析不完整的字符串值。
        预期结果：返回包含部分值的对象。
        """
        json_str = '{"path": "/home/user/doc'
        result = parse_streaming_json(json_str)
        # 至少不应该崩溃
        assert isinstance(result, dict)

    def test_parses_nested_object(self):
        """
        测试解析嵌套对象。
        预期结果：正确解析嵌套结构。
        """
        json_str = '{"user": {"name": "Bob", "age": 25}, "active": true}'
        result = parse_streaming_json(json_str)

        assert result["user"]["name"] == "Bob"
        assert result["user"]["age"] == 25
        assert result["active"] is True

    def test_parses_array(self):
        """
        测试解析数组。
        预期结果：正确解析数组。
        """
        json_str = '{"items": [1, 2, 3]}'
        result = parse_streaming_json(json_str)

        assert result["items"] == [1, 2, 3]

    def test_handles_invalid_json(self):
        """
        测试处理无效 JSON。
        预期结果：返回空对象，不抛出异常。
        """
        json_str = 'not valid json at all'
        result = parse_streaming_json(json_str)

        assert result == {}


class TestExtractPartialStringValue:
    """测试 extract_partial_string_value 函数。"""

    def test_extracts_complete_string(self):
        """
        测试提取完整的字符串值。
        预期结果：返回正确的字符串值。
        """
        json_str = '{"path": "/home/user/file.txt"}'
        result = extract_partial_string_value(json_str, "path")

        assert result == "/home/user/file.txt"

    def test_extracts_partial_string(self):
        """
        测试提取部分字符串值。
        预期结果：返回已解析的部分字符串。
        """
        json_str = '{"path": "/home/user/doc'
        result = extract_partial_string_value(json_str, "path")

        # 应该返回部分值
        assert result == "/home/user/doc"

    def test_returns_none_for_missing_key(self):
        """
        测试不存在的键。
        预期结果：返回 None。
        """
        json_str = '{"name": "Alice"}'
        result = extract_partial_string_value(json_str, "age")

        assert result is None

    def test_handles_empty_json(self):
        """
        测试空 JSON 字符串。
        预期结果：返回 None。
        """
        result = extract_partial_string_value("", "key")
        assert result is None

    def test_extracts_multiple_keys(self):
        """
        测试从包含多个键的 JSON 中提取值。
        预期结果：正确提取指定键的值。
        """
        json_str = '{"name": "Alice", "path": "/home/alice", "age": 30}'

        name = extract_partial_string_value(json_str, "name")
        path = extract_partial_string_value(json_str, "path")

        assert name == "Alice"
        assert path == "/home/alice"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

