"""
pi-agent-core package.

一个具有工具执行和事件流的有状态代理。
"""

# 添加 ai 模块到 Python 路径（用于本地开发）
import sys
from pathlib import Path

# 计算 ai 模块的路径：agent/src/__init__.py -> agent/src -> agent -> python-packages -> ai/src
# __file__ 是 agent/src/__init__.py
# parent 是 agent/src
# parent.parent 是 agent
# parent.parent.parent 是 python-packages
_ai_src_path = Path(__file__).parent.parent.parent / "ai" / "src"
if _ai_src_path.exists() and str(_ai_src_path) not in sys.path:
    sys.path.insert(0, str(_ai_src_path))

# 核心代理类
from .agent import Agent, AgentOptions
# 循环函数
from .agent_loop import agent_loop, agent_loop_continue
# 配置加载工具
from .config_loader import (
    load_agent_config,
    load_system_prompt,
    create_agent_context_from_config,
    create_agent_state_from_config,
    create_agent_loop_config_from_config,
    get_tool_names_from_config,
    create_tool_registry_from_available_tools,
    create_tool_registry_from_module,
    create_stream_fn_from_agent_config,
)
# Stream 函数工厂
from .stream_fn_factory import (
    create_stream_fn_from_config,
    create_stream_fn_with_options,
    register_stream_fn_creator,
    unregister_stream_fn_creator,
    get_registered_providers,
)
# 工具注册表
from .tool_registry import (
    ToolRegistry,
    create_tool_registry_from_config,
)
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
    # 工具注册表
    "ToolRegistry",
    "create_tool_registry_from_config",
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
    # 配置加载工具
    "load_agent_config",
    "load_system_prompt",
    "create_agent_context_from_config",
    "create_agent_state_from_config",
    "create_agent_loop_config_from_config",
    "get_tool_names_from_config",
    "create_tool_registry_from_available_tools",
    "create_tool_registry_from_module",
    "create_stream_fn_from_agent_config",
    # Stream 函数工厂
    "create_stream_fn_from_config",
    "create_stream_fn_with_options",
    "register_stream_fn_creator",
    "unregister_stream_fn_creator",
    "get_registered_providers",
]

