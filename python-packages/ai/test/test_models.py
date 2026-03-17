"""
models.py 模块的单元测试。

测试目标：
1. 验证模型注册和查询功能
2. 验证成本计算功能
3. 验证 supports_xhigh 和 models_are_equal 辅助函数
"""

import pytest
from src.models import (
    register_models,
    get_model,
    get_providers,
    get_models,
    calculate_cost,
    supports_xhigh,
    models_are_equal,
)
from src.core_types import Model, ModelCost, Usage


class TestRegisterModels:
    """测试 register_models 函数。"""

    def test_registers_models(self):
        """
        测试注册模型字典。
        预期结果：模型被成功注册。
        """
        models = {
            "openai": {
                "gpt-4": Model(
                    id="gpt-4",
                    name="GPT-4",
                    api="openai-responses",
                    provider="openai",
                ),
            }
        }

        register_models(models)

        model = get_model("openai", "gpt-4")
        assert model is not None
        assert model.id == "gpt-4"

    def test_merges_models(self):
        """
        测试合并模型注册。
        预期结果：多次注册合并到同一提供商。
        """
        models1 = {
            "openai": {
                "gpt-4": Model(
                    id="gpt-4",
                    name="GPT-4",
                    api="openai-responses",
                    provider="openai",
                ),
            }
        }
        models2 = {
            "openai": {
                "gpt-4o": Model(
                    id="gpt-4o",
                    name="GPT-4o",
                    api="openai-responses",
                    provider="openai",
                ),
            }
        }

        register_models(models1)
        register_models(models2)

        models = get_models("openai")
        model_ids = [m.id for m in models]
        assert "gpt-4" in model_ids
        assert "gpt-4o" in model_ids


class TestGetModel:
    """测试 get_model 函数。"""

    def test_returns_none_for_unknown_provider(self):
        """
        测试获取未知提供商的模型。
        预期结果：返回 None。
        """
        result = get_model("unknown-provider", "model-id")
        assert result is None

    def test_returns_none_for_unknown_model(self):
        """
        测试获取已知提供商的未知模型。
        预期结果：返回 None。
        """
        register_models({"test-provider": {}})

        result = get_model("test-provider", "unknown-model")
        assert result is None

    def test_returns_registered_model(self):
        """
        测试获取已注册的模型。
        预期结果：返回正确的模型。
        """
        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
        )
        register_models({"test-provider": {"test-model": model}})

        result = get_model("test-provider", "test-model")
        assert result is not None
        assert result.id == "test-model"


class TestGetProviders:
    """测试 get_providers 函数。"""

    def test_returns_empty_list_when_no_models(self):
        """
        测试没有注册模型时返回空列表。
        预期结果：返回空列表。
        """
        # 由于是全局注册表，我们只能测试返回的是列表
        result = get_providers()
        assert isinstance(result, list)

    def test_returns_provider_names(self):
        """
        测试返回提供商名称列表。
        预期结果：返回所有提供商名称。
        """
        register_models({
            "provider-a": {},
            "provider-b": {},
        })

        result = get_providers()
        assert "provider-a" in result
        assert "provider-b" in result


class TestGetModels:
    """测试 get_models 函数。"""

    def test_returns_empty_list_for_unknown_provider(self):
        """
        测试获取未知提供商的模型列表。
        预期结果：返回空列表。
        """
        result = get_models("unknown-provider")
        assert result == []

    def test_returns_all_models_for_provider(self):
        """
        测试获取提供商的所有模型。
        预期结果：返回该提供商的所有模型。
        """
        model1 = Model(
            id="model-1",
            name="Model 1",
            api="test-api",
            provider="test-provider",
        )
        model2 = Model(
            id="model-2",
            name="Model 2",
            api="test-api",
            provider="test-provider",
        )
        register_models({"test-provider": {"model-1": model1, "model-2": model2}})

        result = get_models("test-provider")
        assert len(result) >= 2
        model_ids = [m.id for m in result]
        assert "model-1" in model_ids
        assert "model-2" in model_ids


