# Pi 项目目录结构说明

本文档详细介绍 Pi 单体仓库的目录结构和各模块功能。

## 根目录结构

```
pi-mono/
├── .pi/                    # Pi 配置目录
├── .husky/                 # Git hooks 配置
├── .github/                # GitHub 配置（workflows、issue 模板）
├── scripts/                # 构建和发布脚本
├── packages/               # 所有子包
├── AGENTS.md               # Agent 开发规则
├── README.md               # 项目说明
├── CONTRIBUTING.md         # 贡献指南
├── package.json            # 根 package.json
├── tsconfig.json           # TypeScript 配置
├── tsconfig.base.json      # 基础 TypeScript 配置
├── biome.json              # Biome 代码格式化配置
├── test.sh                 # 测试脚本
├── pi-test.sh              # 从源码运行 pi 的脚本
└── pi-mono.code-workspace  # VS Code 工作区配置
```

## 包结构 (`packages/`)

### 1. @mariozechner/pi-ai (`packages/ai/`)

统一的多提供商 LLM API，支持 OpenAI、Anthropic、Google 等。

```
packages/ai/
├── src/
│   ├── index.ts              # 主入口
│   ├── cli.ts                # CLI 工具
│   ├── types.ts              # 核心类型定义
│   ├── models.ts             # 模型定义
│   ├── models.generated.ts   # 自动生成的模型列表
│   ├── stream.ts             # 流式 API
│   ├── oauth.ts              # OAuth 认证
│   ├── api-registry.ts       # API 注册表
│   ├── env-api-keys.ts       # 环境变量 API 密钥管理
│   ├── bedrock-provider.ts   # Bedrock 提供商
│   ├── providers/            # 各 LLM 提供商实现
│   │   ├── anthropic.ts          # Anthropic Claude
│   │   ├── openai-completions.ts # OpenAI Completions API
│   │   ├── openai-responses.ts   # OpenAI Responses API
│   │   ├── google.ts             # Google AI
│   │   ├── google-vertex.ts      # Google Vertex AI
│   │   ├── google-gemini-cli.ts  # Gemini CLI
│   │   ├── mistral.ts            # Mistral AI
│   │   ├── amazon-bedrock.ts     # Amazon Bedrock
│   │   ├── azure-openai-responses.ts
│   │   ├── openai-codex-responses.ts
│   │   └── ...                   # 其他提供商
│   └── utils/                # 工具函数
│       ├── oauth/            # OAuth 实现
│       │   ├── anthropic.ts      # Anthropic OAuth
│       │   ├── openai-codex.ts   # OpenAI Codex OAuth
│       │   ├── github-copilot.ts # GitHub Copilot OAuth
│       │   ├── google-gemini-cli.ts
│       │   └── ...
│       ├── event-stream.ts   # 事件流处理
│       ├── overflow.ts       # 溢出处理
│       ├── validation.ts     # 验证工具
│       └── ...
├── test/                     # 测试文件
├── scripts/                  # 脚本（模型生成等）
├── README.md
├── CHANGELOG.md
└── package.json
```

### 2. @mariozechner/pi-agent-core (`packages/agent/`)

Agent 运行时，提供工具调用和状态管理。

```
packages/agent/
├── src/
│   ├── index.ts       # 主入口
│   ├── agent.ts       # Agent 核心
│   ├── agent-loop.ts  # Agent 循环逻辑
│   ├── types.ts       # 类型定义
│   └── proxy.ts       # 代理工具
├── test/              # 测试文件
├── README.md
├── CHANGELOG.md
└── package.json
```

### 3. @mariozechner/pi-coding-agent (`packages/coding-agent/`)

交互式编程代理 CLI，核心产品。

