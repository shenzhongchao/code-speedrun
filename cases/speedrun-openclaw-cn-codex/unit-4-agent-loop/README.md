# Unit 4: Agent Loop

> **Motto**: *同一会话，一次只跑一个脑回路*

## In Plain Language

Agent loop 是 OpenClaw 真正做事的地方。它接收已经准备好的上下文，按 session 排队，运行模型和工具，发出生命周期/工具/助手事件，并让调用方等待结果。

## Background Knowledge

- **单车道施工**: 同一个会话不能同时施工两次；技术上是 per-session queue。
- **直播字幕**: 助理边想边输出事件；技术上是 assistant/tool/lifecycle stream。
- **取号等待**: 请求先 accepted，之后再等 end/error；技术上是 `agent` 和 `agent.wait` 分离。

## Key Terminology

- **Session lane**: 同一 session 的串行执行队列。
- **Lifecycle**: run 的开始、结束、错误阶段。
- **Payload**: agent loop 最终给 reply delivery 的结构化输出。

## What This Unit Does

`agent-loop.js` 模拟 `runEmbeddedPiAgent` 的最小核心：接收 context，必要时调用 `calendar.create` 工具，生成 assistant payload，并支持 `wait(runId)`。默认路径离线运行；设置 `.env` 后可以用 OpenAI-compatible API 真实调用模型，也可以切到 Pi Agent SDK 边界。

## Key Code Walkthrough

- `createSessionLane()` 用 Promise chain 保证同一 session 串行。
- `createLifecycleBus()` 保存事件并实现 `waitForEnd()`。
- `createOpenAICompatibleLLM()` 把 context 和 tool schemas 翻译成 Chat Completions 请求。
- `createPiOpenAICompatibleLLM()` 展示 `@mariozechner/pi-agent-core` / `@mariozechner/pi-ai` 的 SDK 接入点。
- `runEmbeddedAgent()` 发 start/end，调用模型和工具，产出 assistant payload。
- `createAgentRuntime()` 暴露 `agent()`、`wait()` 和 `events()`。

## How to Run

```bash
node unit-4-agent-loop/index.js
```

真实 LLM 模式：

```bash
cp .env.example .env
# 填写 OPENAI_API_KEY 后：
npm run llm:unit4
```

`OPENCLAW_LLM_SDK=openai` 使用官方 `openai` SDK；`OPENCLAW_LLM_SDK=pi` 使用 Pi Agent SDK。两种模式都走 `OPENAI_BASE_URL`、`OPENAI_API_KEY` 和 `OPENAI_MODEL`。

## Expected Output

输出包含 agent loop result、`agent.wait` result 和 lifecycle stream。

## Exercises

### Explain It Back

解释为什么 `agent.wait` 只等待结果，不应该停止正在跑的 agent。

### Modify It

- 连续提交两个同 session 的 run，打印它们的执行顺序。
- 让工具抛错，补一个 `phase: "error"` 生命周期事件。

## Debug Guide

在 `lane.enqueue()` 和 `bus.emit()` 上打断点，观察 accepted 请求如何变成 start/end 事件。