class TestCalculateCost:
    """测试 calculate_cost 函数。"""

    def test_calculates_cost_correctly(self):
        """
        测试正确计算成本。
        预期结果：成本按照模型定价正确计算。
        """
        model = Model(
            id="test-model",
            name="Test Model",
            api="test-api",
            provider="test-provider",
            cost=ModelCost(
                input=10.0,  # $10/M tokens
                output=30.0,  # $30/M tokens
                cacheRead=1.0,  # $1/M tokens
                cacheWrite=5.0,  # $5/M tokens
            ),
        )
        usage = Usage(
            input=100000,  # 100K tokens
            output=50000,  # 50K tokens
            cacheRead=20000,  # 20K tokens
            cacheWrite=10000,  # 10K tokens
        )

        calculate_cost(model, usage)

        # input: 100K * $10/M = $1.0
        assert usage.cost.input == 1.0
        # output: 50K * $30/M = $1.5
        assert usage.cost.output == 1.5
        # cacheRead: 20K * $1/M = $0.02
        assert usage.cost.cacheRead == 0.02
        # cacheWrite: 10K * $5/M = $0.05
        assert usage.cost.cacheWrite == 0.05
        # total: $2.57
        assert usage.cost.total == pytest.approx(2.57, rel=1e-2)

    def test_calculates_zero_cost(self):
        """
        测试零成本计算。
        预期结果：零使用量返回零成本。
        """
        model = Model(
            id="free-model",
            name="Free Model",
            api="test-api",
            provider="test-provider",
            cost=ModelCost(),
        )
        usage = Usage()

        calculate_cost(model, usage)

        assert usage.cost.total == 0.0


class TestSupportsXhigh:
    """测试 supports_xhigh 函数。"""

    def test_supports_gpt_52(self):
        """
        测试 GPT-5.2 支持 xhigh。
        预期结果：返回 True。
        """
        model = Model(
            id="gpt-5.2-mini",
            name="GPT-5.2 Mini",
            api="openai-responses",
            provider="openai",
        )

        assert supports_xhigh(model) is True

    def test_supports_gpt_53(self):
        """
        测试 GPT-5.3 支持 xhigh。
        预期结果：返回 True。
        """
        model = Model(
            id="gpt-5.3-pro",
            name="GPT-5.3 Pro",
            api="openai-responses",
            provider="openai",
        )

        assert supports_xhigh(model) is True

    def test_supports_anthropic_opus_46(self):
        """
        测试 Anthropic Opus 4.6 支持 xhigh。
        预期结果：返回 True。
        """
        model = Model(
            id="claude-opus-4-6-20250514",
            name="Claude Opus 4.6",
            api="anthropic-messages",
            provider="anthropic",
        )

        assert supports_xhigh(model) is True

    def test_not_supports_regular_model(self):
        """
        测试普通模型不支持 xhigh。
        预期结果：返回 False。
        """
        model = Model(
            id="gpt-4o",
            name="GPT-4o",
            api="openai-responses",
            provider="openai",
        )

        assert supports_xhigh(model) is False


class TestModelsAreEqual:
    """测试 models_are_equal 函数。"""

    def test_equal_models(self):
        """
        测试相等的模型。
        预期结果：返回 True。
        """
        model1 = Model(
            id="gpt-4",
            name="GPT-4",
            api="openai-responses",
            provider="openai",
        )
        model2 = Model(
            id="gpt-4",
            name="GPT-4",
            api="openai-responses",
            provider="openai",
        )

        assert models_are_equal(model1, model2) is True

    def test_different_ids(self):
        """
        测试不同 ID 的模型。
        预期结果：返回 False。
        """
        model1 = Model(
            id="gpt-4",
            name="GPT-4",
            api="openai-responses",
            provider="openai",
        )
        model2 = Model(
            id="gpt-4o",
            name="GPT-4o",
            api="openai-responses",
            provider="openai",
        )

        assert models_are_equal(model1, model2) is False

    def test_different_providers(self):
        """
        测试不同提供商的模型。
        预期结果：返回 False。
        """
        model1 = Model(
            id="gpt-4",
            name="GPT-4",
            api="openai-responses",
            provider="openai",
        )
        model2 = Model(
            id="gpt-4",
            name="GPT-4",
            api="azure-openai-responses",
            provider="azure-openai-responses",
        )

        assert models_are_equal(model1, model2) is False

    def test_none_models(self):
        """
        测试 None 模型。
        预期结果：返回 False。
        """
        model = Model(
            id="gpt-4",
            name="GPT-4",
            api="openai-responses",
            provider="openai",
        )

        assert models_are_equal(None, model) is False
        assert models_are_equal(model, None) is False
        assert models_are_equal(None, None) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

