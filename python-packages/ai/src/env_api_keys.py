"""
环境变量 API Key 检测。

本模块提供从环境变量获取不同 LLM 提供商 API Key 的功能。
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


def get_env_api_key(provider: str) -> Optional[str]:
    """
    从已知环境变量获取提供商的 API Key。

    此函数根据提供商名称检查环境变量中的 API Key。
    对于需要 OAuth token 的提供商，此函数不会返回 API Key。

    Args:
        provider: 提供商名称（如 "openai", "anthropic"）

    Returns:
        找到则返回 API Key，否则返回 None
    """
    # GitHub Copilot - 支持多种环境变量
    if provider == "github-copilot":
        return (
            os.environ.get("COPILOT_GITHUB_TOKEN")
            or os.environ.get("GH_TOKEN")
            or os.environ.get("GITHUB_TOKEN")
        )

    # Anthropic: ANTHROPIC_OAUTH_TOKEN 优先于 ANTHROPIC_API_KEY
    if provider == "anthropic":
        return os.environ.get("ANTHROPIC_OAUTH_TOKEN") or os.environ.get("ANTHROPIC_API_KEY")

    # Vertex AI 支持显式 API Key 或应用默认凭证
    if provider == "google-vertex":
        if os.environ.get("GOOGLE_CLOUD_API_KEY"):
            return os.environ.get("GOOGLE_CLOUD_API_KEY")

        has_credentials = _has_vertex_adc_credentials()
        has_project = bool(
            os.environ.get("GOOGLE_CLOUD_PROJECT")
            or os.environ.get("GCLOUD_PROJECT")
        )
        has_location = bool(os.environ.get("GOOGLE_CLOUD_LOCATION"))

        # 如果有 ADC 凭证、项目和位置，返回认证标记
        if has_credentials and has_project and has_location:
            return "<authenticated>"

    # Amazon Bedrock 支持多种凭证来源
    if provider == "amazon-bedrock":
        if (
            os.environ.get("AWS_PROFILE")
            or (
                os.environ.get("AWS_ACCESS_KEY_ID")
                and os.environ.get("AWS_SECRET_ACCESS_KEY")
            )
            or os.environ.get("AWS_BEARER_TOKEN_BEDROCK")
            or os.environ.get("AWS_CONTAINER_CREDENTIALS_RELATIVE_URI")
            or os.environ.get("AWS_CONTAINER_CREDENTIALS_FULL_URI")
            or os.environ.get("AWS_WEB_IDENTITY_TOKEN_FILE")
        ):
            return "<authenticated>"

    # Friday（美团内部大模型平台）
    # 支持多种认证方式：
    # - FRIDAY_BILLING_ID: 计费 ID（用于 Authorization header）
    # - FRIDAY_AGENT_ID: Agent 身份 ID（用于 Mt-Agent-Id header）
    if provider == "friday":
        return os.environ.get("FRIDAY_BILLING_ID")

    # 标准环境变量映射
    env_map = {
        "openai": "OPENAI_API_KEY",
        "azure-openai-responses": "AZURE_OPENAI_API_KEY",
        "google": "GEMINI_API_KEY",
        "groq": "GROQ_API_KEY",
        "cerebras": "CEREBRAS_API_KEY",
        "xai": "XAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "vercel-ai-gateway": "AI_GATEWAY_API_KEY",
        "zai": "ZAI_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "minimax": "MINIMAX_API_KEY",
        "minimax-cn": "MINIMAX_CN_API_KEY",
        "huggingface": "HF_TOKEN",
        "opencode": "OPENCODE_API_KEY",
        "opencode-go": "OPENCODE_API_KEY",
        "kimi-coding": "KIMI_API_KEY",
    }

    env_var = env_map.get(provider)
    return os.environ.get(env_var) if env_var else None


# Vertex ADC 凭证检查的缓存结果
_cached_vertex_adc_credentials_exists: Optional[bool] = None


def _has_vertex_adc_credentials() -> bool:
    """
    检查 Vertex AI 应用默认凭证是否可用。

    Returns:
        如果 ADC 凭证可用则返回 True
    """
    global _cached_vertex_adc_credentials_exists

    if _cached_vertex_adc_credentials_exists is not None:
        return _cached_vertex_adc_credentials_exists

    # 首先检查 GOOGLE_APPLICATION_CREDENTIALS 环境变量（标准方式）
    gac_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if gac_path:
        _cached_vertex_adc_credentials_exists = Path(gac_path).exists()
        return _cached_vertex_adc_credentials_exists

    # 回退到默认 ADC 路径
    home = Path.home()
    default_adc_path = home / ".config" / "gcloud" / "application_default_credentials.json"
    _cached_vertex_adc_credentials_exists = default_adc_path.exists()

    return _cached_vertex_adc_credentials_exists

