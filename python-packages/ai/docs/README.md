# AI - Python LLM 抽象层

统一 LLM API 抽象层，支持多提供商、流式响应、工具调用和成本追踪。

## 项目结构

```
python-packages/ai/
├── pyproject.toml          # 包配置和依赖
├── src/                    # 源代码
│   ├── __init__.py         # 包入口，导出所有公共 API
│   ├── types.py            # 核心类型定义
│   ├── api_registry.py     # API 提供商注册中心
│   ├── stream.py           # 流式/完成接口
│   ├── models.py           # 模型管理和成本计算
│   ├── env_api_keys.py     # 环境变量 API Key 检测
│   ├── providers/          # 提供商相关模块
│   │   ├── __init__.py
│   │   ├── transform_messages.py  # 跨提供商消息转换
│   │   └── simple_options.py      # 简化选项构建
│   └── utils/              # 工具函数
│       ├── __init__.py
│       ├── event_stream.py       # 异步事件流
│       ├── validation.py         # Tool 参数验证
│       ├── json_parse.py         # 部分 JSON 解析
│       ├── overflow.py           # 上下文溢出检测
│       └── sanitize_unicode.py   # Unicode 清理
└── test/                   # 单元测试
    ├── conftest.py         # pytest 配置
    ├── test_types.py       # 类型测试
    ├── test_api_registry.py
    ├── test_stream.py
    ├── test_models.py
    ├── test_env_api_keys.py
    ├── test_event_stream.py
    ├── test_validation.py
    ├── test_json_parse.py
    ├── test_overflow.py
    ├── test_sanitize_unicode.py
    ├── test_transform_messages.py
        └── test_simple_options.py
```

## 模块依赖关系

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              __init__.py                                     │
│                         (公共 API 导出入口)                                   │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
        ┌───────────────────────────┼───────────────────────────┬──────────────┐
        │                           │                           │              │
        ▼                           ▼                           ▼              ▼
┌───────────────┐          ┌───────────────┐          ┌───────────────┐ ┌───────────────┐
│   types.py    │          │  stream.py    │          │ api_registry  │ │   models.py   │
│  (核心类型)    │          │  (流式接口)    │          │ (提供商注册)   │ │  (模型管理)    │
└───────────────┘          └───────┬───────┘          └───────┬───────┘ └───────┬───────┘
        ▲                          │                          │                 │
        │                          ▼                          │                 │
        │                 ┌────────────────┐                  │                 │
        │                 │ get_api_provider│ ◄────────────────┘                 │
        │                 └────────────────┘                                    │
        │                          │                                            │
        │                          ▼                                            │
        │              ┌──────────────────────┐                                 │
        │              │ ApiProvider.stream() │                                 │
        │              │ ApiProvider.streamSimple()                             │
        │              └──────────────────────┘                                 │
        │                                                                     │
        └─────────────────────────────────────────────────────────────────────┘
                                    TYPE_CHECKING (类型导入)
