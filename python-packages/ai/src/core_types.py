"""
核心类型定义模块。

本模块包含 AI 抽象层使用的所有核心类型定义，
包括消息类型、内容块、工具定义和流式事件。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    TypedDict,
    Union,
)

# ============================================================================
# API 和提供商类型
# ============================================================================

# 已知的 API 类型（LLM 提供商的具体 API 接口）
KnownApi = Literal[
    "openai-completions",       # OpenAI Chat Completions API
    "mistral-conversations",    # Mistral Conversations API
    "openai-responses",         # OpenAI Responses API
    "azure-openai-responses",   # Azure OpenAI Responses API
    "openai-codex-responses",   # OpenAI Codex Responses API
    "anthropic-messages",       # Anthropic Messages API
    "bedrock-converse-stream",  # Amazon Bedrock Converse API
    "google-generative-ai",     # Google Generative AI API
    "google-gemini-cli",        # Google Gemini CLI
    "google-vertex",            # Google Vertex AI API
    "friday-responses",         # Friday Responses API（美团内部）
]

# API 类型 = 已知 API 或自定义字符串
Api = Union[KnownApi, str]

# 已知的提供商名称
KnownProvider = Literal[
    "amazon-bedrock",
    "anthropic",
    "google",
    "google-gemini-cli",
    "google-antigravity",
    "google-vertex",
    "openai",
    "azure-openai-responses",
    "openai-codex",
    "github-copilot",
    "xai",
    "groq",
    "cerebras",
    "openrouter",
    "vercel-ai-gateway",
    "zai",
    "mistral",
    "minimax",
    "minimax-cn",
    "huggingface",
    "opencode",
    "opencode-go",
    "kimi-coding",
    "friday",                    # Friday（美团内部大模型平台）
]

# 提供商类型 = 已知提供商或自定义字符串
Provider = Union[KnownProvider, str]


# ============================================================================
# 思考（Thinking）类型
# ============================================================================

# 思考级别：从最小到极高
ThinkingLevel = Literal["minimal", "low", "medium", "high", "xhigh"]


class ThinkingBudgets(TypedDict, total=False):
    """每个思考级别的 token 预算（仅适用于基于 token 的提供商）。"""

    minimal: int
    low: int
    medium: int
    high: int


# ============================================================================
# 流式选项
# ============================================================================

# 缓存保留策略
CacheRetention = Literal["none", "short", "long"]
# 传输协议
Transport = Literal["sse", "websocket", "auto"]


class StreamOptions(TypedDict, total=False):
    """所有提供商共享的基础选项。"""

    temperature: float              # 温度参数，控制随机性
    maxTokens: int                  # 最大输出 token 数
    signal: Any                     # asyncio.CancelledSignal，用于取消请求
    apiKey: str                     # API 密钥
    transport: Transport            # 传输协议
    cacheRetention: CacheRetention  # 缓存保留策略
    sessionId: str                  # 会话 ID
    onPayload: Callable[[Any, "Model"], Any]  # payload 回调函数
    headers: Dict[str, str]         # 自定义请求头
    maxRetryDelayMs: int            # 最大重试延迟（毫秒）
    metadata: Dict[str, Any]        # 元数据


class SimpleStreamOptions(StreamOptions, total=False):
    """统一选项，包含 reasoning 参数，用于 streamSimple() 和 completeSimple()。"""

    reasoning: ThinkingLevel        # 思考级别
    thinkingBudgets: ThinkingBudgets  # 思考预算配置


# ============================================================================
# 内容类型
# ============================================================================


class TextSignatureV1(TypedDict):
    """文本签名 V1 格式。"""
    v: Literal[1]
    id: str
    phase: Optional[Literal["commentary", "final_answer"]]


@dataclass
class TextContent:
    """文本内容块。"""

    type: Literal["text"] = "text"
    text: str = ""                          # 文本内容
    textSignature: Optional[str] = None     # 文本签名（用于某些提供商）


@dataclass
class ThinkingContent:
    """思考/推理内容块。"""

    type: Literal["thinking"] = "thinking"
    thinking: str = ""                      # 思考内容
    thinkingSignature: Optional[str] = None # 思考签名
    redacted: bool = False                  # 是否被编辑过


@dataclass
class ImageContent:
    """图片内容块。"""

    type: Literal["image"] = "image"
    data: str = ""          # base64 编码的图片数据
    mimeType: str = ""      # MIME 类型，如 "image/jpeg", "image/png"


@dataclass
class ToolCall:
    """工具调用内容块。"""

    type: Literal["toolCall"] = "toolCall"
    id: str = ""                            # 工具调用 ID，用于关联工具结果
    name: str = ""                          # 工具名称
    arguments: Dict[str, Any] = field(default_factory=dict)  # 工具参数
    thoughtSignature: Optional[str] = None  # 思考签名（Google 特有）


# 内容块联合类型
ContentBlock = Union[TextContent, ThinkingContent, ImageContent, ToolCall]


# ============================================================================
# 使用量类型
# ============================================================================


@dataclass
class UsageCost:
    """API 使用成本明细。"""

    input: float = 0.0       # 输入成本
    output: float = 0.0      # 输出成本
    cacheRead: float = 0.0   # 缓存读取成本
    cacheWrite: float = 0.0  # 缓存写入成本
    total: float = 0.0       # 总成本


@dataclass
class Usage:
    """Token 使用量信息。"""

    input: int = 0           # 输入 token 数
    output: int = 0          # 输出 token 数
    cacheRead: int = 0       # 缓存读取 token 数
    cacheWrite: int = 0      # 缓存写入 token 数
    totalTokens: int = 0     # 总 token 数
    cost: UsageCost = field(default_factory=UsageCost)  # 成本明细


# ============================================================================
# 停止原因
# ============================================================================

# 停止原因类型
StopReason = Literal["stop", "length", "toolUse", "error", "aborted"]


# ============================================================================
# 消息类型
# ============================================================================

# 用户消息内容：字符串或内容块列表
UserContent = Union[str, List[Union[TextContent, ImageContent]]]
# 助手消息内容：内容块列表
AssistantContent = List[Union[TextContent, ThinkingContent, ToolCall]]
# 工具结果内容：内容块列表
ToolResultContent = List[Union[TextContent, ImageContent]]


@dataclass
class UserMessage:
    """用户消息。"""

    role: Literal["user"] = "user"
    content: UserContent = ""                # 用户输入内容
    timestamp: int = 0                       # Unix 时间戳（毫秒）


@dataclass
class AssistantMessage:
    """助手消息。"""

    role: Literal["assistant"] = "assistant"
    content: AssistantContent = field(default_factory=list)  # 助手输出内容
    api: Api = ""                            # 使用的 API 类型
    provider: Provider = ""                  # 提供商名称
    model: str = ""                          # 模型 ID
    usage: Usage = field(default_factory=Usage)  # Token 使用量
    stopReason: StopReason = "stop"          # 停止原因
    errorMessage: Optional[str] = None       # 错误消息（如果有）
    timestamp: int = 0                       # Unix 时间戳（毫秒）


@dataclass
class ToolResultMessage:
    """工具结果消息。"""

    role: Literal["toolResult"] = "toolResult"
    toolCallId: str = ""                     # 对应的工具调用 ID
    toolName: str = ""                       # 工具名称
    content: ToolResultContent = field(default_factory=list)  # 工具执行结果
    details: Optional[Dict[str, Any]] = None # 详细信息
    isError: bool = False                    # 是否执行出错
    timestamp: int = 0                       # Unix 时间戳（毫秒）


# 消息联合类型
Message = Union[UserMessage, AssistantMessage, ToolResultMessage]


# ============================================================================
# 工具定义
# ============================================================================


class ToolParameterSchema(TypedDict, total=False):
    """工具参数的 JSON Schema 定义。"""

    type: str                               # 类型，如 "object"
    properties: Dict[str, Any]              # 属性定义
    required: Optional[List[str]]           # 必需字段列表
    description: Optional[str]              # 描述
    enum: Optional[List[str]]               # 枚举值列表
    items: Optional["ToolParameterSchema"]  # 数组项的 schema


@dataclass
class Tool:
    """工具定义。"""

    name: str                               # 工具名称
    description: str                        # 工具描述
    parameters: ToolParameterSchema = field(default_factory=lambda: {"type": "object", "properties": {}})


# ============================================================================
# 上下文
# ============================================================================


@dataclass
class Context:
    """对话上下文。"""

    systemPrompt: Optional[str] = None      # 系统提示词
    messages: List[Message] = field(default_factory=list)  # 消息列表
    tools: Optional[List[Tool]] = None      # 可用工具列表


# ============================================================================
# 流式事件
# ============================================================================


@dataclass
class StartEvent:
    """流开始事件。"""

    type: Literal["start"] = "start"
    partial: AssistantMessage = field(default_factory=AssistantMessage)  # 部分消息


@dataclass
class TextStartEvent:
    """文本块开始事件。"""

    type: Literal["text_start"] = "text_start"
    contentIndex: int = 0                   # 内容块索引
    partial: AssistantMessage = field(default_factory=AssistantMessage)


@dataclass
class TextDeltaEvent:
    """文本增量事件。"""

    type: Literal["text_delta"] = "text_delta"
    contentIndex: int = 0                   # 内容块索引
    delta: str = ""                         # 增量文本
    partial: AssistantMessage = field(default_factory=AssistantMessage)


@dataclass
class TextEndEvent:
    """文本块结束事件。"""

    type: Literal["text_end"] = "text_end"
    contentIndex: int = 0                   # 内容块索引
    content: str = ""                       # 完整文本内容
    partial: AssistantMessage = field(default_factory=AssistantMessage)


@dataclass
class ThinkingStartEvent:
    """思考块开始事件。"""

    type: Literal["thinking_start"] = "thinking_start"
    contentIndex: int = 0                   # 内容块索引
    partial: AssistantMessage = field(default_factory=AssistantMessage)


@dataclass
class ThinkingDeltaEvent:
    """思考增量事件。"""

    type: Literal["thinking_delta"] = "thinking_delta"
    contentIndex: int = 0                   # 内容块索引
    delta: str = ""                         # 增量思考内容
    partial: AssistantMessage = field(default_factory=AssistantMessage)


@dataclass
class ThinkingEndEvent:
    """思考块结束事件。"""

    type: Literal["thinking_end"] = "thinking_end"
    contentIndex: int = 0                   # 内容块索引
    content: str = ""                       # 完整思考内容
    partial: AssistantMessage = field(default_factory=AssistantMessage)


@dataclass
class ToolCallStartEvent:
    """工具调用开始事件。"""

    type: Literal["toolcall_start"] = "toolcall_start"
    contentIndex: int = 0                   # 内容块索引
    partial: AssistantMessage = field(default_factory=AssistantMessage)


@dataclass
class ToolCallDeltaEvent:
    """工具调用增量事件。"""

    type: Literal["toolcall_delta"] = "toolcall_delta"
    contentIndex: int = 0                   # 内容块索引
    delta: str = ""                         # 增量内容（通常是参数 JSON）
    partial: AssistantMessage = field(default_factory=AssistantMessage)


@dataclass
class ToolCallEndEvent:
    """工具调用结束事件。"""

    type: Literal["toolcall_end"] = "toolcall_end"
    contentIndex: int = 0                   # 内容块索引
    toolCall: ToolCall = field(default_factory=ToolCall)  # 完整的工具调用
    partial: AssistantMessage = field(default_factory=AssistantMessage)


@dataclass
class DoneEvent:
    """流完成事件。"""

    type: Literal["done"] = "done"
    reason: Literal["stop", "length", "toolUse"] = "stop"  # 完成原因
    message: AssistantMessage = field(default_factory=AssistantMessage)  # 完整消息


@dataclass
class ErrorEvent:
    """流错误事件。"""

    type: Literal["error"] = "error"
    reason: Literal["aborted", "error"] = "error"  # 错误原因
    error: AssistantMessage = field(default_factory=AssistantMessage)


# 助手消息事件联合类型
AssistantMessageEvent = Union[
    StartEvent,
    TextStartEvent,
    TextDeltaEvent,
    TextEndEvent,
    ThinkingStartEvent,
    ThinkingDeltaEvent,
    ThinkingEndEvent,
    ToolCallStartEvent,
    ToolCallDeltaEvent,
    ToolCallEndEvent,
    DoneEvent,
    ErrorEvent,
]


# ============================================================================
# 模型类型
# ============================================================================


class OpenRouterRouting(TypedDict, total=False):
    """OpenRouter 提供商路由偏好设置。"""

    only: List[str]   # 仅使用的提供商列表
    order: List[str]  # 提供商优先顺序


class VercelGatewayRouting(TypedDict, total=False):
    """Vercel AI Gateway 路由偏好设置。"""

    only: List[str]   # 仅使用的提供商列表
    order: List[str]  # 提供商优先顺序


class OpenAICompletionsCompat(TypedDict, total=False):
    """OpenAI 兼容 Completions API 的兼容性设置。"""

    supportsStore: bool                      # 是否支持 store 功能
    supportsDeveloperRole: bool              # 是否支持 developer 角色
    supportsReasoningEffort: bool            # 是否支持 reasoning_effort 参数
    reasoningEffortMap: Dict[ThinkingLevel, str]  # 思考级别映射
    supportsUsageInStreaming: bool           # 流式响应是否支持 usage 信息
    maxTokensField: Literal["max_completion_tokens", "max_tokens"]  # 最大 token 字段名
    requiresToolResultName: bool             # 工具结果是否需要 name 字段
    requiresAssistantAfterToolResult: bool   # 工具结果后是否需要 assistant 消息
    requiresThinkingAsText: bool             # 是否将思考作为文本处理
    thinkingFormat: Literal["openai", "zai", "qwen"]  # 思考格式
    openRouterRouting: OpenRouterRouting     # OpenRouter 路由设置
    vercelGatewayRouting: VercelGatewayRouting  # Vercel Gateway 路由设置
    supportsStrictMode: bool                 # 是否支持严格模式


class OpenAIResponsesCompat(TypedDict, total=False):
    """OpenAI Responses API 的兼容性设置。"""

    pass


@dataclass
class ModelCost:
    """模型成本信息（每百万 token）。"""

    input: float = 0.0       # 输入成本 $/百万 token
    output: float = 0.0      # 输出成本 $/百万 token
    cacheRead: float = 0.0   # 缓存读取成本 $/百万 token
    cacheWrite: float = 0.0  # 缓存写入成本 $/百万 token


@dataclass
class Model:
    """模型定义。"""

    id: str                                  # 模型 ID
    name: str                                # 模型名称
    api: Api                                 # API 类型
    provider: Provider                       # 提供商
    baseUrl: str = ""                        # API 基础 URL
    reasoning: bool = False                  # 是否支持推理/思考
    input: List[Literal["text", "image"]] = field(default_factory=lambda: ["text"])  # 支持的输入类型
    cost: ModelCost = field(default_factory=ModelCost)  # 成本信息
    contextWindow: int = 0                   # 上下文窗口大小
    maxTokens: int = 0                       # 最大输出 token 数
    headers: Optional[Dict[str, str]] = None  # 自定义请求头
    compat: Optional[Union[OpenAICompletionsCompat, OpenAIResponsesCompat]] = None  # 兼容性设置


# ============================================================================
# 流函数类型
# ============================================================================

# 流函数类型定义
StreamFunction = Callable[[Model, Context, Optional[StreamOptions]], "AssistantMessageEventStream"]

