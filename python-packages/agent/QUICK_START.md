# Agent 配置快速开始指南

## 5 分钟快速上手

### 1. 使用默认配置

```python
from src import load_agent_config, create_agent_state_from_config

# 加载配置
config = load_agent_config("config/agent_config.json")

# 创建 Agent 状态
agent_state = create_agent_state_from_config(config)

print(f"使用模型: {agent_state.model.id}")
print(f"系统提示: {agent_state.system_prompt}")
```

### 2. 配置文件格式

创建 `config/my_config.json`：

```json
{
  "system_prompt": "prompts/my_prompt.txt",
  "model": {
    "api": "openai-chat",
    "provider": "openai",
    "id": "gpt-4o"
  },
  "temperature": 0.7,
  "max_tokens": 2048
}
```

创建 `config/prompts/my_prompt.txt`：

```
你是一个专业的编程助手。
你应该：
1. 提供高质量的代码示例
2. 解释代码的工作原理
3. 指出潜在的问题
```

### 3. 直接在 JSON 中设置提示词

```json
{
  "system_prompt": "你是一个有帮助的AI助手。",
  "model": {
    "api": "openai-chat",
    "provider": "openai",
    "id": "gpt-4"
  }
}
```

### 4. 创建不同类型的对象

```python
from src import (
    load_agent_config,
    create_agent_context_from_config,
    create_agent_state_from_config,
    create_agent_loop_config_from_config
)

config = load_agent_config("config/my_config.json")

# 创建 AgentContext（用于上下文管理）
context = create_agent_context_from_config(config)

# 创建 AgentState（用于状态管理）
state = create_agent_state_from_config(config)

# 创建 AgentLoopConfig（用于循环执行）
loop_config = create_agent_loop_config_from_config(config)
```

### 5. 支持的配置参数

```json
{
  "system_prompt": "string",           // 提示词或文件路径（必须）
  "model": {                           // 模型配置（必须）
    "api": "string",                   // API 标识符
    "provider": "string",              // 提供商名称
    "id": "string"                     // 模型 ID
  },
  "thinking_level": "off|minimal|low|medium|high|xhigh",  // 思考级别
  "temperature": "number",             // 0.0-2.0
  "max_tokens": "number",              // 最大输出 tokens
  "tools": [],                         // 工具列表
  "steering_mode": "string",           // 引导模式
  "follow_up_mode": "string"           // 跟进模式
}
```

## 常见场景

### 场景 1: 为不同的任务使用不同的提示词

```
config/
├── prompts/
│   ├── coding.txt           # 编程助手提示词
│   ├── writing.txt          # 写作助手提示词
│   └── analysis.txt         # 分析助手提示词
├── coding_config.json
├── writing_config.json
└── analysis_config.json
```

```python
# 加载不同的配置
coding_config = load_agent_config("config/coding_config.json")
writing_config = load_agent_config("config/writing_config.json")
```

### 场景 2: 多个模型配置

```python
openai_config = load_agent_config("config/openai_config.json")
anthropic_config = load_agent_config("config/anthropic_config.json")
```

### 场景 3: 动态配置

```python
import json
from pathlib import Path

# 手动创建配置
config_dict = {
    "system_prompt": "你的提示词",
    "model": {
        "api": "openai-chat",
        "provider": "openai",
        "id": "gpt-4"
    }
}

# 保存到文件
config_file = Path("config/dynamic_config.json")
config_file.parent.mkdir(parents=True, exist_ok=True)
config_file.write_text(
    json.dumps(config_dict, indent=2, ensure_ascii=False),
    encoding="utf-8"
)

# 加载并使用
config = load_agent_config(config_file)
```

## 文件结构建议

```
python-packages/agent/
├── config/                    # 配置目录
│   ├── agent_config.json     # 默认配置
│   ├── coding_config.json    # 编程配置
│   └── prompts/              # 提示词文件
│       ├── system_prompt.txt
│       ├── coding.txt
│       └── writing.txt
├── src/
│   ├── __init__.py
│   ├── config_loader.py      # 配置加载模块
│   ├── agent.py
│   └── ...
└── test/
    ├── test_config_loader.py
    └── ...
```

## API 参考

### `load_agent_config(config_path: str | Path) -> Dict[str, Any]`
加载 JSON 配置文件，返回包含已解析 system_prompt 的字典。

### `load_system_prompt(prompt_value: str, config_dir: Optional[Path] = None) -> str`
加载单个系统提示词。如果是文件路径则读取文件，否则返回原文本。

### `create_agent_state_from_config(config: Dict[str, Any]) -> AgentState`
从配置字典创建 AgentState 对象。

### `create_agent_context_from_config(config: Dict[str, Any]) -> AgentContext`
从配置字典创建 AgentContext 对象。

### `create_agent_loop_config_from_config(config: Dict[str, Any]) -> AgentLoopConfig`
从配置字典创建 AgentLoopConfig 对象。

## 错误处理

```python
from src import load_agent_config

try:
    config = load_agent_config("config/my_config.json")
except FileNotFoundError:
    print("配置文件不存在")
except json.JSONDecodeError:
    print("配置文件格式错误")
except ValueError as e:
    print(f"配置参数错误: {e}")
```

## 最佳实践

✅ **推荐做法**
- 使用相对路径存储 system_prompt
- 为不同场景创建单独的配置文件
- 将提示词放在 `prompts/` 子目录
- 使用 UTF-8 编码所有文件
- 提交配置文件到版本控制

❌ **避免做法**
- 硬编码提示词内容
- 使用绝对路径（会导致跨机器问题）
- 在代码中修改配置
- 忽视文件编码问题

## 运行示例

```bash
cd python-packages/agent
python3 example_config_usage.py
```

## 完整文档

查看 `CONFIG_GUIDE.md` 获取详细文档。

## 测试

```bash
cd python-packages/agent
python3 -m pytest test/test_config_loader.py -v
```

## 需要帮助？

1. 查看 `CONFIG_GUIDE.md` 中的详细说明
2. 运行 `example_config_usage.py` 查看实际示例
3. 查看 `test/test_config_loader.py` 中的测试用例
4. 查看 `IMPLEMENTATION_SUMMARY.md` 了解实现细节

