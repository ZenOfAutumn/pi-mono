"""
providers/simple_options.py 模块的单元测试。

测试目标：
1. 验证 build_base_options 构建正确的选项
2. 验证 clamp_reasoning 限制 reasoning 级别
3. 验证 adjust_max_tokens_for_thinking 计算 token 预算
"""

import pytest

from src.providers.simple_options import (
    build_base_options,
    clamp_reasoning,
    adjust_max_tokens_for_thinking,
)
from src.core_types import Model, ModelCost


class TestBuildBaseOptions:
    """测试 build_base_options 函数。"""

    def test_builds_options_from_simple_options(self):
        """
        测试从简单选项构建基础选项。
        预期结果：所有字段正确映射。
        """
        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
            maxTokens=4096,
        )
        simple_options = {
            "temperature": 0.7,
            "maxTokens": 2048,
            "apiKey": "test-key",
        }

        result = build_base_options(model, simple_options)

        assert result["temperature"] == 0.7
        assert result["maxTokens"] == 2048
        assert result["apiKey"] == "test-key"

    def test_uses_model_max_tokens_as_default(self):
        """
        测试使用模型的 maxTokens 作为默认值。
        预期结果：当 options 存在且没有 maxTokens 时使用模型的值（限制为 32000）。
        """
        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
            maxTokens=4096,
        )

        # 当传入包含其他字段但没有 maxTokens 的 options 时，会使用模型的 maxTokens
        result = build_base_options(model, {"temperature": 0.7})

        assert result["maxTokens"] == 4096

    def test_caps_max_tokens_at_32000(self):
        """
        测试 maxTokens 上限为 32000。
        预期结果：模型 maxTokens 超过 32000 时被限制。
        """
        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
            maxTokens=100000,
        )

        # 当传入包含其他字段但没有 maxTokens 的 options 时，会使用模型的 maxTokens（限制为 32000）
        result = build_base_options(model, {"temperature": 0.7})

        assert result["maxTokens"] == 32000

    def test_api_key_parameter_takes_precedence(self):
        """
        测试 apiKey 参数优先于 options 中的值。
        预期结果：使用传入的 apiKey 参数。
        """
        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
        )
        simple_options = {
            "apiKey": "options-key",
        }

        result = build_base_options(model, simple_options, api_key="param-key")

        assert result["apiKey"] == "param-key"

    def test_handles_none_options(self):
        """
        测试处理 None 选项。
        预期结果：返回有效的选项字典。
        """
        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
        )

        result = build_base_options(model, None)

        assert isinstance(result, dict)


class TestClampReasoning:
    """测试 clamp_reasoning 函数。"""

    def test_xhigh_clamped_to_high(self):
        """
        测试 xhigh 被限制为 high。
        预期结果："xhigh" 返回 "high"。
        """
        assert clamp_reasoning("xhigh") == "high"

    def test_other_levels_unchanged(self):
        """
        测试其他级别不变。
        预期结果：minimal, low, medium, high 原样返回。
        """
        assert clamp_reasoning("minimal") == "minimal"
        assert clamp_reasoning("low") == "low"
        assert clamp_reasoning("medium") == "medium"
        assert clamp_reasoning("high") == "high"

    def test_none_returns_none(self):
        """
        测试 None 返回 None。
        预期结果：None 原样返回。
        """
        assert clamp_reasoning(None) is None


class TestAdjustMaxTokensForThinking:
    """测试 adjust_max_tokens_for_thinking 函数。"""

    def test_adds_thinking_budget(self):
        """
        测试添加 thinking 预算。
        预期结果：maxTokens 增加了 thinking 预算。
        """
        base_max_tokens = 4096
        model_max_tokens = 16384
        reasoning_level = "medium"  # 默认 8192 预算

        max_tokens, thinking_budget = adjust_max_tokens_for_thinking(
            base_max_tokens, model_max_tokens, reasoning_level
        )

        # maxTokens = min(4096 + 8192, 16384) = 12288
        assert max_tokens == 12288
        assert thinking_budget == 8192

    def test_respects_model_max_tokens(self):
        """
        测试遵守模型最大 token 限制。
        预期结果：不超过模型的 contextWindow。
        """
        base_max_tokens = 4096
        model_max_tokens = 8192  # 较小
        reasoning_level = "high"  # 默认 16384 预算

        max_tokens, thinking_budget = adjust_max_tokens_for_thinking(
            base_max_tokens, model_max_tokens, reasoning_level
        )

        # maxTokens 不会超过 model_max_tokens
        assert max_tokens <= model_max_tokens

    def test_different_reasoning_levels(self):
        """
        测试不同 reasoning 级别的预算。
        预期结果：不同级别有不同的 thinking 预算。
        """
        base_max_tokens = 4096
        model_max_tokens = 65536

        # minimal: 1024
        _, budget_minimal = adjust_max_tokens_for_thinking(
            base_max_tokens, model_max_tokens, "minimal"
        )
        assert budget_minimal == 1024

        # low: 2048
        _, budget_low = adjust_max_tokens_for_thinking(
            base_max_tokens, model_max_tokens, "low"
        )
        assert budget_low == 2048

        # high: 16384
        _, budget_high = adjust_max_tokens_for_thinking(
            base_max_tokens, model_max_tokens, "high"
        )
        assert budget_high == 16384

    def test_custom_budgets(self):
        """
        测试自定义预算。
        预期结果：使用传入的自定义预算。
        """
        base_max_tokens = 4096
        model_max_tokens = 32768
        reasoning_level = "medium"
        custom_budgets = {
            "minimal": 512,
            "low": 1024,
            "medium": 4096,
            "high": 8192,
        }

        max_tokens, thinking_budget = adjust_max_tokens_for_thinking(
            base_max_tokens, model_max_tokens, reasoning_level, custom_budgets
        )

        assert thinking_budget == 4096

    def test_adjusts_thinking_budget_when_exceeds_limit(self):
        """
        测试当 thinking 预算超过限制时调整。
        预期结果：thinking 预算被减少以留出最小输出空间。
        """
        base_max_tokens = 100
        model_max_tokens = 100
        reasoning_level = "high"  # 16384 预算，但模型只有 100

        max_tokens, thinking_budget = adjust_max_tokens_for_thinking(
            base_max_tokens, model_max_tokens, reasoning_level
        )

        # 应该留出至少 1024 的输出空间
        # 但由于模型只有 100 tokens，thinking_budget 会被调整
        assert max_tokens == 100
        # thinking_budget = max(0, 100 - 1024) = 0
        assert thinking_budget >= 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

