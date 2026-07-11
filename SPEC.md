# CodeGuard — 注重安全治理的 Coding Agent Harness

> Spec-Driven, Subagent-Built, Human-Owned.

---

## 1. 问题陈述

现有 AI 编码工具（Copilot、Cursor、Claude Code）让 LLM 直接操作文件系统和 shell，但安全护栏几乎全部依赖提示词约束——LLM 可能执行 `rm -rf /`、泄露密钥、或未经确认推送代码。本项目的核心命题是：**把安全治理从"提示词希望"变成"确定性代码机制"**，构建一个让 LLM 能安全编码的 harness。

**目标用户**：需要 AI 辅助编码但担心安全风险的开发者。

**为什么值得做**：当前编码 agent 的治理是最薄弱的环节。本项目通过三级护栏 + HITL 状态机 + 沙箱执行，证明治理可以是可测试、可验证的工程代码，而非模糊的提示词。

---

## 2. 用户故事

| # | 用户故事 | 验收标准 |
|---|---------|---------|
| US1 | 作为开发者，我希望危险操作（删除文件、强制推送、修改系统配置）被自动拦截，需我手动确认后才能执行 | 护栏拦截危险命令并弹出审批，审批通过才执行 |
| US2 | 作为开发者，我希望 agent 写完代码后自动运行测试，失败时根据错误信息自动修正 | 反馈闭环最多 3 轮修正，测试变绿或标记为需人工介入 |
| US3 | 作为开发者，我希望 agent 能记住项目约定和我的决策，跨会话保持一致性 | 项目约定持久化到 `.codeguard/rules.md`，每次会话自动加载 |
| US4 | 作为开发者，我希望 API key 被安全存储（不写入代码、不提交 git），首次运行引导安全录入 | key 通过 keyring 存储，不回显明文，可查看状态/更新/清除 |
| US5 | 作为开发者，我希望通过 Docker 一行命令启动整个 harness（含 WebUI），并清楚知道如何配置 key | `docker build && docker run` 可启动，README 写清 key 配置方式 |
| US6 | 作为开发者（评审者），我希望核心机制在 mock LLM 下通过确定性单元测试验证 | `pytest` 一键运行，mock 测试覆盖护栏/反馈/主循环，不依赖网络 |

---

## 3. 功能规约

### 3.1 Agent 主循环 (`core/loop.py`)

| 属性 | 描述 |
|------|------|
| 输入 | 用户任务描述 + 项目根目录路径 |
| 行为 | 组织上下文 → 调用 LLM → 解析响应中的动作 → 经治理层检查 → 分发执行 → 收集结果 → 回灌给 LLM → 判断是否停机 |
| 停机条件 | (a) LLM 返回 `FINISH` 信号；(b) 达到最大轮次（默认 20）；(c) 连续 3 轮无有效进展 |
| 错误处理 | LLM 调用失败重试 3 次（指数退避 1s/2s/4s）；动作解析失败将原始响应回灌要求重试；工具执行异常捕获后作为错误结果回灌 |

### 3.2 工具层 (`core/tools.py`)

| 工具 | 参数 | 行为 | 风险等级 |
|------|------|------|---------|
| `read_file` | `path: str` | 读取文件内容返回 | SAFE |
| `write_file` | `path: str, content: str` | 写入/覆盖文件 | HITL_REQUIRED |
| `execute_shell` | `command: str, cwd?: str` | 执行 shell 命令，返回 stdout/stderr/exit_code | 按命令分类 |
| `run_tests` | `command?: str` | 运行测试套件，返回解析后的结构化结果 | SAFE |
| `search_code` | `pattern: str, path?: str` | 基于 ripgrep 搜索代码 | SAFE |

工具注册表：声明式注册，每个工具包含 `name`、`description`、`parameters` 定义、`risk_level` 默认值。

### 3.3 治理层 (`core/governance.py`) ★ 重点维度

**三级危险分类**：

