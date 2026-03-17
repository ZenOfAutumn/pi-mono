"""
utils/validation.py 模块的单元测试。

测试目标：
1. 验证 validate_tool_call 能够正确查找工具并验证参数
2. 验证 validate_tool_arguments 能够正确验证参数
3. 验证验证失败时抛出正确的错误信息
"""

from src.core_types import Tool, ToolCall

import pytest
from src.utils.validation import validate_tool_call, validate_tool_arguments


class TestValidateToolCall:
    """测试 validate_tool_call 函数。"""

    def test_validates_existing_tool(self):
        """
        测试验证存在的工具调用。
        预期结果：参数验证通过，返回验证后的参数。
        """
        tools = [
            Tool(
                name="calculate",
                description="Calculate expression",
                parameters={
                    "type": "object",
                    "properties": {
                        "expression": {"type": "string"},
                    },
                    "required": ["expression"],
                },
            )
        ]

        tool_call = ToolCall(
            id="call-123",
            name="calculate",
            arguments={"expression": "1 + 2"},
        )

        result = validate_tool_call(tools, tool_call)
        assert result == {"expression": "1 + 2"}

    def test_raises_for_unknown_tool(self):
        """
        测试调用不存在的工具。
        预期结果：抛出 ValueError，说明工具不存在。
        """
        tools = [
            Tool(name="calculate", description="Calculate"),
        ]

        tool_call = ToolCall(
            id="call-123",
            name="unknown_tool",
            arguments={},
        )

        with pytest.raises(ValueError) as exc_info:
            validate_tool_call(tools, tool_call)

        assert 'Tool "unknown_tool" not found' in str(exc_info.value)


class TestValidateToolArguments:
    """测试 validate_tool_arguments 函数。"""

    def test_validates_correct_arguments(self):
        """
        测试验证正确的参数。
        预期结果：参数验证通过。
        """
        tool = Tool(
            name="calculate",
            description="Calculate expression",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {"type": "string"},
                    "precision": {"type": "integer"},
                },
                "required": ["expression"],
            },
        )

        tool_call = ToolCall(
            id="call-123",
            name="calculate",
            arguments={"expression": "1 + 2", "precision": 2},
        )

        result = validate_tool_arguments(tool, tool_call)
        assert result["expression"] == "1 + 2"
        assert result["precision"] == 2

    def test_validates_with_missing_optional_field(self):
        """
        测试缺少可选字段的参数。
        预期结果：验证通过，可选字段不在结果中。
        """
        tool = Tool(
            name="greet",
            description="Greet someone",
            parameters={
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "greeting": {"type": "string"},
                },
                "required": ["name"],
            },
        )

        tool_call = ToolCall(
            id="call-456",
            name="greet",
            arguments={"name": "World"},
        )

        result = validate_tool_arguments(tool, tool_call)
        assert result["name"] == "World"
        assert "greeting" not in result

    def test_raises_for_missing_required_field(self):
        """
        测试缺少必填字段。
        预期结果：抛出 ValueError，说明缺少必填字段。
        """
        tool = Tool(
            name="calculate",
            description="Calculate expression",
            parameters={
                "type": "object",
                "properties": {
                    "expression": {"type": "string"},
                },
                "required": ["expression"],
            },
        )

        tool_call = ToolCall(
            id="call-789",
            name="calculate",
            arguments={},
        )

        with pytest.raises(ValueError) as exc_info:
            validate_tool_arguments(tool, tool_call)

        error_msg = str(exc_info.value)
        assert 'Validation failed for tool "calculate"' in error_msg

    def test_validates_empty_schema(self):
        """
        测试空 schema 的验证。
        预期结果：空参数也能通过验证。
        """
        tool = Tool(
            name="noop",
            description="No operation",
            parameters={"type": "object", "properties": {}},
        )

        tool_call = ToolCall(
            id="call-000",
            name="noop",
            arguments={},
        )

        result = validate_tool_arguments(tool, tool_call)
        assert result == {}

    def test_validates_with_enum(self):
        """
        测试带有枚举值的参数验证。
        预期结果：枚举值正确验证。
        """
        tool = Tool(
            name="set_mode",
            description="Set operation mode",
            parameters={
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["fast", "slow", "balanced"],
                    },
                },
                "required": ["mode"],
            },
        )

        tool_call = ToolCall(
            id="call-111",
            name="set_mode",
            arguments={"mode": "fast"},
        )

        result = validate_tool_arguments(tool, tool_call)
        assert result["mode"] == "fast"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

