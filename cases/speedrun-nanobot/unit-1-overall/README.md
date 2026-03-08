# Unit 1: Overall — nanobot 主流程总览

## In Plain Language
把它想成“总控台”：来自聊天渠道的请求先入队，主循环决定是否调用工具，之后把结果回发；后台还有闹钟任务（Cron）和巡检任务（Heartbeat）会主动唤醒主循环。

## Background Knowledge
- **网关编排**：把多个子系统（消息、上下文、模型、工具、调度）拼成一个完整流水线。
- **事件驱动**：消息到达才处理，定时器到期才执行。
- **同构入口**：无论用户消息、cron 还是 heartbeat，最终都走同一个 AgentLoop。

## Key Terminology
- **Gateway**：启动并编排全系统的入口（对应 nanobot `cli gateway`）。
- **AgentLoop**：工具调用主循环。
- **Cron Job**：定时任务，按计划触发。
- **Heartbeat**：周期巡检机制，按需唤醒执行。

## What This Unit Does
本单元是端到端最小可运行版：
1. 从 Unit 2 引入消息总线与会话存储；
2. 从 Unit 3 引入上下文拼装；
3. 从 Unit 6 引入 Provider 与工具注册；
4. 从 Unit 4 引入 AgentLoop 执行引擎；
5. 从 Unit 5 引入 Cron 与 Heartbeat 触发器。

你会看到三条路径共用同一执行引擎：用户聊天、定时任务、心跳任务。这正是原仓库 `nanobot/cli/commands.py::gateway()` 的核心设计。

## Key Code Walkthrough
- `unit-1-overall/index.py:23`：装配 ContextBuilder / Provider / ToolRegistry / AgentLoop。
- `unit-1-overall/index.py:50`：处理一条真实入站聊天消息。
- `unit-1-overall/index.py:62`：Cron 到期后通过 `agent.process_direct()` 执行。
- `unit-1-overall/index.py:74`：Heartbeat 先判定，再决定是否唤醒 AgentLoop。

## How to Run
```bash
python unit-1-overall/index.py
```

## Expected Output
```text
[Unit1] chat reply: 我已读取工具结果：...
[Unit1] cron result: ['我已读取工具结果：...']
[Unit1] heartbeat result: 我已读取工具结果：...
[Unit1] sessions: ['heartbeat', 'telegram:chat-007']
```

## Exercises
1. 把聊天 channel 改成 `discord`，观察 session key 如何变化。
2. 给 Cron 增加第二个 job，比较多任务执行输出。
3. **Explain It Back**：解释“为什么 cron/heartbeat 不直接访问 provider，而是复用 AgentLoop”。

## Debug Guide
### 1. Observation Points
File: `unit-1-overall/index.py:50`
What to observe: 首条用户消息如何进入总线并被主循环消费。
Breakpoint or log: 在 `agent.handle_once()` 前后打印队列长度。

File: `unit-1-overall/index.py:62`
What to observe: Cron 触发是否走同一 `process_direct()`。
Breakpoint or log: 打印 `session_key`。

File: `unit-1-overall/index.py:86`
What to observe: Heartbeat 判定结果与执行结果。
Breakpoint or log: 打印 `heartbeat_result`。

### 2. Common Failures
Symptom: 只处理聊天，不执行 cron。
Cause: job 未到期或 `run_pending` 未调用。
Fix: 用 `interval_s=0` 并显式调用 `run_pending`。
Verify: `cron result` 非空。

Symptom: heartbeat 没有结果。
Cause: HEARTBEAT 文本没有未完成项 (`- [ ]`)。
Fix: 添加一条待办。
Verify: `heartbeat result` 返回字符串而不是 `None`。

Symptom: session 列表缺少 heartbeat。
Cause: heartbeat 回调没走 `agent.process_direct`。
Fix: 检查 `run_heartbeat` 回调实现。
Verify: `sessions` 输出包含 `heartbeat`。

### 3. State Inspection
- 打印 `sessions.list_keys()` 检查三条路径是否正确落到不同会话。
- 打印 `cron.jobs` 查看 next_run 是否更新。

### 4. Isolation Testing
- 本单元可单独运行，不依赖外部 API。
- 若要缩小排障范围，可先跑 Unit 2/3/4/5/6，再回到整体编排。