| 等级 | 示例 | 处理方式 |
|------|------|---------|
| `SAFE` | `read_file`, `search_code`, `run_tests` | 直接执行 |
| `HITL_REQUIRED` | `write_file`（项目外路径）、`git push`、`pip install`、`npm install`、网络请求 | 暂停等待人工审批 |
| `BLOCK` | `rm -rf /`、`format`、`chmod 777 /`、`git push --force main`、`sudo`、访问 `/etc/`、写入 `.env` | 自动拒绝，不可绕过 |

**护栏规则引擎**：

- 基于命令模式匹配（正则表达式 + 参数分析）的确定性规则引擎
- 规则可配置（`.codeguard/rules.yaml`），支持自定义添加/覆盖
- 对 `execute_shell` 命令做参数解析，识别危险标志（`-rf`, `--force`, `sudo` 等）
- 对 `write_file` 检查目标路径是否在项目工作目录内、是否敏感文件（`.env`, `credentials.*`）

**HITL 状态机**：

```
IDLE → AWAITING_APPROVAL → APPROVED → IDLE
                          → DENIED → IDLE
                          → TIMEOUT(60s) → IDLE
```

- 审批请求包含：动作描述、风险评估、上下文说明
- 超时默认拒绝
- 拒绝后通知 LLM 该动作被拒绝，要求提供替代方案

**沙箱执行**：

- 危险命令在受限 subprocess 中运行
- 工作目录限制为项目根目录
- 可选：限制可访问的文件系统路径（通过 `--root` 参数）

### 3.4 反馈闭环 (`core/feedback.py`)

| 组件 | 输入 | 行为 | 输出 |
|------|------|------|------|
| 测试解析器 | 测试命令输出 | 解析 pytest/unittest 输出，提取失败数、失败测试名、错误信息 | `FeedbackReport` |
| Lint 解析器 | lint 命令输出 | 解析 flake8/ruff 输出，提取错误文件和行号 | `FeedbackReport` |
| 反馈注入 | `FeedbackReport` | 格式化反馈为 LLM 可理解的文本，注入下一轮上下文 | str |

修正循环：最多 3 轮自动修正，若仍失败则标记为 `NEEDS_HUMAN` 并停止。

### 3.5 记忆层 (`core/memory.py`)

- **短期记忆**：当前会话的对话历史（消息列表），token 预算管理（保留最近 N 条消息 + 摘要）
- **长期记忆**：项目级约定文件 `.codeguard/rules.md`，跨会话持久化，每次会话自动加载到系统提示
- **上下文构建**：按优先级组装：系统提示 → 项目约定 → 近期对话历史 → 当前任务

### 3.6 配置层 (`core/config.py`)

```yaml
# .codeguard/config.yaml
llm:
  provider: deepseek
  model: deepseek-chat
  api_base: https://api.deepseek.com/v1
  temperature: 0.1
  max_tokens: 4096

agent:
  max_turns: 20
  max_fix_attempts: 3
  hitl_timeout: 60

guardrails:
  custom_rules: []  # 用户自定义规则
  blocked_patterns: []  # 额外拦截模式
```

---

## 4. 领域与机制设计

### 4.1 领域分析

Coding 领域的特性：

- **反馈信号**：测试结果（pytest/unittest）、lint 输出（flake8/ruff）、类型检查（mypy）——全部是客观、确定、可解析的结构化输出
- **危险动作**：文件系统破坏（`rm -rf`）、版本控制灾难（`git push --force`）、系统配置篡改（`sudo`/`chmod`）、凭据泄露（读取 `.env`）
- **所需工具**：文件读写、shell 执行、测试运行、代码搜索——均可通过 subprocess 和文件 I/O 实现
- **记忆需求**：项目约定、用户偏好、历史决策——文件级持久化即可满足，无需复杂向量数据库

### 4.2 重点维度：治理（Guardrails）

**为什么选治理**：

