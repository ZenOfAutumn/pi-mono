"""
Friday Responses API 配置模块。

本模块定义 Friday Responses API 的配置选项，
包括认证头、端点 URL 和请求参数映射。

配置优先级：
1. 代码中直接传入的参数
2. 配置文件 (config/friday.json)
3. 环境变量
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Literal, Optional, TypedDict, Union

if TYPE_CHECKING:
    from ..core_types import ThinkingLevel


# ============================================================================
# 常量定义
# ============================================================================

# Friday Responses API 端点
FRIDAY_RESPONSES_API_URL = "https://aigc.sankuai.com/v1/responses"

# 默认模型 ID
DEFAULT_FRIDAY_MODEL = "gpt-4o-mini"

# 配置文件路径（相对于包根目录）
def _get_default_config_file() -> Path:
    """
    获取默认配置文件路径。

    配置文件位于包的 config 目录下。

    Returns:
        配置文件路径
    """
    # 获取当前模块所在目录，然后向上找到包根目录
    current_dir = Path(__file__).parent  # providers/
    package_root = current_dir.parent.parent  # ai/
    return package_root / "config" / "friday.json"


DEFAULT_CONFIG_FILE = _get_default_config_file()

# 配置文件中的键名
CONFIG_KEY_BILLING_ID = "billing_id"
CONFIG_KEY_AGENT_ID = "agent_id"
CONFIG_KEY_CONTEXT_TOKEN = "context_token"
CONFIG_KEY_USER_ID = "user_id"
CONFIG_KEY_API_URL = "api_url"
CONFIG_KEY_DEFAULT_MODEL = "default_model"
CONFIG_KEY_HEADERS = "headers"

# 环境变量名称（作为备用）
ENV_FRIDAY_BILLING_ID = "FRIDAY_BILLING_ID"
ENV_FRIDAY_AGENT_ID = "FRIDAY_AGENT_ID"
ENV_FRIDAY_CONTEXT_TOKEN = "FRIDAY_CONTEXT_TOKEN"
ENV_FRIDAY_USER_ID = "FRIDAY_USER_ID"


# ============================================================================
# 配置文件管理
# ============================================================================

class FridayConfigManager:
    """
    Friday 配置文件管理器。

    负责读取、写入和管理 config/friday.json 配置文件。

    配置文件格式（推荐 - 所有认证信息放在 headers 中）：
    {
        "api_url": "https://aigc.sankuai.com/v1/responses",
        "default_model": "gpt-4o-mini",
        "headers": {
            "billing_id": "your_billing_id",
            "agent_id": "your_agent_id",
            "context_token": "your_context_token",
            "user_id": "your_user_id",
            "Content-Type": "application/json;charset=UTF-8"
        }
    }

    向后兼容格式（认证信息放在独立字段）：
    {
        "billing_id": "your_billing_id",
        "agent_id": "your_agent_id",
        "context_token": "your_context_token",
        "user_id": "your_user_id",
        "api_url": "https://aigc.sankuai.com/v1/responses",
        "default_model": "gpt-4o-mini"
    }
    """

    def __init__(self, config_path: Optional[Path] = None):
        """
        初始化配置管理器。

        Args:
            config_path: 配置文件路径，默认为 config/friday.json
        """
        self.config_path = config_path or DEFAULT_CONFIG_FILE
        self._config: Optional[Dict[str, Any]] = None

    @property
    def config(self) -> Dict[str, Any]:
        """
        获取配置内容（延迟加载）。

        Returns:
            配置字典
        """
        if self._config is None:
            self._config = self._load_config()
        return self._config

    def _load_config(self) -> Dict[str, Any]:
        """
        从文件加载配置。

        Returns:
            配置字典，如果文件不存在则返回空字典
        """
        if not self.config_path.exists():
            return {}

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def _save_config(self) -> None:
        """
        保存配置到文件。

        会自动创建配置目录。
        """
        # 确保目录存在
        self.config_path.parent.mkdir(parents=True, exist_ok=True)

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        获取配置值。

        查找顺序：
        1. 配置文件
        2. 环境变量（仅对认证相关字段）

        Args:
            key: 配置键名
            default: 默认值

        Returns:
            配置值
        """
        # 先从配置文件读取
        value = self.config.get(key)
        if value is not None:
            return str(value)

        # 回退到环境变量
        env_map = {
            CONFIG_KEY_BILLING_ID: ENV_FRIDAY_BILLING_ID,
            CONFIG_KEY_AGENT_ID: ENV_FRIDAY_AGENT_ID,
            CONFIG_KEY_CONTEXT_TOKEN: ENV_FRIDAY_CONTEXT_TOKEN,
            CONFIG_KEY_USER_ID: ENV_FRIDAY_USER_ID,
        }
        if key in env_map:
            return os.environ.get(env_map[key], default)

        return default

    def set(self, key: str, value: str) -> None:
        """
        设置配置值。

        Args:
            key: 配置键名
            value: 配置值
        """
        self.config[key] = value
        self._save_config()

    def delete(self, key: str) -> bool:
        """
        删除配置项。

        Args:
            key: 配置键名

        Returns:
            是否删除成功
        """
        if key in self.config:
            del self.config[key]
            self._save_config()
            return True
        return False

    def clear(self) -> None:
        """清空所有配置。"""
        self._config = {}
        if self.config_path.exists():
            self.config_path.unlink()

    def get_billing_id(self) -> Optional[str]:
        """获取计费 ID。优先从 headers 读取，其次从独立字段读取。"""
        # 优先从 headers 读取
        headers = self.get_headers()
        billing_id = headers.get("billing_id")
        if billing_id:
            return billing_id
        # 其次从独立字段读取
        return self.get(CONFIG_KEY_BILLING_ID)

    def get_agent_id(self) -> Optional[str]:
        """获取 Agent ID。优先从 headers 读取，其次从独立字段读取。"""
        headers = self.get_headers()
        agent_id = headers.get("agent_id")
        if agent_id:
            return agent_id
        return self.get(CONFIG_KEY_AGENT_ID)

    def get_context_token(self) -> Optional[str]:
        """获取上下文 Token。优先从 headers 读取，其次从独立字段读取。"""
        headers = self.get_headers()
        context_token = headers.get("context_token")
        if context_token:
            return context_token
        return self.get(CONFIG_KEY_CONTEXT_TOKEN)

    def get_user_id(self) -> Optional[str]:
        """获取用户 ID。优先从 headers 读取，其次从独立字段读取。"""
        headers = self.get_headers()
        user_id = headers.get("user_id")
        if user_id:
            return user_id
        return self.get(CONFIG_KEY_USER_ID)

    def get_api_url(self) -> str:
        """获取 API URL。"""
        return self.get(CONFIG_KEY_API_URL, FRIDAY_RESPONSES_API_URL) or FRIDAY_RESPONSES_API_URL

    def get_default_model(self) -> str:
        """获取默认模型。"""
        return self.get(CONFIG_KEY_DEFAULT_MODEL, DEFAULT_FRIDAY_MODEL) or DEFAULT_FRIDAY_MODEL

    def get_headers(self) -> Dict[str, str]:
        """获取自定义请求头。"""
        headers = self.config.get(CONFIG_KEY_HEADERS, {})
        if isinstance(headers, dict):
            return {k: str(v) for k, v in headers.items()}
        return {}

    def set_headers(self, headers: Dict[str, str]) -> None:
        """设置自定义请求头。"""
        self.config[CONFIG_KEY_HEADERS] = headers
        self._save_config()

    def set_billing_id(self, billing_id: str) -> None:
        """设置计费 ID。"""
        self.set(CONFIG_KEY_BILLING_ID, billing_id)

    def set_agent_id(self, agent_id: str) -> None:
        """设置 Agent ID。"""
        self.set(CONFIG_KEY_AGENT_ID, agent_id)

    def set_context_token(self, context_token: str) -> None:
        """设置上下文 Token。"""
        self.set(CONFIG_KEY_CONTEXT_TOKEN, context_token)

    def set_user_id(self, user_id: str) -> None:
        """设置用户 ID。"""
        self.set(CONFIG_KEY_USER_ID, user_id)

    def set_api_url(self, api_url: str) -> None:
        """设置 API URL。"""
        self.set(CONFIG_KEY_API_URL, api_url)

    def set_default_model(self, default_model: str) -> None:
        """设置默认模型。"""
        self.set(CONFIG_KEY_DEFAULT_MODEL, default_model)


