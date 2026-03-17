"""
env_api_keys.py 模块的单元测试。

测试目标：
1. 验证 get_env_api_key 能够从环境变量获取 API Key
2. 验证不同提供商的环境变量映射
3. 验证特殊提供商的处理（如 Vertex AI、Bedrock）
"""

import pytest

from src.env_api_keys import get_env_api_key


class TestGetEnvApiKey:
    """测试 get_env_api_key 函数。"""

    def test_gets_openai_key(self, monkeypatch):
        """
        测试获取 OpenAI API Key。
        预期结果：从 OPENAI_API_KEY 环境变量获取。
        """
        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key-123")

        result = get_env_api_key("openai")
        assert result == "sk-test-key-123"

    def test_gets_anthropic_key(self, monkeypatch):
        """
        测试获取 Anthropic API Key。
        预期结果：从 ANTHROPIC_API_KEY 环境变量获取。
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")

        result = get_env_api_key("anthropic")
        assert result == "sk-ant-test"

    def test_anthropic_oauth_takes_precedence(self, monkeypatch):
        """
        测试 Anthropic OAuth Token 优先于 API Key。
        预期结果：优先返回 ANTHROPIC_OAUTH_TOKEN。
        """
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-key")
        monkeypatch.setenv("ANTHROPIC_OAUTH_TOKEN", "oauth-token-123")

        result = get_env_api_key("anthropic")
        assert result == "oauth-token-123"

    def test_gets_google_key(self, monkeypatch):
        """
        测试获取 Google API Key。
        预期结果：从 GEMINI_API_KEY 环境变量获取。
        """
        monkeypatch.setenv("GEMINI_API_KEY", "gemini-key-456")

        result = get_env_api_key("google")
        assert result == "gemini-key-456"

    def test_gets_groq_key(self, monkeypatch):
        """
        测试获取 Groq API Key。
        预期结果：从 GROQ_API_KEY 环境变量获取。
        """
        monkeypatch.setenv("GROQ_API_KEY", "gsk-test")

        result = get_env_api_key("groq")
        assert result == "gsk-test"

    def test_gets_xai_key(self, monkeypatch):
        """
        测试获取 xAI API Key。
        预期结果：从 XAI_API_KEY 环境变量获取。
        """
        monkeypatch.setenv("XAI_API_KEY", "xai-key-789")

        result = get_env_api_key("xai")
        assert result == "xai-key-789"

    def test_gets_openrouter_key(self, monkeypatch):
        """
        测试获取 OpenRouter API Key。
        预期结果：从 OPENROUTER_API_KEY 环境变量获取。
        """
        monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")

        result = get_env_api_key("openrouter")
        assert result == "sk-or-test"

    def test_returns_none_for_missing_key(self, monkeypatch):
        """
        测试缺少环境变量时返回 None。
        预期结果：返回 None。
        """
        # 确保环境变量不存在
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        result = get_env_api_key("openai")
        assert result is None

    def test_returns_none_for_unknown_provider(self, monkeypatch):
        """
        测试未知提供商返回 None。
        预期结果：返回 None。
        """
        result = get_env_api_key("unknown-provider")
        assert result is None

    def test_github_copilot_key_priority(self, monkeypatch):
        """
        测试 GitHub Copilot Key 优先级。
        预期结果：COPILOT_GITHUB_TOKEN 优先。
        """
        monkeypatch.setenv("GH_TOKEN", "gh-token")
        monkeypatch.setenv("GITHUB_TOKEN", "github-token")
        monkeypatch.setenv("COPILOT_GITHUB_TOKEN", "copilot-token")

        result = get_env_api_key("github-copilot")
        assert result == "copilot-token"

    def test_github_copilot_fallback_to_gh_token(self, monkeypatch):
        """
        测试 GitHub Copilot 回退到 GH_TOKEN。
        预期结果：使用 GH_TOKEN。
        """
        monkeypatch.delenv("COPILOT_GITHUB_TOKEN", raising=False)
        monkeypatch.setenv("GH_TOKEN", "gh-token-fallback")

        result = get_env_api_key("github-copilot")
        assert result == "gh-token-fallback"

    def test_bedrock_with_profile(self, monkeypatch):
        """
        测试 Bedrock 使用 AWS Profile。
        预期结果：返回 "<authenticated>"。
        """
        monkeypatch.setenv("AWS_PROFILE", "my-profile")
        monkeypatch.delenv("AWS_ACCESS_KEY_ID", raising=False)
        monkeypatch.delenv("AWS_SECRET_ACCESS_KEY", raising=False)

        result = get_env_api_key("amazon-bedrock")
        assert result == "<authenticated>"

    def test_bedrock_with_access_keys(self, monkeypatch):
        """
        测试 Bedrock 使用 AWS Access Keys。
        预期结果：返回 "<authenticated>"。
        """
        monkeypatch.delenv("AWS_PROFILE", raising=False)
        monkeypatch.setenv("AWS_ACCESS_KEY_ID", "AKIATEST")
        monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "secret123")

        result = get_env_api_key("amazon-bedrock")
        assert result == "<authenticated>"

    def test_bedrock_without_credentials(self, monkeypatch):
        """
        测试 Bedrock 没有凭证时返回 None。
        预期结果：返回 None。
        """
        # 清除所有 AWS 相关环境变量
        for key in [
            "AWS_PROFILE",
            "AWS_ACCESS_KEY_ID",
            "AWS_SECRET_ACCESS_KEY",
            "AWS_BEARER_TOKEN_BEDROCK",
            "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
            "AWS_CONTAINER_CREDENTIALS_FULL_URI",
            "AWS_WEB_IDENTITY_TOKEN_FILE",
        ]:
            monkeypatch.delenv(key, raising=False)

        result = get_env_api_key("amazon-bedrock")
        assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

