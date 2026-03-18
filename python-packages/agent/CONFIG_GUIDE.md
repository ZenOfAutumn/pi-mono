# Agent 配置指南

本文档介绍如何使用 Agent 的配置加载功能。

## 概述

Agent 支持从 JSON 配置文件加载配置参数，其中 `system_prompt` 可以是：
- **直接文本**：配置文件中直接设置的提示词内容
- **文件路径**：指向包含提示词的 `.txt` 或 `.md` 文件的路径（相对或绝对）

## 配置文件格式

### 基础配置结构

```json
{
  "system_prompt": "string (直接文本或文件路径)",
  "model": {
    "api": "string (API 标识符)",
    "provider": "string (提供商名称)",
    "id": "string (模型 ID)"
  },
  "thinking_level": "off|minimal|low|medium|high|xhigh",
  "temperature": "number (0.0-2.0)",
  "max_tokens": "number",
  "tools": "array (工具列表)",
  "steering_mode": "one-at-a-time|parallel",
  "follow_up_mode": "one-at-a-time|parallel"
}
```

### 系统提示词配置方式

#### 方式 1：直接在 JSON 中设置提示词

```json
{
  "system_prompt": "你是一个有帮助的AI助手。请回答用户的问题。",
  "model": {
    "api": "openai-chat",
    "provider": "openai",
    "id": "gpt-4o"
  }
}
```

#### 方式 2：从文件读取提示词（相对路径）

```json
{
  "system_prompt": "prompts/system_prompt.txt",
  "model": {
    "api": "openai-chat",
    "provider": "openai",
    "id": "gpt-4o"
  }
}
```

项目结构示例：
```
python-packages/agent/
├── config/
│   ├── agent_config.json
│   └── prompts/
│       └── system_prompt.txt
```

#### 方式 3：从文件读取提示词（绝对路径）

```json
{
  "system_prompt": "/absolute/path/to/system_prompt.txt",
  "model": {
    "api": "openai-chat",
    "provider": "openai",
    "id": "gpt-4o"
  }
}
```

#### 方式 4：从 Markdown 文件读取

```json
{
  "system_prompt": "prompts/system_guide.md",
  "model": {
    "api": "anthropic-messages",
    "provider": "anthropic",
    "id": "claude-3-opus-20240229"
  }
}
```

## 配置加载 API

### `load_agent_config(config_path: str | Path) -> Dict[str, Any]`

从 JSON 配置文件加载配置，自动解析 `system_prompt` 文件路径。

**参数：**
- `config_path`: 配置文件的路径（相对或绝对）

**返回值：**
- 包含已解析系统提示词的配置字典

**示例：**
```python
from src import load_agent_config
from pathlib import Path

config = load_agent_config("config/agent_config.json")
print(config["system_prompt"])  # 已加载的提示词内容
```

### `load_system_prompt(prompt_value: str, config_dir: Optional[Path] = None) -> str`

加载系统提示词。如果输入是文件路径（`.txt` 或 `.md`），则从文件读取；否则直接返回输入。

**参数：**
- `prompt_value`: 直接的提示词文本或文件路径
- `config_dir`: 配置文件所在目录（用于解析相对路径）

**返回值：**
- 提示词内容字符串

**示例：**
```python
from src import load_system_prompt
from pathlib import Path

# 直接文本
result = load_system_prompt("你是一个助手")
# result = "你是一个助手"

# 文件路径
config_dir = Path("config")
result = load_system_prompt("prompts/custom.txt", config_dir)
# 从 config/prompts/custom.txt 读取内容
```

### `create_agent_state_from_config(config: Dict[str, Any]) -> AgentState`

从配置字典创建 `AgentState` 实例。

**示例：**
```python
from src import load_agent_config, create_agent_state_from_config

config = load_agent_config("config/agent_config.json")
agent_state = create_agent_state_from_config(config)

print(agent_state.system_prompt)
print(agent_state.model.id)
print(agent_state.thinking_level)
```

### `create_agent_loop_config_from_config(config: Dict[str, Any]) -> AgentLoopConfig`

从配置字典创建 `AgentLoopConfig` 实例。

**示例：**
```python
from src import load_agent_config, create_agent_loop_config_from_config

config = load_agent_config("config/agent_config.json")
loop_config = create_agent_loop_config_from_config(config)

print(loop_config.temperature)
print(loop_config.max_tokens)
```

### `create_agent_context_from_config(config: Dict[str, Any]) -> AgentContext`