1. 治理的每个子机制（护栏规则匹配、HITL 状态转换、沙箱限制）天然是确定性代码，最契合 §A.4 的"机制必须是代码"要求
2. 三级分类 + 状态机 + 沙箱组合起来有足够的工程深度
3. 治理是当前编码 agent 中最薄弱的环节，最具实际价值

**实现方案**：

| 子机制 | 实现方式 | Mock 可测试性 |
|--------|---------|-------------|
| 危险命令分类 | 正则规则引擎 + 参数解析，`classify_command(cmd) -> RiskLevel` | 可直接传入任意命令字符串断言分类结果 |
| HITL 状态机 | `class HITLStateMachine`，状态转换表驱动 | 传入 Action 触发状态转换，断言状态和超时行为 |
| 文件路径安全 | 路径规范化 + 前缀匹配 + 敏感文件列表 | 传入路径断言是否允许写入 |
| 沙箱执行 | subprocess + 工作目录限制 | 传入命令断言执行环境受限 |

### 4.3 其他维度最低实现

| 维度 | 最低实现 |
|------|---------|
| 决策/主循环 | 组织上下文 → 调 LLM → 解析动作 → 分发 → 回灌，带轮次和停机判断 |
| 工具 | 5 个工具（读/写/shell/测试/搜索），声明式注册，风险标注 |
| 记忆 | 对话历史 + `.codeguard/rules.md` 文件持久化 |
| 反馈 | 测试/lint 输出解析器，结构化回灌 |
| 配置 | YAML 配置文件，LLM 参数 + agent 参数 + 护栏自定义 |

---

## 5. 非功能性需求

### 5.1 性能

- Agent 单轮响应时间（不含 LLM 调用）< 100ms
- 护栏分类延迟 < 10ms
- 测试解析器支持最多 1000 条测试结果

### 5.2 安全（凭据威胁模型）

**威胁模型**：

| 威胁 | 风险 | 对策 |
|------|------|------|
| API key 硬编码在源码中 | 高 — 泄露到 git 历史 | 禁止硬编码，使用 keyring 存储 |
| API key 通过环境变量 `export` 传入 | 中 — 进入 shell history | 通过 `.env` 文件加载（Python-dotenv），README 说明明文风险 |
| `.env` 文件被提交到 git | 高 — 公开泄露 | `.gitignore` 包含 `.env`，pre-commit hook 检查 |
| API key 在日志中打印 | 中 — 调试泄露 | 日志过滤，key 值脱敏（仅显示前 4 后 4 位） |
| 内存中 key 被 dump | 低 — 需本地权限 | 超出本项目范围，README 说明限制 |

**凭据存储方案**：使用 Python `keyring` 库，后端自动选择 Windows Credential Manager / macOS Keychain / Linux Secret Service。

### 5.3 可用性

- CLI 命令不超过 3 个词（`codeguard start`, `codeguard config`, `codeguard key`）
- WebUI 操作直觉化（输入框 → 发送 → 实时日志 → 审批弹窗）
- 错误信息包含可操作的修复建议

### 5.4 可观测性

- 每轮 agent 循环记录：轮次、动作、风险等级、执行结果
- 护栏拦截事件记录：时间、命令、分类、处理方式
- WebUI 通过 WebSocket 实时推送日志流

---

## 6. 系统架构

### 6.1 组件图

