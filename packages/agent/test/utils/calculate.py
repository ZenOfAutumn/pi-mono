"""
Calculate tool for testing.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.types import (
    AgentTool,
    AgentToolResult,
    TextContent,
)


def calculate(expression: str) -> AgentToolResult:
    """
    Evaluate a mathematical expression.

    Args:
        expression: The mathematical expression to evaluate

    Returns:
        AgentToolResult with the calculated result
    """
    try:
        # Safe evaluation using a restricted environment
        allowed_names = {
            "abs": abs,
            "min": min,
            "max": max,
            "sum": sum,
            "pow": pow,
            "round": round,
        }
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return AgentToolResult(
            content=[TextContent(text=f"{expression} = {result}")],
            details=None,
        )
    except Exception as e:
        raise RuntimeError(str(e))


calculate_tool = AgentTool(
    name="calculate",
    label="Calculator",
    description="Evaluate mathematical expressions",
    parameters={
        "type": "object",
        "properties": {
            "expression": {
                "type": "string",
                "description": "The mathematical expression to evaluate"
            }
        },
        "required": ["expression"]
    },
    execute=lambda tool_call_id, params, signal, on_update: calculate(params["expression"]),
)