```
packages/coding-agent/
├── src/
│   ├── index.ts              # 主入口
│   ├── main.ts               # 主函数
│   ├── cli.ts                # CLI 入口
│   ├── config.ts             # 配置管理
│   ├── migrations.ts         # 数据迁移
│   ├── cli/                  # CLI 相关
│   │   ├── args.ts               # 参数解析
│   │   ├── list-models.ts        # 列出模型
│   │   ├── session-picker.ts     # 会话选择器
│   │   ├── config-selector.ts    # 配置选择器
│   │   └── file-processor.ts     # 文件处理
│   ├── core/                 # 核心功能
│   │   ├── sdk.ts                # SDK
│   │   ├── exec.ts               # 执行逻辑
│   │   ├── skills.ts             # 技能系统
│   │   ├── timings.ts            # 时间统计
│   │   ├── defaults.ts           # 默认配置
│   │   ├── messages.ts           # 消息处理
│   │   ├── event-bus.ts          # 事件总线
│   │   ├── diagnostics.ts        # 诊断信息
│   │   ├── keybindings.ts        # 快捷键
│   │   ├── auth-storage.ts       # 认证存储
│   │   ├── bash-executor.ts      # Bash 执行器
│   │   ├── system-prompt.ts      # 系统提示词
│   │   ├── model-registry.ts     # 模型注册
│   │   ├── model-resolver.ts     # 模型解析
│   │   ├── slash-commands.ts     # 斜杠命令
│   │   ├── package-manager.ts    # 包管理
│   │   ├── resource-loader.ts    # 资源加载
│   │   ├── session-manager.ts    # 会话管理
│   │   ├── prompt-templates.ts   # 提示词模板
│   │   ├── settings-manager.ts   # 设置管理
│   │   ├── tools/                # 内置工具
│   │   │   ├── ls.ts                 # 列出文件
│   │   │   ├── bash.ts               # Bash 命令
│   │   │   ├── edit.ts               # 编辑文件
│   │   │   ├── read.ts               # 读取文件
│   │   │   ├── write.ts              # 写入文件
│   │   │   ├── grep.ts               # 搜索内容
│   │   │   ├── find.ts               # 查找文件
│   │   │   ├── truncate.ts           # 截断文件
│   │   │   └── edit-diff.ts          # 差异编辑
│   │   ├── compaction/           # 压缩系统
│   │   │   ├── compaction.ts
│   │   │   ├── branch-summarization.ts
│   │   │   └── ...
│   │   ├── extensions/          # 扩展系统
│   │   │   ├── loader.ts
│   │   │   ├── runner.ts
│   │   │   └── ...
│   │   └── export-html/         # HTML 导出
│   │       ├── template.html
│   │       ├── template.css
│   │       └── ...
│   ├── modes/                # 运行模式
│   │   ├── print-mode.ts         # 打印模式
│   │   ├── rpc/                  # RPC 模式
│   │   │   ├── rpc-mode.ts
│   │   │   ├── rpc-client.ts
│   │   │   └── ...
│   │   └── interactive/         # 交互模式
│   │       ├── interactive-mode.ts
│   │       ├── theme/               # 主题
│   │       └── components/          # UI 组件
│   │           ├── footer.ts
│   │           ├── diff.ts
│   │           ├── bash-execution.ts
│   │           ├── assistant-message.ts
│   │           └── ...
│   └── utils/                # 工具函数
│       ├── git.ts
│       ├── shell.ts
│       ├── clipboard.ts
│       └── ...
├── docs/                     # 文档
│   ├── providers.md              # 提供商文档
│   ├── models.md                 # 模型文档
│   ├── extensions.md             # 扩展开发
│   ├── skills.md                 # 技能文档
│   ├── keybindings.md            # 快捷键
│   ├── settings.md               # 设置
│   ├── themes.md                 # 主题
│   ├── sdk.md                    # SDK 文档
│   ├── rpc.md                    # RPC 文档
│   └── ...
├── examples/                 # 示例代码
│   ├── sdk/                      # SDK 示例
│   └── extensions/               # 扩展示例
│       ├── hello.ts
│       ├── sandbox/
│       ├── subagent/
│       ├── plan-mode/
│       └── ...
├── test/                     # 测试文件
├── README.md
├── CHANGELOG.md
└── package.json
```

### 4. @mariozechner/pi-tui (`packages/tui/`)

终端 UI 库，提供差异化渲染。

```
packages/tui/
├── src/
│   ├── index.ts             # 主入口
│   ├── tui.ts               # TUI 核心
│   ├── terminal.ts          # 终端抽象
│   ├── keys.ts              # 按键处理
│   ├── keybindings.ts       # 快捷键管理
│   ├── autocomplete.ts      # 自动完成
│   ├── fuzzy.ts             # 模糊搜索
│   ├── kill-ring.ts         # Kill ring（剪切历史）
│   ├── undo-stack.ts        # 撤销栈
│   ├── stdin-buffer.ts      # 标准输入缓冲
│   ├── terminal-image.ts    # 终端图片
│   ├── editor-component.ts  # 编辑器组件
│   └── components/          # UI 组件
│       ├── box.ts               # 盒子
│       ├── text.ts              # 文本
│       ├── input.ts             # 输入框
│       ├── editor.ts            # 编辑器
│       ├── image.ts             # 图片
│       ├── loader.ts            # 加载动画
│       ├── markdown.ts          # Markdown 渲染
│       ├── select-list.ts       # 选择列表
│       └── ...
├── test/                    # 测试文件
├── README.md
├── CHANGELOG.md
└── package.json
```

### 5. @mariozechner/pi-web-ui (`packages/web-ui/`)

用于 AI 聊天界面的 Web 组件。