# 全局配置管理器实例
_config_manager: Optional[FridayConfigManager] = None


def get_config_manager() -> FridayConfigManager:
    """
    获取全局配置管理器实例。

    Returns:
        配置管理器实例
    """
    global _config_manager
    if _config_manager is None:
        _config_manager = FridayConfigManager()
    return _config_manager


def set_config_path(config_path: Path) -> None:
    """
    设置配置文件路径。

    Args:
        config_path: 配置文件路径
    """
    global _config_manager
    _config_manager = FridayConfigManager(config_path)


# ============================================================================
# 认证级别
# ============================================================================

AuthLevel = Literal["basic", "identity", "user_identity"]
"""
认证级别：
- basic: 基础鉴权，仅需要 Authorization
- identity: 身份鉴权，需要 Authorization + Mt-Agent-Id
- user_identity: 携带用户信息身份鉴权，需要完整认证头
"""


# ============================================================================
# 认证配置
# ============================================================================

@dataclass
class FridayAuthConfig:
    """
    Friday API 认证配置。

    Friday 提供三种认证级别：
    1. 基础鉴权：仅需 Authorization（计费 ID）
    2. 身份鉴权：Authorization + Mt-Agent-Id
    3. 用户身份鉴权：完整认证头（包括 Mt-Context-Token）
    """

    billing_id: str                           # 计费 ID（必需）
    agent_id: Optional[str] = None            # Agent 身份 ID
    context_token: Optional[str] = None       # 上下文 Token（用于 MCP 等资源访问）
    user_id: Optional[str] = None             # 美团用户 ID
    headers: Optional[Dict[str, str]] = None  # 自定义请求头

    @property
    def auth_level(self) -> AuthLevel:
        """
        根据提供的凭证确定认证级别。

        Returns:
            认证级别
        """
        if self.context_token and self.agent_id:
            return "user_identity"
        elif self.agent_id:
            return "identity"
        else:
            return "basic"

    def to_headers(self) -> Dict[str, str]:
        """
        生成 HTTP 请求头。

        优先从 self.headers 中读取认证相关字段，
        如果没有则从各自的字段读取。

        Returns:
            认证头字典
        """
        # 优先从 headers 中获取认证信息，其次从独立字段获取
        billing_id = self._get_header_value("billing_id", self.billing_id)
        agent_id = self._get_header_value("agent_id", self.agent_id)
        context_token = self._get_header_value("context_token", self.context_token)
        user_id = self._get_header_value("user_id", self.user_id)
        content_type = self._get_header_value("content_type", "application/json;charset=UTF-8")

        headers: Dict[str, str] = {
            "Authorization": f"Bearer {billing_id}",
            "Content-Type": content_type,
        }

        if agent_id:
            headers["Mt-Agent-Id"] = agent_id

        if context_token:
            headers["Mt-Context-Token"] = context_token

        if user_id:
            headers["Mt-User-Id"] = user_id

        # 合并其他自定义请求头（排除已处理的认证字段）
        if self.headers:
            excluded_keys = {"billing_id", "agent_id", "context_token", "user_id", "content_type"}
            for key, value in self.headers.items():
                if key.lower() not in excluded_keys:
                    headers[key] = value

        return headers

    def _get_header_value(self, key: str, fallback: Optional[str]) -> Optional[str]:
        """
        从 headers 中获取值，如果不存在则返回 fallback。

        Args:
            key: headers 中的键名
            fallback: 默认值

        Returns:
            值或 fallback
        """
        if self.headers:
            # 尝试小写键名
            value = self.headers.get(key.lower())
            if value is not None:
                return value
            # 尝试原始键名（用于 Content-Type 等标准头）
            if key == "content_type":
                value = self.headers.get("Content-Type")
                if value is not None:
                    return value
        return fallback

    @classmethod
    def from_config(cls, config_manager: Optional[FridayConfigManager] = None) -> Optional["FridayAuthConfig"]:
        """
        从配置文件创建认证配置。

        Args:
            config_manager: 配置管理器，默认使用全局实例

        Returns:
            认证配置，如果缺少必需的配置则返回 None
        """
        if config_manager is None:
            config_manager = get_config_manager()

        billing_id = config_manager.get_billing_id()
        if not billing_id:
            return None

        return cls(
            billing_id=billing_id,
            agent_id=config_manager.get_agent_id(),
            context_token=config_manager.get_context_token(),
            user_id=config_manager.get_user_id(),
            headers=config_manager.get_headers(),
        )

    @classmethod
    def from_env(cls) -> Optional["FridayAuthConfig"]:
        """
        从环境变量创建认证配置。

        此方法保留用于向后兼容，推荐使用 from_config()。

        Returns:
            认证配置，如果缺少必需的环境变量则返回 None
        """
        billing_id = os.environ.get(ENV_FRIDAY_BILLING_ID)
        if not billing_id:
            return None

        return cls(
            billing_id=billing_id,
            agent_id=os.environ.get(ENV_FRIDAY_AGENT_ID),
            context_token=os.environ.get(ENV_FRIDAY_CONTEXT_TOKEN),
            user_id=os.environ.get(ENV_FRIDAY_USER_ID),
        )


