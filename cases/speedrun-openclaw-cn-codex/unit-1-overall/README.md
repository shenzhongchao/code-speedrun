# Unit 1: Overall - OpenClaw

> **Motto**: *一次 turn，穿过整个助理内核*

## In Plain Language

这一单元跑一条完整消息：Telegram 消息进入 Gateway，变成 agent 请求，加载 session/workspace/memory/skills，进入 agent loop，调用工具，最后投递回 Telegram。

默认运行用离线规则后端。设置 `.env` 里的 `OPENCLAW_USE_REAL_LLM=true` 后，Unit 4 会用 OpenAI-compatible API 生成回复和 tool_calls，其他边界不变。

## Background Knowledge

- **控制台前台**: Gateway 像前台，负责收信、验身份、派工；技术上它是本地 WebSocket 控制平面。
- **工作台**: Workspace 像助理桌面，放身份文件、记忆、skills 和会话资料；技术上它决定 prompt 和工具上下文。
- **单车道**: 同一个 session 像一条窄路，一次只允许一个 run 通过；技术上用 per-session queue 防止历史和工具状态竞争。

## Key Terminology

- **Agent run**: 一次从用户输入到最终回复的完整执行。
- **Session key**: 会话标签，决定使用哪个 agent、workspace 和历史。
- **Lifecycle stream**: run 的 start/end/error 事件流。
- **Tool stream**: 工具调用的 start/end 事件流。

## What This Unit Does

`index.js` 导入 Unit 2-6 的真实 speedrun API，把一个 Telegram direct message 跑到底。它展示 OpenClaw 的核心不是“Gateway 转发消息”，而是“local-first agent runtime 如何把消息变成行动”。

## Key Code Walkthrough

- `unit-1-overall/index.js` 先创建 Gateway 和 Telegram channel。
- 然后用 `prepareRunContext()` 解析 agent scope、workspace、memory hits 和 skills。
- `createAgentRuntime()` 接收 context 并执行一个带工具调用的 run。
- `deliverRunResult()` 把 agent payload 整理后交给 Telegram transport。

## How to Run

```bash
node unit-1-overall/index.js
```

真实 LLM 模式：

```bash
npm run llm:overall
```

## Expected Output

你会看到 gateway plan、规范化请求、prepared context、agent loop result、`agent.wait` result 和最终 Telegram delivery。

## Exercises

### Explain It Back

用自己的话解释：为什么 Gateway 是控制平面，而不是 OpenClaw 的大脑？

### Modify It

- 把输入文本改成“不需要提醒，只总结部署状态”，观察 Unit 4 是否还调用 `calendar.create`。
- 给 `channelPolicy.deny` 加入 `calendar.create`，观察工具被拒绝时哪里抛错。

## Debug Guide

在 VS Code 里选择 `Unit 1: Overall`。建议断点放在 `prepareRunContext()`、`runtime.agent()` 和 `deliverRunResult()` 调用处，按 F10 单步观察数据如何跨 unit 传递。
