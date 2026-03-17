"""
Agent 类型定义模块
定义了 pi-agent-core 包中使用的所有核心类型。

主要包括:
- 内容块类型 (TextContent, ImageContent, ThinkingContent, ToolCall)
- 消息类型 (UserMessage, AssistantMessage, ToolResultMessage)
- 代理状态和配置类型 (AgentState, AgentLoopConfig, AgentContext)
- 事件类型 (AgentStartEvent, AgentEndEvent, TurnStartEvent 等)
- 工具类型 (Tool, AgentTool, AgentToolResult)
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    List,
    Literal,
    Optional,
    Set,
    TypedDict,
    Union,
    Awaitable,
    Protocol,
    runtime_checkable,
)


# ============================================================================
# 内容块类型定义
# ============================================================================

@dataclass
class TextContent:
    """
    文本内容块。
    用于表示消息中的文本内容。
    """
    type: Literal["text"] = "text"
    text: str = ""


@dataclass
class ImageContent:
    """
    图片内容块。
    用于表示消息中的图片内容，支持 base64 编码的图片数据。
    """
    type: Literal["image"] = "image"
    data: str = ""  # base64 编码的图片数据
    mime_type: str = "image/png"  # 图片 MIME 类型


@dataclass
class ThinkingContent:
    """
    思考内容块。
    用于支持思维链 (Chain of Thought) 的模型，记录模型的推理过程。
    """
    type: Literal["thinking"] = "thinking"
    thinking: str = ""  # 模型的思考/推理内容


@dataclass
class ToolCall:
    """
    工具调用内容块。
    表示助手消息中对工具的调用请求。
    """
    type: Literal["toolCall"] = "toolCall"
    id: str = ""  # 工具调用的唯一标识符
    name: str = ""  # 工具名称
    arguments: Dict[str, Any] = field(default_factory=dict)  # 工具参数


# 内容联合类型：支持文本、图片、思考和工具调用
Content = Union[TextContent, ImageContent, ThinkingContent, ToolCall]


# ============================================================================
# 使用量统计类型
# ============================================================================

@dataclass
class Usage:
    """
    Token 使用量统计信息。
    记录 LLM 调用的 token 消耗和费用。
    """
    input: int = 0  # 输入 token 数
    output: int = 0  # 输出 token 数
    cache_read: int = 0  # 从缓存读取的 token 数
    cache_write: int = 0  # 写入缓存的 token 数
    total_tokens: int = 0  # 总 token 数
    cost: Dict[str, float] = field(default_factory=lambda: {
        "input": 0.0, "output": 0.0, "cache_read": 0.0, "cache_write": 0.0, "total": 0.0
    })  # 费用明细


# ============================================================================
# 模型配置类型
# ============================================================================

@dataclass
class Model:
    """
    模型配置。
    包含 LLM 提供商和模型标识信息。
    """
    api: str = ""  # API 标识符 (如 "anthropic-messages", "openai-chat")
    provider: str = ""  # 提供商名称 (如 "anthropic", "openai")
    id: str = ""  # 模型 ID (如 "claude-sonnet-4-20250514", "gpt-4o")


# ============================================================================
# 消息类型定义
# ============================================================================

@dataclass
class UserMessage:
    """
    用户消息。
    表示来自用户的消息，可包含文本、图片等多种内容类型。
    """
    role: Literal["user"] = "user"
    content: List[Content] = field(default_factory=list)  # 消息内容列表
    timestamp: int = 0  # 消息时间戳（毫秒）


@dataclass
class AssistantMessage:
    """
    助手消息。
    表示来自 LLM 的响应消息，包含生成的内容、使用量统计等信息。
    """
    role: Literal["assistant"] = "assistant"
    content: List[Content] = field(default_factory=list)  # 消息内容列表
    timestamp: int = 0  # 消息时间戳（毫秒）
    api: str = ""  # 使用的 API
    provider: str = ""  # 提供商名称
    model: str = ""  # 模型 ID
    usage: Usage = field(default_factory=Usage)  # token 使用量统计
    stop_reason: str = "stop"  # 停止原因 (stop, length, toolUse, error, aborted)
    error_message: Optional[str] = None  # 错误信息（如果有）


@dataclass
class ToolResultMessage:
    """
    工具结果消息。
    表示工具执行后返回的结果，作为上下文传递给 LLM。
    """
    role: Literal["toolResult"] = "toolResult"
    content: List[Content] = field(default_factory=list)  # 结果内容
    timestamp: int = 0  # 消息时间戳（毫秒）
    tool_call_id: str = ""  # 对应的工具调用 ID
    tool_name: str = ""  # 工具名称
    details: Dict[str, Any] = field(default_factory=dict)  # 额外详细信息
    is_error: bool = False  # 是否为错误结果


# 消息联合类型
MessageUnion = Union[UserMessage, AssistantMessage, ToolResultMessage]


# ============================================================================
# 思考级别枚举
# ============================================================================

class ThinkingLevel(str, Enum):
    """
    思考/推理级别枚举。
    用于支持思维链的模型，控制推理深度。

    注意: "xhigh" 级别仅 OpenAI gpt-5.x 系列模型支持。
    """
    OFF = "off"  # 关闭思考
    MINIMAL = "minimal"  # 最小思考
    LOW = "low"  # 低级思考
    MEDIUM = "medium"  # 中级思考
    HIGH = "high"  # 高级思考
    XHIGH = "xhigh"  # 超高级思考（仅部分模型支持）


# ============================================================================
# 流式函数协议
# ============================================================================

@runtime_checkable
class StreamFn(Protocol):
    """
    流式函数协议。
    定义了调用 LLM API 的标准接口。

    用于支持自定义的 LLM 调用方式，如:
    - 直接调用 (streamSimple)
    - 通过代理服务器调用 (streamProxy)
    """
    def __call__(
        self,
        model: Model,
        context: 'Context',
        options: Optional['SimpleStreamOptions'] = None,
    ) -> Awaitable['EventStream']:
        ...


class SimpleStreamOptions(TypedDict, total=False):
    """
    简化的流式调用选项。
    包含 LLM 调用的各种配置参数。
    """
    temperature: Optional[float]  # 温度参数，控制输出随机性
    max_tokens: Optional[int]  # 最大输出 token 数
    reasoning: Optional[str]  # 推理模式/级别
    session_id: Optional[str]  # 会话 ID，用于提供商缓存
    api_key: Optional[str]  # API 密钥
    signal: Optional[Any]  # 中止信号 (threading.Event 或类似对象)
    on_payload: Optional[Callable[[Dict[str, Any]], None]]  # 请求载荷回调
    transport: Optional[str]  # 传输方式 (sse, ws 等)
    thinking_budgets: Optional[Dict[str, int]]  # 各思考级别的 token 预算
    max_retry_delay_ms: Optional[int]  # 最大重试延迟（毫秒）


# ============================================================================
# 代理循环配置
# ============================================================================

@dataclass
class AgentLoopConfig:
    """
    代理循环配置。
    包含运行代理循环所需的所有配置选项。

    主要配置:
    - model: 使用的 LLM 模型
    - convert_to_llm: 将 AgentMessage 转换为 LLM 兼容消息的函数
    - transform_context: 可选的上下文转换函数（用于修剪、压缩等）
    - get_steering_messages: 获取中断消息的回调
    - get_follow_up_messages: 获取后续消息的回调
    """
    model: Model = field(default_factory=Model)

    # 将 AgentMessage[] 转换为 LLM 兼容的 Message[]，每次 LLM 调用前执行
    # 必须将 AgentMessage 过滤/转换为 UserMessage、AssistantMessage 或 ToolResultMessage
    convert_to_llm: Callable[[List['AgentMessage']], Awaitable[List[MessageUnion]]] = None  # type: ignore

    # 可选的上下文转换函数，在 convert_to_llm 之前执行
    # 用于上下文窗口管理（修剪旧消息）或注入外部上下文
    transform_context: Optional[Callable[[List['AgentMessage'], Optional[Any]], Awaitable[List['AgentMessage']]]] = None

    # 动态解析 API 密钥的函数
    # 适用于短期 OAuth 令牌（如 GitHub Copilot），可能在长时间工具执行期间过期
    get_api_key: Optional[Callable[[str], Awaitable[Optional[str]]]] = None

    # 返回引导消息的函数，用于在代理运行期间注入中断
    # 在每次工具执行后调用检查用户中断
    # 如果返回消息，剩余工具调用将被跳过，这些消息会在下次 LLM 调用前注入上下文
    get_steering_messages: Optional[Callable[[], Awaitable[List['AgentMessage']]]] = None

    # 返回后续消息的函数，在代理本应停止时检查
    # 仅在代理没有更多工具调用和引导消息时调用
    # 如果返回消息，它们会被注入上下文并运行另一轮
    get_follow_up_messages: Optional[Callable[[], Awaitable[List['AgentMessage']]]] = None

    # 流式调用参数
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    reasoning: Optional[str] = None
    session_id: Optional[str] = None
    api_key: Optional[str] = None
    thinking_budgets: Optional[Dict[str, int]] = None


# ============================================================================
# 自定义消息类型扩展
# ============================================================================

class CustomAgentMessages(TypedDict, total=False):
    """
    自定义消息类型的可扩展接口。

    应用可以通过声明合并扩展此接口添加自定义消息类型：

    示例:
        # 在模块级别添加
        CustomAgentMessages.notification = { "role": "notification", "text": str, "timestamp": int }

    这样 AgentMessage 就能包含自定义类型，实现类型安全。
    """
    pass


# AgentMessage: LLM 消息 + 自定义消息的联合类型
# 这是代理中使用的主要消息类型，比原生 LLM 消息更灵活
AgentMessage = Union[Dict[str, Any]]


# ============================================================================
# 代理状态
# ============================================================================

@dataclass
class AgentState:
    """
    代理状态。
    包含代理的所有配置和会话数据。

    通过 agent.state 访问。在流式传输期间，stream_message 包含部分助手消息。
    """
    system_prompt: str = ""  # 系统提示词
    model: Optional[Model] = None  # 当前使用的模型
    thinking_level: ThinkingLevel = ThinkingLevel.OFF  # 思考级别
    tools: List['AgentTool'] = field(default_factory=list)  # 可用工具列表
    messages: List[AgentMessage] = field(default_factory=list)  # 会话消息历史（可包含附件和自定义消息类型）
    is_streaming: bool = False  # 是否正在流式传输
    stream_message: Optional[AgentMessage] = None  # 流式传输期间的当前部分消息
    pending_tool_calls: Set[str] = field(default_factory=set)  # 待处理的工具调用 ID 集合
    error: Optional[str] = None  # 错误信息（如果有）


# ============================================================================
# 工具执行结果
# ============================================================================

@dataclass
class AgentToolResult:
    """
    工具执行结果。
    包含工具执行后的返回内容和详细信息。
    """
    # 内容块，支持文本和图片
    content: List[Union[TextContent, ImageContent]] = field(default_factory=list)
    # 详细信息，用于 UI 显示或日志记录
    details: Dict[str, Any] = field(default_factory=dict)


# 工具执行进度更新回调类型
AgentToolUpdateCallback = Callable[[AgentToolResult], None]


# ============================================================================
# 工具定义
# ============================================================================

@dataclass
class Tool:
    """
    基础工具定义。
    包含工具的元数据，供 LLM 了解如何调用。
    """
    name: str = ""  # 工具名称（唯一标识符）
    description: str = ""  # 工具描述（供 LLM 理解用途）
    parameters: Dict[str, Any] = field(default_factory=dict)  # 参数 JSON Schema


@dataclass
class AgentTool(Tool):
    """
    代理工具。
    扩展基础工具定义，添加执行功能。

    工具执行流程:
    1. LLM 返回工具调用请求
    2. 代理验证参数
    3. 调用 execute 函数
    4. 返回结果给 LLM
    """
    # 工具的人类可读标签，用于 UI 显示
    label: str = ""

    # 工具执行函数
    # 参数:
    #   - tool_call_id: 工具调用唯一标识符
    #   - params: 验证后的工具参数
    #   - signal: 中止信号
    #   - on_update: 进度更新回调（可选）
    # 返回: AgentToolResult
    execute: Optional[Callable[
        [str, Dict[str, Any], Optional[Any], Optional[AgentToolUpdateCallback]],
        Awaitable[AgentToolResult]
    ]] = None


# ============================================================================
# 上下文类型
# ============================================================================

@dataclass
class AgentContext:
    """
    代理上下文。
    包含代理运行时的完整状态，使用 AgentMessage 和 AgentTool。
    """
    system_prompt: str = ""  # 系统提示词
    messages: List[AgentMessage] = field(default_factory=list)  # 消息历史
    tools: Optional[List[AgentTool]] = None  # 可用工具


@dataclass
class Context:
    """
    LLM 上下文。
    包含发送给 LLM 的完整上下文，使用标准消息类型。
    """
    system_prompt: str = ""  # 系统提示词
    messages: List[Union[UserMessage, AssistantMessage, ToolResultMessage]] = field(default_factory=list)  # 消息历史
    tools: Optional[List[Tool]] = None  # 可用工具


# ============================================================================
# 代理事件类型
# ============================================================================

@dataclass
class AgentStartEvent:
    """
    代理启动事件。
    在代理开始处理时发出。
    """
    type: Literal["agent_start"] = "agent_start"


@dataclass
class AgentEndEvent:
    """
    代理结束事件。
    在代理完成所有处理后发出，包含所有新消息。
    """
    type: Literal["agent_end"] = "agent_end"
    messages: List[AgentMessage] = field(default_factory=list)


@dataclass
class TurnStartEvent:
    """
    轮次开始事件。
    每个新的 LLM 调用轮次开始时发出。
    一个轮次 = 一次 LLM 调用 + 工具执行。
    """
    type: Literal["turn_start"] = "turn_start"


@dataclass
class TurnEndEvent:
    """
    轮次结束事件。
    每个轮次完成时发出，包含助手消息和工具结果。
    """
    type: Literal["turn_end"] = "turn_end"
    message: AgentMessage = None  # type: ignore
    tool_results: List[ToolResultMessage] = field(default_factory=list)


@dataclass
class MessageStartEvent:
    """
    消息开始事件。
    任何消息（user、assistant、toolResult）开始时发出。
    """
    type: Literal["message_start"] = "message_start"
    message: AgentMessage = None  # type: ignore


@dataclass
class MessageUpdateEvent:
    """
    消息更新事件。
    仅在助手消息流式传输期间发出，包含增量更新。
    """
    type: Literal["message_update"] = "message_update"
    message: AgentMessage = None  # type: ignore
    assistant_message_event: Optional[Dict[str, Any]] = None  # 原始的助手消息事件


@dataclass
class MessageEndEvent:
    """
    消息结束事件。
    消息完成时发出。
    """
    type: Literal["message_end"] = "message_end"
    message: AgentMessage = None  # type: ignore


@dataclass
class ToolExecutionStartEvent:
    """
    工具执行开始事件。
    工具开始执行时发出。
    """
    type: Literal["tool_execution_start"] = "tool_execution_start"
    tool_call_id: str = ""  # 工具调用 ID
    tool_name: str = ""  # 工具名称
    args: Dict[str, Any] = field(default_factory=dict)  # 工具参数


@dataclass
class ToolExecutionUpdateEvent:
    """
    工具执行更新事件。
    工具执行过程中发出进度更新。
    """
    type: Literal["tool_execution_update"] = "tool_execution_update"
    tool_call_id: str = ""
    tool_name: str = ""
    args: Dict[str, Any] = field(default_factory=dict)
    partial_result: Any = None  # 部分结果


@dataclass
class ToolExecutionEndEvent:
    """
    工具执行结束事件。
    工具执行完成时发出。
    """
    type: Literal["tool_execution_end"] = "tool_execution_end"
    tool_call_id: str = ""
    tool_name: str = ""
    result: Any = None  # 执行结果
    is_error: bool = False  # 是否为错误


# ============================================================================
# 事件联合类型
# ============================================================================

# 所有代理事件的联合类型
AgentEvent = Union[
    AgentStartEvent,
    AgentEndEvent,
    TurnStartEvent,
    TurnEndEvent,
    MessageStartEvent,
    MessageUpdateEvent,
    MessageEndEvent,
    ToolExecutionStartEvent,
    ToolExecutionUpdateEvent,
    ToolExecutionEndEvent,
    Dict[str, Any],  # 支持动态事件类型
]