# ============================================================================
# 流式选项
# ============================================================================

class FridayResponsesOptions(TypedDict, total=False):
    """
    Friday Responses API 特有的流式选项。
    """

    # 基础选项
    temperature: float                        # 温度参数（0-2）
    maxTokens: int                            # 最大输出 token 数
    topP: float                               # 核采样参数

    # Friday 特有选项
    billingId: str                            # 计费 ID
    agentId: str                              # Agent 身份 ID
    contextToken: str                         # 上下文 Token
    userId: str                               # 美团用户 ID

    # 配置文件路径
    configPath: str                           # Friday 配置文件路径（覆盖默认路径）

    # 自定义请求头
    headers: Dict[str, str]                   # 自定义 HTTP 请求头

    # 思考模型配置
    reasoning: ThinkingLevel                  # 思考级别
    thinkTokens: int                          # 思考 token 预算

    # 输出格式
    textFormat: Literal["text", "json_object"]  # 输出格式

    # 上下文管理
    previousResponseId: str                   # 上一次响应 ID（多轮对话）

    # 工具配置
    toolChoice: Union[Literal["auto", "none"], Dict[str, any]]  # 工具选择策略
    parallelToolCalls: bool                   # 是否允许并行工具调用

    # 其他选项
    metadata: Dict[str, any]                  # 业务随路参数