```
┌──────────────────────────────────────────────────┐
│                   WebUI (FastAPI)                  │
│   ┌─────────┐  ┌──────────┐  ┌────────────────┐  │
│   │ 任务输入  │  │ 实时日志流 │  │ HITL 审批面板   │  │
│   └─────────┘  └──────────┘  └────────────────┘  │
└──────────────────────┬───────────────────────────┘
                       │ REST + WebSocket
┌──────────────────────▼───────────────────────────┐
│                  Agent Loop                        │
│  ┌─────────────────────────────────────────────┐ │
│  │          Context Builder (memory.py)          │ │
│  │   对话历史 + 项目约定 + 文件快照 → prompt       │ │
│  └──────────────────┬──────────────────────────┘ │
│                     ▼                              │
│  ┌─────────────────────────────────────────────┐ │
│  │     LLM Adapter (llm.py) — 可注入 mock       │ │
│  │   DeepSeek API / MockLLM / 其他供应商         │ │
│  └──────────────────┬──────────────────────────┘ │
│                     ▼                              │
│  ┌─────────────────────────────────────────────┐ │
│  │        Action Parser (loop.py)                │ │
│  │   解析 LLM 响应 → Action(type, params)         │ │
│  └──────────────────┬──────────────────────────┘ │
│                     ▼                              │
│  ┌─────────────────────────────────────────────┐ │
│  │     Governance (governance.py) ★重点          │ │
│  │  Action → 三级分类 → BLOCK/HITL/ALLOW         │ │
│  └──────────────────┬──────────────────────────┘ │
│           ┌─────────┼─────────┐                   │
│           ▼         ▼         ▼                   │
│  ┌────────┴──┐ ┌────┴────┐ ┌┴──────────┐         │
│  │ Tool Exec  │ │ HITL    │ │ Feedback   │         │
│  │ (tools.py) │ │ 审批等待 │ │ (feedback) │         │
│  └───────────┘ └─────────┘ └────────────┘         │
└──────────────────────────────────────────────────┘
```

### 6.2 数据流

1. 用户在 WebUI 输入任务 → 创建 Session
2. Agent Loop 构建上下文 → 调用 LLM → 解析 Action
3. Action 进入 Governance → 三级分类
4. `SAFE` → 直接执行 → 结果回灌；`HITL` → 等待 WebUI 审批；`BLOCK` → 拒绝并通知 LLM
5. 执行后触发 Feedback 解析 → 结果注入下一轮上下文
6. 循环直到 `FINISH` 或超限

### 6.3 外部依赖

| 依赖 | 用途 | 替代方案 |
|------|------|---------|
| DeepSeek API | LLM 推理 | 任何 OpenAI 兼容 API |
| ripgrep (`rg`) | 代码搜索 | 可选，纯 Python 回退 |
| pytest | 测试运行 | 用户项目自带 |
| keyring | 凭据存储 | 环境变量回退 |

---

## 7. 数据模型

| 实体 | 字段 | 类型 | 说明 |
|------|------|------|------|
| **Action** | `type`, `params: dict`, `risk_level`, `id: str` | dataclass | LLM 输出的一个动作 |
| **Message** | `role: str`, `content: str`, `timestamp: float` | dataclass | 对话中的一条消息 |
| **Session** | `id: str`, `messages: list[Message]`, `project_root: str`, `max_turns: int`, `status: str` | dataclass | 一次 agent 会话 |
| **GuardrailRule** | `pattern: str`, `risk_level: str`, `description: str` | dataclass | 一条护栏规则 |
| **ApprovalRequest** | `action_id: str`, `action: Action`, `risk_detail: str`, `status: str`, `timestamp: float` | dataclass | 等待审批的操作 |
| **FeedbackReport** | `source: str`, `failures: list[dict]`, `summary: str`, `is_clean: bool` | dataclass | 测试/lint 反馈结果 |
| **ToolDef** | `name: str`, `description: str`, `parameters: dict`, `risk_level: str` | dataclass | 工具注册定义 |

---

## 8. 凭据与分发设计

### 8.1 凭据管理

**存储方案**：Python `keyring` 库，自动适配操作系统：
- Windows → Windows Credential Manager
- macOS → Keychain
- Linux → Secret Service / D-Bus

**首次录入流程**：
```
$ codeguard key set
Enter your DeepSeek API key: ********
Key stored successfully in Windows Credential Manager.
```

**查看状态**：
```
$ codeguard key status
DeepSeek API key: configured (****-****-abcd)  ← 仅显示后 4 位
```

**更新/清除**：
```
$ codeguard key update   # 重新录入
$ codeguard key clear    # 清除存储的 key
```

**环境变量回退**：若 keyring 不可用，回退读取 `DEEPSEEK_API_KEY` 环境变量（通过 `.env` 文件加载），README 中写明明文风险。

