# Unit 7: Agent Runner — 容器内部的智能体运行时

## 用大白话说

Unit 4 讲的是"门外的管理员怎么开门、递东西、收结果"。这个单元讲的是"门里的工人拿到东西后怎么干活"。容器启动后，`agent-runner` 读取 stdin 的输入，调用 Claude Agent SDK 执行查询，同时通过 MCP 工具服务器让 Claude 能发消息、创建定时任务。工人干完活后，把结果用哨兵标记包裹写到 stdout，门外的管理员（Unit 4）就能收到。

## 背景知识

NanoClaw 的容器内部运行两个关键组件：

1. **Agent Runner**（`index.ts`）：主进程，调用 Claude Agent SDK 的 `query()` API。它维护一个"查询循环"——执行完一次查询后不退出，而是等待 IPC 输入目录中的新消息文件，收到后启动新一轮查询。这样一个容器可以处理多轮对话。

2. **MCP 工具服务器**（`ipc-mcp-stdio.ts`）：一个 stdio 模式的 MCP Server，作为 Claude 的工具提供者。Claude 调用 `send_message` 工具时，MCP 服务器把请求写成 JSON 文件到 IPC 目录，主进程（Unit 6）轮询读取并执行。

**为什么用 MCP 而不是直接函数调用？** 因为 Claude Agent SDK 的工具扩展机制就是 MCP。SDK 启动 MCP 服务器作为子进程，通过 stdio 通信。这是标准化的协议，任何 MCP 兼容的工具都能接入。

## 关键术语

- **Claude Agent SDK**: Anthropic 官方的智能体 SDK，`query()` 函数是核心入口
- **MCP (Model Context Protocol)**: 模型上下文协议，标准化的工具扩展接口
- **MessageStream**: 自定义的异步迭代器，让 SDK 在一次查询期间持续接收新消息
- **哨兵标记 (Sentinel Marker)**: `---NANOCLAW_OUTPUT_START---` / `---NANOCLAW_OUTPUT_END---`，包裹 JSON 输出
- **`_close` 哨兵**: IPC 输入目录中的特殊文件，通知容器结束当前会话
- **Hook**: SDK 的钩子机制。`PreCompact` 在上下文压缩前归档对话，`PreToolUse` 在执行 Bash 前剥离密钥
- **permissionMode: 'bypassPermissions'**: 容器内的 Claude 跳过权限确认（因为已经在沙箱里了）

## 这个单元做了什么

模拟容器内部的完整运行时：
1. 从 stdin 读取输入（prompt、sessionId、secrets 等）
2. 启动 MCP 工具服务器（模拟）
3. 调用 Claude Agent SDK 执行查询（模拟）
4. 通过哨兵标记输出结果
5. 等待 IPC 输入（新消息或 `_close`）
6. 收到新消息则启动新一轮查询
7. 演示 MCP 工具：`send_message`、`schedule_task`、`list_tasks`

## 关键代码走读

### 查询循环
`main()` 中的 `while(true)` 循环是核心：`runQuery()` → `writeOutput()` → `waitForIpcMessage()` → 下一轮 `runQuery()`。每轮查询结束后发出一个 `result: null` 的输出标记，让宿主机知道"我空闲了"。收到 `_close` 哨兵则退出循环。

### MessageStream 异步迭代器
SDK 的 `query()` 接受一个 `AsyncIterable` 作为 prompt 参数。`MessageStream` 实现了 `push()` 和 `end()` 方法，让查询期间可以动态注入新消息（来自 IPC 轮询）。这是实现"容器内多轮对话"的关键。

### MCP 工具的 IPC 写入
`send_message` 工具不直接发送 WhatsApp 消息（容器没有网络访问权限），而是写一个 JSON 文件到 `/workspace/ipc/messages/`。宿主机的 IPC 监听器（Unit 6）读取并执行。原子写入（先写 `.tmp` 再 `rename`）防止读到半写的文件。

### Hooks 安全机制
- `PreToolUse` Hook：在每个 Bash 命令前注入 `unset ANTHROPIC_API_KEY ...`，防止 Claude 执行的 shell 命令泄露 API 密钥
- `PreCompact` Hook：在 SDK 压缩上下文前，把完整对话归档到 `conversations/` 目录

## 运行方式

```bash
npm run unit7
```

## 预期输出

```
--- 模拟容器启动 ---
[agent-runner] 从 stdin 读取输入...
[agent-runner] 群组: test-group, 会话: session-abc, 是否主频道: false
[agent-runner] 删除临时输入文件（含密钥）
--- MCP 工具服务器 ---
[mcp] 注册工具: send_message, schedule_task, list_tasks, pause_task, resume_task, cancel_task, register_group
[mcp] send_message("你好世界") -> 写入 IPC 文件: messages/1234-abcd.json
[mcp] schedule_task(cron "0 9 * * *") -> 写入 IPC 文件: tasks/1234-efgh.json
[mcp] list_tasks() -> 读取 current_tasks.json: 2 个任务
--- 查询循环 ---
[agent-runner] 开始查询 #1 (会话: session-abc)
[sdk] 收到 prompt: "<messages>..."
[sdk] Claude 回复: "今天天气不错！"
---NANOCLAW_OUTPUT_START---
{"status":"success","result":"今天天气不错！","newSessionId":"session-new-456"}
---NANOCLAW_OUTPUT_END---
[agent-runner] 查询 #1 完成，等待 IPC 输入...
[agent-runner] 收到新消息: "谢谢！明天呢？"
[agent-runner] 开始查询 #2 (会话: session-new-456, resumeAt: uuid-xxx)
[sdk] Claude 回复: "明天可能会下雨"
---NANOCLAW_OUTPUT_START---
{"status":"success","result":"明天可能会下雨","newSessionId":"session-new-456"}
---NANOCLAW_OUTPUT_END---
[agent-runner] 收到 _close 哨兵，退出
--- Hooks 演示 ---
[hook] PreToolUse/Bash: 注入 "unset ANTHROPIC_API_KEY CLAUDE_CODE_OAUTH_TOKEN; " 前缀
[hook] PreCompact: 归档对话到 conversations/2026-02-26-天气查询.md
--- 演示结束 ---
```

## 练习

1. **添加新的 MCP 工具**: 实现一个 `read_file` 工具，让 Claude 能读取群组目录下的文件
2. **实现消息过滤**: 在 `MessageStream.push()` 中添加逻辑，过滤掉空消息或重复消息
3. **用自己的话解释**: 为什么 `PreToolUse` Hook 要在 Bash 命令前 `unset` 环境变量？如果不这样做，Claude 执行 `env` 命令会看到什么？

## 调试指南

- **观察点**: 在 `writeOutput()` 处打断点，观察哨兵标记如何包裹 JSON
- **常见问题**: 如果查询循环不退出，检查 `_close` 哨兵文件是否被正确创建和删除
- **状态检查**: 打印 `sessionId` 和 `resumeAt`，确认会话恢复参数是否正确传递