从配置字典创建 `AgentContext` 实例。

**示例：**
```python
from src import load_agent_config, create_agent_context_from_config

config = load_agent_config("config/agent_config.json")
context = create_agent_context_from_config(config)

print(context.system_prompt)
print(context.messages)
```

## 实际使用示例

### 示例 1：加载默认配置

```python
import asyncio
from src import load_agent_config, create_agent_state_from_config

async def main():
    # 加载配置
    config = load_agent_config("config/agent_config.json")

    # 创建 Agent 状态
    agent_state = create_agent_state_from_config(config)

    print(f"系统提示词: {agent_state.system_prompt}")
    print(f"使用模型: {agent_state.model.id}")

asyncio.run(main())
```

### 示例 2：自定义配置

创建自定义配置文件 `config/custom_config.json`：

```json
{
  "system_prompt": "prompts/coding_assistant.txt",
  "model": {
    "api": "openai-chat",
    "provider": "openai",
    "id": "gpt-4"
  },
  "temperature": 0.3,
  "max_tokens": 8000,
  "thinking_level": "high"
}
```

创建 `config/prompts/coding_assistant.txt`：

```
你是一个专业的代码助手。
你应该：
1. 提供高质量的代码示例
2. 解释代码的工作原理
3. 指出潜在的问题和改进方案
4. 遵循最佳编程实践
```

加载并使用配置：

```python
from src import load_agent_config, create_agent_loop_config_from_config

config = load_agent_config("config/custom_config.json")
loop_config = create_agent_loop_config_from_config(config)

# 使用 loop_config 运行 agent loop
```

### 示例 3：多个提示词文件

支持为不同场景创建多个提示词文件：

项目结构：
```
python-packages/agent/
├── config/
│   ├── agent_config.json
│   ├── coding_config.json
│   ├── prompts/
│   │   ├── system_prompt.txt
│   │   ├── coding_assistant.txt
│   │   └── writing_assistant.txt
```

使用不同的配置文件：

```python
from src import load_agent_config

# 通用配置
general_config = load_agent_config("config/agent_config.json")

# 编程助手配置
coding_config = load_agent_config("config/coding_config.json")
```

## 配置加载流程

1. **调用 `load_agent_config()`**
   - 读取 JSON 配置文件
   - 解析 `system_prompt` 字段

2. **处理 `system_prompt`**
   - 检查是否以 `.txt` 或 `.md` 结尾
   - 如果是文件路径，从配置目录相对位置读取
   - 如果文件存在，读取内容；否则返回原值

3. **返回完整的配置字典**
   - `system_prompt` 已解析为实际内容
   - 其他字段保持不变

## 错误处理

### 配置文件不存在

```python
from src import load_agent_config

try:
    config = load_agent_config("nonexistent.json")
except FileNotFoundError as e:
    print(f"配置文件不存在: {e}")
```

### 提示词文件不存在

如果指定的提示词文件不存在，系统会返回原始的文件路径字符串：

```python
from src import load_agent_config

config = load_agent_config("config/agent_config.json")
# system_prompt 设置为 "nonexistent_prompt.txt"
# 由于文件不存在，会返回 "nonexistent_prompt.txt"
```

## 最佳实践

1. **使用相对路径**
   - 在配置文件中使用相对于配置文件目录的相对路径
   - 这样可以轻松移动项目目录

2. **组织提示词文件**
   - 将所有提示词文件放在 `prompts/` 子目录
   - 使用描述性的文件名（如 `system_prompt.txt`, `coding_assistant.txt`）

3. **文件编码**
   - 确保提示词文件使用 UTF-8 编码
   - 支持中文、emoji 等 Unicode 字符

4. **配置版本控制**
   - 将配置文件和提示词文件提交到版本控制系统
   - 这样可以追踪配置变更历史

## 默认配置文件

项目提供了默认配置文件示例：

**位置：** `python-packages/agent/config/agent_config.json`

**内容：**
```json
{
  "system_prompt": "config/prompts/system_prompt.txt",
  "model": {
    "api": "openai-chat",
    "provider": "openai",
    "id": "gpt-4o"
  },
  "thinking_level": "off",
  "temperature": 0.7,
  "max_tokens": 2048,
  "tools": [],
  "steering_mode": "one-at-a-time",
  "follow_up_mode": "one-at-a-time"
}
```

**对应的提示词文件：** `python-packages/agent/config/prompts/system_prompt.txt`

