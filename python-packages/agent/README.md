# pi-agent-core

具有状态管理和事件流的通用代理。

## 功能特性

- **状态代理**：管理代理状态、消息和工具
- **事件流**：代理生命周期的实时事件通知
- **工具执行**：支持工具定义和执行
- **消息队列**：支持转向（中断）和后续消息队列
- **异步兼容**：完全支持 async/await

## 安装

```bash
pip install pi-agent-core
```

## 快速开始

```python
from pi_agent_core import Agent, Model, ThinkingLevel

# 创建代理
agent = Agent()

# 配置代理
agent.set_system_prompt("You are a helpful assistant.")
agent.set_model(Model(api="openai-chat", provider="openai", id="gpt-4o"))
agent.set_thinking_level(ThinkingLevel.HIGH)

# 订阅事件
agent.subscribe(lambda event: print(f"Event: {event['type']}"))

# 运行代理
await agent.prompt("Hello, how can you help me?")
```

## API 参考

### Agent

用于管理状态、消息和工具执行的主要代理类。

#### 构造函数

```python
agent = Agent(opts: Optional[AgentOptions] = None)
```

#### 方法

- `set_system_prompt(prompt: str)` - 设置系统提示词
- `set_model(model: Model)` - 设置要使用的 LLM 模型
- `set_thinking_level(level: ThinkingLevel)` - 设置思考/推理级别
- `set_tools(tools: List[AgentTool])` - 设置可用工具
- `subscribe(fn: Callable[[AgentEvent], None]) -> Callable[[], None]` - 订阅代理事件
- `async prompt(input: Union[str, AgentMessage, List[AgentMessage]], images: Optional[List[ImageContent]] = None)` - 向代理发送提示
- `async continue_()` - 从当前上下文继续
- `abort()` - 中止当前操作
- `async wait_for_idle()` - 等待代理变为空闲状态
- `reset()` - 重置代理状态

#### 属性

- `state: AgentState` - 获取当前代理状态
- `session_id: Optional[str]` - 获取/设置会话 ID
- `thinking_budgets: Optional[Dict[str, int]]` - 获取/设置思考预算
- `transport: str` - 获取当前传输方式
- `max_retry_delay_ms: Optional[int]` - 获取/设置最大重试延迟

### 类型定义

#### 内容类型

- `TextContent` - 文本内容
- `ImageContent` - 图片内容（base64 编码）
- `ThinkingContent` - 思考/推理内容
- `ToolCall` - 工具调用

#### 消息类型

- `UserMessage` - 用户消息
- `AssistantMessage` - 助手/LLM 响应消息
- `ToolResultMessage` - 工具执行结果消息

#### 代理状态

- `AgentState` - 当前代理状态，包括消息、工具和配置

#### 事件类型

- `AgentStartEvent` - 代理已启动
- `AgentEndEvent` - 代理已结束
- `TurnStartEvent` - 新轮次（LLM 调用+工具执行）已启动
- `TurnEndEvent` - 轮次已完成
- `MessageStartEvent` - 消息已启动
- `MessageUpdateEvent` - 消息已更新（流式传输）
- `MessageEndEvent` - 消息已结束
- `ToolExecutionStartEvent` - 工具执行已启动
- `ToolExecutionUpdateEvent` - 工具执行进度更新
- `ToolExecutionEndEvent` - 工具执行已结束

## 许可证

MIT