### 8.2 分发：Docker 容器

**Dockerfile 结构**：
- 基于 `python:3.12-slim`
- 安装系统依赖（ripgrep）
- 安装 Python 依赖
- 复制源码
- `ENTRYPOINT ["codeguard", "serve"]` 启动 WebUI

**运行命令**：
```bash
docker build -t codeguard .
docker run -p 8080:8080 -v $(pwd):/workspace codeguard
```

**key 在 Docker 中的安全配置**：
- 推荐：在宿主机用 `codeguard key set` 预先配置 keyring，Docker 不直接处理 key
- 备选：挂载 `.env` 文件到容器（`-v .env:/app/.env`），README 说明明文风险
- 禁止：在 Dockerfile 中写死 key、通过 `-e` 传入（会进入 shell history）

### 8.3 已知限制

- Docker 镜像约 200MB（Python slim + 依赖）
- 仅支持 x86_64 架构
- 需要宿主机安装 Docker Engine 20.10+
- 沙箱隔离依赖宿主机文件系统权限，非完全隔离

---

## 9. 技术选型与理由

| 选择 | 理由 |
|------|------|
| **Python** | AI 生态最成熟，OpenAI SDK 直接兼容 DeepSeek；pytest 测试生态完善；keyring 跨平台凭据方案成熟 |
| **DeepSeek** | 国内可直接访问，兼容 OpenAI API 格式，价格低廉，代码能力经社区验证 |
| **FastAPI** | Python 异步 Web 框架，原生支持 WebSocket（实时日志推送），自动生成 API 文档 |
| **Docker** | 跨平台分发最简单，CI 友好，隔离性好 |
| **keyring** | 跨平台凭据存储，自动适配 Windows/macOS/Linux 原生钥匙串 |
| **pytest** | Python 标准测试框架，输出可解析，生态丰富 |

---

## 10. 验收标准

| 功能 | 验收标准 |
|------|---------|
| Agent 主循环 | 给定任务 → agent 能执行多轮工具调用 → 最终返回 FINISH 或超限停机 |
| 护栏拦截 | 危险命令（`rm -rf /`）被 BLOCK，安全命令（`ls`）被 ALLOW |
| HITL 审批 | 中等危险操作触发审批请求，审批通过后执行，拒绝后不执行 |
| 反馈闭环 | 注入失败测试 → agent 读取失败信息 → 修正代码 → 测试变绿 |
| 记忆持久化 | 写入 `.codeguard/rules.md` → 新会话自动加载规则 |
| 凭据安全 | key 不出现源码/git 历史/日志中；状态查看不回显明文 |
| Docker 分发 | `docker build && docker run` 可启动 WebUI |
| Mock 单元测试 | `pytest` 不依赖网络/真实 LLM，覆盖护栏、反馈、主循环 |
| 机制演示 | 三个场景（护栏拦截、反馈修正、重点维度）可确定性复现 |
| WebUI | 浏览器访问 `localhost:8080`，可输入任务、查看日志、审批操作 |

---

## 11. 风险与未决问题

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| LLM 输出格式不稳定，动作解析失败 | 高 | 在 prompt 中要求严格 JSON 格式；解析失败时回灌原始响应要求重试；提供 few-shot 示例 |
| 护栏规则覆盖不全，新型危险命令绕过 | 中 | 默认拒绝未知命令类型（`deny-by-default`）；规则可扩展；README 说明护栏非 100% 安全 |
| 沙箱隔离不彻底 | 中 | Docker 容器本身提供一层隔离；README 明确声明沙箱局限 |
| DeepSeek API 不稳定或限流 | 中 | 指数退避重试；支持配置其他 OpenAI 兼容供应商 |
| 记忆文件冲突（多会话同时写） | 低 | 文件锁 + 会话级写入队列 |
| token 预算管理不精确 | 低 | 使用 tiktoken 计数；超出时自动截断最早消息 |