"""
配置加载模块
支持从 JSON 文件加载 agent 配置，其中 system_prompt 可以是文件路径
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, Optional

from .types import AgentContext, AgentLoopConfig, AgentState, Model, ThinkingLevel


def load_system_prompt(prompt_value: str, config_dir: Optional[Path] = None) -> str:
    """
    加载系统提示词

    如果 prompt_value 是文件路径（以 .txt 结尾），则从文件读取内容
    否则直接返回 prompt_value 作为系统提示词

    Args:
        prompt_value: 系统提示词或文件路径
        config_dir: 配置文件所在目录（用于相对路径解析）

    Returns:
        系统提示词内容
    """
    # 检查是否是文件路径
    if prompt_value.endswith(".txt") or prompt_value.endswith(".md"):
        # 尝试解析为文件路径
        path = Path(prompt_value)

        # 如果是相对路径，基于 config_dir 解析
        if not path.is_absolute() and config_dir is not None:
            path = config_dir / path

        # 检查文件是否存在
        if path.exists() and path.is_file():
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()

    # 不是文件路径，直接返回
    return prompt_value


def load_agent_config(config_path: str | Path) -> Dict[str, Any]:
    """
    从 JSON 文件加载 agent 配置

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典，system_prompt 已解析为内容
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    # 读取 JSON 配置
    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    # 解析 system_prompt
    if "system_prompt" in config:
        config_dir = config_path.parent
        config["system_prompt"] = load_system_prompt(config["system_prompt"], config_dir)

    return config


def create_agent_context_from_config(config: Dict[str, Any]) -> AgentContext:
    """
    从配置字典创建 AgentContext

    Args:
        config: 配置字典

    Returns:
        AgentContext 实例
    """
    return AgentContext(
        system_prompt=config.get("system_prompt", ""),
        messages=config.get("messages", []),
        tools=None,  # 工具需要单独注册
    )


def create_agent_state_from_config(config: Dict[str, Any]) -> AgentState:
    """
    从配置字典创建 AgentState

    Args:
        config: 配置字典

    Returns:
        AgentState 实例
    """
    # 解析模型配置
    model_config = config.get("model", {})
    model = Model(
        api=model_config.get("api", ""),
        provider=model_config.get("provider", ""),
        id=model_config.get("id", ""),
    )

    # 解析思考级别
    thinking_level_str = config.get("thinking_level", "off")
    try:
        thinking_level = ThinkingLevel(thinking_level_str)
    except ValueError:
        thinking_level = ThinkingLevel.OFF

    return AgentState(
        system_prompt=config.get("system_prompt", ""),
        model=model,
        thinking_level=thinking_level,
        tools=[],  # 工具需要单独注册
        messages=config.get("messages", []),
    )


def create_agent_loop_config_from_config(config: Dict[str, Any]) -> AgentLoopConfig:
    """
    从配置字典创建 AgentLoopConfig

    Args:
        config: 配置字典

    Returns:
        AgentLoopConfig 实例
    """
    # 解析模型配置
    model_config = config.get("model", {})
    model = Model(
        api=model_config.get("api", ""),
        provider=model_config.get("provider", ""),
        id=model_config.get("id", ""),
    )

    return AgentLoopConfig(
        model=model,
        temperature=config.get("temperature"),
        max_tokens=config.get("max_tokens"),
        reasoning=config.get("reasoning"),
        session_id=config.get("session_id"),
        api_key=config.get("api_key"),
        thinking_budgets=config.get("thinking_budgets"),
    )