# ============================================================================
# 请求参数构建
# ============================================================================

def build_friday_request_params(
    model_id: str,
    input_messages: list,
    tools: Optional[list] = None,
    options: Optional[FridayResponsesOptions] = None,
) -> Dict[str, any]:
    """
    构建 Friday Responses API 请求参数。

    Args:
        model_id: 模型 ID
        input_messages: 输入消息列表
        tools: 可选的工具列表
        options: 可选的流式选项

    Returns:
        请求参数字典
    """
    params: Dict[str, any] = {
        "model": model_id,
        "input": input_messages,
        "stream": True,  # 始终使用流式
    }

    # 工具配置（不需要 options）
    if tools:
        params["tools"] = tools

    if not options:
        return params

    # 基础参数
    if "maxTokens" in options:
        params["max_output_tokens"] = options["maxTokens"]

    if "temperature" in options:
        params["temperature"] = options["temperature"]

    if "topP" in options:
        params["top_p"] = options["topP"]

    # 思考模型配置
    if options.get("reasoning") is not None or options.get("thinkTokens") is not None:
        think_config: Dict[str, any] = {"enabled": True}
        if options.get("thinkTokens") is not None:
            think_config["thinkTokens"] = options["thinkTokens"]
        params["think"] = think_config

    # 输出格式
    if "textFormat" in options:
        params["text"] = {"format": {"type": options["textFormat"]}}

    # 上下文管理
    if "previousResponseId" in options:
        params["previous_response_id"] = options["previousResponseId"]

    # 工具选择配置
    if "toolChoice" in options:
        params["tool_choice"] = options["toolChoice"]

    if "parallelToolCalls" in options:
        params["parallel_tool_calls"] = options["parallelToolCalls"]

    # 业务随路参数
    if "metadata" in options:
        params["metadata"] = options["metadata"]

    return params


# ============================================================================
# 流式事件类型
# ============================================================================

FridayStreamEventType = Literal[
    "response.created",
    "response.in_progress",
    "response.output_text.delta",
    "response.function_call_arguments.delta",
    "response.function_call_arguments.done",
    "response.completed",
]
"""
Friday Responses API 流式事件类型：
- response.created: 响应创建
- response.in_progress: 响应进行中
- response.output_text.delta: 文本增量
- response.function_call_arguments.delta: 函数调用参数增量
- response.function_call_arguments.done: 函数调用参数完成
- response.completed: 响应完成
"""