```

### 模块间调用详解


| 模块                              | 依赖                    | 说明                               |
| --------------------------------- | ----------------------- | ---------------------------------- |
| `__init__.py`                     | 所有模块                | 统一导出公共 API                   |
| `stream.py`                       | `api_registry`, `types` | 通过注册表查找提供商，调用其流函数 |
| `models.py`                       | `types` (TYPE_CHECKING) | 模型管理，类型仅用于类型检查       |
| `api_registry.py`                 | `types` (TYPE_CHECKING) | 提供商注册，类型仅用于类型检查     |
| `env_api_keys.py`                 | 无依赖                  | 独立模块，检测环境变量             |
| `providers/transform_messages.py` | `types` (TYPE_CHECKING) | 跨提供商消息转换                   |
| `providers/simple_options.py`     | `types` (TYPE_CHECKING) | 构建流式选项                       |
| `utils/*`                         | 无依赖或仅`types`       | 独立工具函数                       |

### TYPE_CHECKING 使用模式

多个模块使用 `TYPE_CHECKING` 避免循环导入：

```python
# models.py, api_registry.py, stream.py 等
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .types import Model, Context, ...  # 仅类型检查时导入
```

**好处**：

- 运行时不导入，避免循环依赖
- 类型检查时导入，保留类型信息
- 使用字符串前向引用 `"Model"` 在类型注解中

### stream() 方法执行时序图

```
┌─────────┐     ┌───────────┐     ┌──────────────┐     ┌───────────────┐     ┌────────────────────────┐
│  用户    │     │ __init__.py│     │  stream.py   │     │api_registry.py│     │ ApiProvider (注册的)    │
└────┬────┘     └─────┬─────┘     └──────┬───────┘     └───────┬───────┘     └───────────┬────────────┘
     │                │                   │                     │                         │
     │  stream(model, │                   │                     │                         │
     │   context, opts)                   │                     │                         │
     │───────────────>│                   │                     │                         │
     │                │                   │                     │                         │
     │                │ stream(model,     │                     │                         │
     │                │   context, opts)  │                     │                         │
     │                │──────────────────>│                     │                         │
     │                │                   │                     │                         │
     │                │                   │ _resolve_api_provider(model.api)              │
     │                │                   │────────────────────>│                         │
     │                │                   │                     │                         │
     │                │                   │ get_api_provider(api)                         │
     │                │                   │────────────────────>│                         │
     │                │                   │                     │                         │
     │                │                   │                     │ 查找 _api_provider_registry
     │                │                   │                     │                         │
     │                │                   │     ApiProvider     │                         │
     │                │                   │<────────────────────│                         │
     │                │                   │                     │                         │
     │                │                   │ provider.stream(model, context, options)      │
     │                │                   │─────────────────────────────────────────────>│
     │                │                   │                     │                         │
     │                │                   │                     │        调用 LLM API      │
     │                │                   │                     │                         │
     │                │                   │     AssistantMessageEventStream               │
     │                │                   │<─────────────────────────────────────────────│
     │                │                   │                     │                         │
     │                │  AssistantMessageEventStream           │                         │
     │                │<──────────────────│                     │                         │
     │                │                   │                     │                         │
     │  AssistantMessageEventStream       │                     │                         │
     │<───────────────│                   │                     │                         │
     │                │                   │                     │                         │
     │  async for event in stream:        │                     │                         │
     │  ────────────────────────────────────────────────────────────────────────────────>│
     │                │                   │                     │        yield events     │
     │  <───────────────────────────────────────────────────────────────────────────────│
     │                │                   │                     │                         │
```

#### 完整调用流程

```
stream(model, context, options)
│
├── 1. _resolve_api_provider(model.api)
│   │
│   └── get_api_provider(api)
│       │
│       └── return _api_provider_registry.get(api)
│
├── 2. provider.stream(model, context, options)
│   │
│   └── 调用注册的提供商流函数
│       │
│       ├── 构建请求 (transform_messages 等)
│       ├── 调用 LLM API
│       └── 返回 AssistantMessageEventStream
│
└── 3. 返回 AssistantMessageEventStream
    │
    └── 用户通过 async for 消费事件流
```

#### complete() 方法调用流程

```
complete(model, context, options)
│
├── 1. stream(model, context, options)  → 返回 EventStream
│
└── 2. await stream.result()  → 等待流完成，返回 AssistantMessage
```

#### 四个核心方法对比


| 方法                | 返回类型           | 说明                               |
| ------------------- | ------------------ | ---------------------------------- |
| `stream()`          | `EventStream`      | 流式返回事件，需手动遍历           |
| `complete()`        | `AssistantMessage` | 等待完成，返回完整消息             |
| `stream_simple()`   | `EventStream`      | 同 stream()，支持 reasoning 参数   |
| `complete_simple()` | `AssistantMessage` | 同 complete()，支持 reasoning 参数 |

## 模块说明

### 核心模块

#### `types.py` - 核心类型定义

定义所有核心数据类型：

- **API 和提供商类型**: `KnownApi`, `Api`, `KnownProvider`, `Provider`
- **思考类型**: `ThinkingLevel`, `ThinkingBudgets`
- **流式选项**: `StreamOptions`, `SimpleStreamOptions`
- **内容类型**: `TextContent`, `ThinkingContent`, `ImageContent`, `ToolCall`
- **使用量类型**: `Usage`, `UsageCost`
- **消息类型**: `UserMessage`, `AssistantMessage`, `ToolResultMessage`
- **工具定义**: `Tool`, `ToolParameterSchema`
- **上下文**: `Context`
- **流式事件**: 12 种事件类型（`StartEvent`, `TextDeltaEvent`, `DoneEvent` 等）
- **模型类型**: `Model`, `ModelCost`

#### `api_registry.py` - API 提供商注册中心

管理 LLM API 提供商的注册和查询：

```python
from src import register_api_provider, get_api_provider, ApiProvider

# 注册提供商
provider = ApiProvider(
    api="my-api",
    stream=my_stream_function,
    streamSimple=my_stream_simple_function,
)
register_api_provider(provider)

# 获取提供商
provider = get_api_provider("my-api")
```

#### `stream.py` - 流式接口

主要流式 API 入口：

```python
from src import stream, complete, stream_simple, complete_simple

# 流式调用
event_stream = stream(model, context, options)
async for event in event_stream:
    print(event)

# 完成调用（返回完整消息）
message = await complete(model, context, options)

# 简化接口（支持 reasoning 参数）
message = await complete_simple(model, context, {"reasoning": "high"})
```

#### `models.py` - 模型管理

模型注册、查询和成本计算：

```python
from src import get_model, get_models, get_providers, calculate_cost

# 获取模型
model = get_model("openai", "gpt-4o")

# 获取所有提供商
providers = get_providers()

# 计算成本
cost = calculate_cost(model, usage)
```

#### `env_api_keys.py` - 环境变量 API Key

从环境变量检测 API Key：

```python
from src import get_env_api_key

# 获取 OpenAI API Key（从 OPENAI_API_KEY）
api_key = get_env_api_key("openai")
```

支持的提供商环境变量：


| 提供商     | 环境变量                                      |
| ---------- | --------------------------------------------- |
| OpenAI     | `OPENAI_API_KEY`                              |
| Anthropic  | `ANTHROPIC_API_KEY` / `ANTHROPIC_OAUTH_TOKEN` |
| Google     | `GEMINI_API_KEY`                              |
| xAI        | `XAI_API_KEY`                                 |
| Groq       | `GROQ_API_KEY`                                |
| Cerebras   | `CEREBRAS_API_KEY`                            |
| OpenRouter | `OPENROUTER_API_KEY`                          |
| Mistral    | `MISTRAL_API_KEY`                             |

### 提供商模块 (`providers/`)

#### `transform_messages.py` - 消息转换

跨提供商消息格式转换，处理：

- Thinking 块转换（跨提供商时转为文本）
- Redacted thinking 处理
- 孤立 tool call 补充合成结果
- 错误/中止消息过滤

```python
from src.providers import transform_messages

transformed = transform_messages(messages, target_model)
```

#### `simple_options.py` - 简化选项

构建和映射流式选项：

```python
from src.providers import build_base_options, adjust_max_tokens_for_thinking

# 构建基础选项
options = build_base_options(model, simple_options)

# 调整 token 预算
max_tokens, thinking_budget = adjust_max_tokens_for_thinking(
    base_max_tokens, model_max_tokens, "high"
)
```

### 工具模块 (`utils/`)

#### `event_stream.py` - 异步事件流

通用异步事件流实现：

```python
from src.utils import EventStream, AssistantMessageEventStream

# 通用事件流
stream = EventStream(
    is_complete=lambda e: e.type == "done",
    extract_result=lambda e: e.message,
)

# 助手消息事件流
stream = AssistantMessageEventStream()
async for event in stream:
    print(event)

# 获取最终结果
message = await stream.result()
```

#### `validation.py` - 参数验证

Tool 参数 JSON Schema 验证：

```python
from src.utils import validate_tool_call, validate_tool_arguments

# 验证工具调用
validated_args = validate_tool_call(tools, tool_call)
```

#### `json_parse.py` - 部分 JSON 解析

流式场景下的部分 JSON 解析：

```python
from src.utils import parse_streaming_json, extract_partial_string_value

# 解析部分 JSON
args = parse_streaming_json('{"path": "/home/user/doc')

# 提取部分字符串值
path = extract_partial_string_value(partial_json, "path")
```

#### `overflow.py` - 上下文溢出检测

检测 LLM 响应是否因上下文超限而失败：

```python
from src.utils import is_context_overflow

if is_context_overflow(message, context_window=128000):
    print("上下文溢出")
```

支持检测 20+ 提供商的溢出错误模式。

#### `sanitize_unicode.py` - Unicode 清理

移除不成对的代理字符，防止 JSON 序列化错误：

```python
from src.utils import sanitize_surrogates, is_valid_unicode

# 清理无效 Unicode
clean_text = sanitize_surrogates(text)

# 检查有效性
if not is_valid_unicode(text):
    text = sanitize_surrogates(text)
```

## 支持的 API 类型

- `openai-completions` - OpenAI Chat Completions API
- `openai-responses` - OpenAI Responses API
- `anthropic-messages` - Anthropic Messages API
- `google-generative-ai` - Google Generative AI API
- `google-vertex` - Google Vertex AI API
- `mistral-conversations` - Mistral Conversations API
- `bedrock-converse-stream` - Amazon Bedrock Converse API

## 流式事件类型


| 事件类型         | 说明         |
| ---------------- | ------------ |
| `start`          | 流开始       |
| `text_start`     | 文本块开始   |
| `text_delta`     | 文本增量     |
| `text_end`       | 文本块结束   |
| `thinking_start` | 思考块开始   |
| `thinking_delta` | 思考增量     |
| `thinking_end`   | 思考块结束   |
| `toolcall_start` | 工具调用开始 |
| `toolcall_delta` | 工具调用增量 |
| `toolcall_end`   | 工具调用结束 |
| `done`           | 完成         |
| `error`          | 错误         |

## 快速开始

```python
from src import Model, Context, Tool, stream

# 定义模型
model = Model(
    id="gpt-4o-mini",
    name="GPT-4o Mini",
    api="openai-responses",
    provider="openai",
)

# 定义工具
tools = [
    Tool(
        name="get_weather",
        description="Get weather for a location",
        parameters={
            "type": "object",
            "properties": {
                "location": {"type": "string"},
            },
            "required": ["location"],
        },
    )
]

# 创建上下文
context = Context(
    system_prompt="You are a helpful assistant.",
    messages=[{"role": "user", "content": "What's the weather in Tokyo?"}],
    tools=tools,
)

# 流式调用
event_stream = stream(model, context)
async for event in event_stream:
    if event.type == "text_delta":
        print(event.delta, end="")
    elif event.type == "toolcall_end":
        print(f"\nTool: {event.toolCall.name}")
        print(f"Args: {event.toolCall.arguments}")

# 获取结果
message = await event_stream.result()
```

## 安装

```bash
cd python-packages/ai
pip install -e .
```

## 运行测试

```bash
cd python-packages/ai
pip install pytest pytest-asyncio
python -m pytest test/ -v
```

## 依赖

- Python >= 3.10
- typing-extensions >= 4.0.0

可选依赖：

- `jsonschema >= 4.0.0` - 用于 Tool 参数验证

## License

MIT
