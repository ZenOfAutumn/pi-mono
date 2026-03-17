"""
pi-agent-core package.

一个具有工具执行和事件流的有状态代理。
"""

# 核心代理类
from .agent import Agent, AgentOptions
# 循环函数
from .agent_loop import agent_loop, agent_loop_continue
# 类型定义
from .types import (
    # 内容块类型
    TextContent,
    ImageContent,
    ThinkingContent,
    ToolCall,
    Content,
    # 消息类型
    UserMessage,
    AssistantMessage,
    ToolResultMessage,
    MessageUnion,
    # 模型和上下文
    Model,
    Context,
    AgentContext,
    # 状态
    AgentState,
    AgentMessage,
    # 工具
    Tool,
    AgentTool,
    AgentToolResult,
    AgentToolUpdateCallback,
    # 事件
    AgentEvent,
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
    # 配置
    AgentLoopConfig,
    SimpleStreamOptions,
    ThinkingLevel,
    StreamFn,
    Usage,
)

__all__ = [
    # 代理
    "Agent",
    "AgentOptions",
    # 循环函数
    "agent_loop",
    "agent_loop_continue",
    # 内容块类型
    "TextContent",
    "ImageContent",
    "ThinkingContent",
    "ToolCall",
    "Content",
    # 消息类型
    "UserMessage",
    "AssistantMessage",
    "ToolResultMessage",
    "MessageUnion",
    # 模型和上下文
    "Model",
    "Context",
    "AgentContext",
    # 状态
    "AgentState",
    "AgentMessage",
    # 工具
    "Tool",
    "AgentTool",
    "AgentToolResult",
    "AgentToolUpdateCallback",
    # 事件
    "AgentEvent",
    "AgentStartEvent",
    "AgentEndEvent",
    "TurnStartEvent",
    "TurnEndEvent",
    "MessageStartEvent",
    "MessageUpdateEvent",
    "MessageEndEvent",
    "ToolExecutionStartEvent",
    "ToolExecutionUpdateEvent",
    "ToolExecutionEndEvent",
    # 配置
    "AgentLoopConfig",
    "SimpleStreamOptions",
    "ThinkingLevel",
    "StreamFn",
    "Usage",
]