```
packages/web-ui/
├── src/
│   ├── index.ts             # 主入口
│   ├── app.css              # 样式
│   ├── ChatPanel.ts         # 聊天面板
│   ├── tools/               # 工具渲染
│   │   ├── artifacts/           # 工件系统
│   │   │   ├── artifacts.ts
│   │   │   ├── PdfArtifact.ts
│   │   │   ├── ImageArtifact.ts
│   │   │   ├── MarkdownArtifact.ts
│   │   │   └── ...
│   │   └── renderers/          # 渲染器
│   │       ├── BashRenderer.ts
│   │       └── ...
│   ├── utils/               # 工具函数
│   │   ├── i18n.ts
│   │   ├── format.ts
│   │   └── ...
│   ├── dialogs/             # 对话框组件
│   │   ├── ModelSelector.ts
│   │   ├── SettingsDialog.ts
│   │   ├── SessionListDialog.ts
│   │   └── ...
│   ├── prompts/             # 提示词
│   │   └── prompts.ts
│   ├── storage/             # 存储系统
│   │   ├── stores/              # 状态存储
│   │   │   ├── sessions-store.ts
│   │   │   ├── settings-store.ts
│   │   │   └── ...
│   │   └── backends/           # 存储后端
│   │       └── indexeddb-storage-backend.ts
│   └── components/          # UI 组件
│       ├── AgentInterface.ts
│       ├── Input.ts
│       ├── Messages.ts
│       ├── MessageList.ts
│       ├── ThinkingBlock.ts
│       ├── sandbox/             # 沙箱组件
│       └── ...
├── example/                 # 示例应用
├── scripts/                 # 脚本
├── README.md
├── CHANGELOG.md
└── package.json
```

### 6. @mariozechner/pi-mom (`packages/mom/`)

Slack 机器人，将消息委托给 pi 编程代理。

```
packages/mom/
├── src/
│   ├── main.ts              # 主入口
│   ├── agent.ts             # Agent 集成
│   ├── slack.ts             # Slack 集成
│   ├── store.ts             # 数据存储
│   ├── events.ts            # 事件处理
│   ├── context.ts           # 上下文管理
│   ├── sandbox.ts           # 沙箱执行
│   ├── download.ts          # 下载功能
│   ├── log.ts               # 日志
│   └── tools/               # 工具
│       ├── bash.ts
│       ├── read.ts
│       ├── write.ts
│       ├── edit.ts
│       └── ...
├── docs/                    # 文档
├── scripts/                 # 脚本
├── dev.sh                   # 开发脚本
├── docker.sh                # Docker 脚本
├── README.md
├── CHANGELOG.md
└── package.json
```

### 7. @mariozechner/pi-pods (`packages/pods/`)

用于在 GPU pods 上管理 vLLM 部署的 CLI。

```
packages/pods/
├── src/
│   ├── index.ts             # 主入口
│   ├── cli.ts               # CLI 入口
│   ├── types.ts             # 类型定义
│   ├── config.ts            # 配置管理
│   ├── ssh.ts               # SSH 连接
│   ├── model-configs.ts     # 模型配置
│   ├── models.json          # 模型列表
│   └── commands/            # 命令
│       ├── pods.ts              # Pod 管理
│       ├── models.ts            # 模型管理
│       └── prompt.ts            # 提示词
├── docs/                    # 文档
├── scripts/                 # 脚本
├── README.md
└── package.json
```

## 其他目录

### `.pi/` 目录

Pi 的配置和扩展目录。

```
.pi/
├── git/                     # Git 相关配置
├── npm/                     # NPM 相关配置
├── prompts/                 # 提示词模板
│   ├── cl.md
│   ├── is.md
│   └── pr.md
└── extensions/              # 本地扩展
    ├── tps.ts
    ├── diff.ts
    └── ...
```

### `scripts/` 目录

构建和发布脚本。

```
scripts/
├── release.mjs              # 发布脚本
├── sync-versions.js         # 同步版本号
├── build-binaries.sh        # 构建二进制
├── cost.ts                  # 成本统计
├── session-transcripts.ts   # 会话转录
└── browser-smoke-entry.ts   # 浏览器冒烟测试
```

### `.github/` 目录

GitHub 配置。

```
.github/
├── workflows/               # GitHub Actions
│   └── ci.yml
└── ISSUE_TEMPLATE/          # Issue 模板
```

## 文件说明

| 文件 | 说明 |
|------|------|
| `AGENTS.md` | Agent 开发规则，适用于人类和 AI |
| `README.md` | 项目说明文档 |
| `CONTRIBUTING.md` | 贡献指南 |
| `package.json` | 根包配置，包含工作区定义 |
| `tsconfig.json` | TypeScript 配置 |
| `tsconfig.base.json` | 基础 TypeScript 配置 |
| `biome.json` | Biome 代码格式化和检查配置 |
| `test.sh` | 运行测试的脚本 |
| `pi-test.sh` | 从源码运行 pi 的脚本 |
| `pi-mono.code-workspace` | VS Code 工作区文件 |

## 版本管理

所有包采用**锁定步进版本控制**，即所有包始终共享相同的版本号。

- `patch`：错误修复和新功能
- `minor`：API 破坏性变更

## 测试

```bash
# 运行所有测试
./test.sh

# 运行特定包的测试
cd packages/ai && npm test

# 运行特定测试文件
npx tsx ../../node_modules/vitest/dist/cli.js --run test/stream.test.ts
```

## 构建

```bash
# 构建所有包
npm run build

# 代码检查
npm run check

