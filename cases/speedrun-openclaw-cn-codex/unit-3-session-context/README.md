# Unit 3: Session Context

> **Motto**: *上下文先决定助理是谁*

## In Plain Language

同一句话给不同助理、不同会话，应该得到不同上下文。OpenClaw 先用 session key 找到 agent workspace，再组装身份文件、记忆、skills 和 system prompt。

## Background Knowledge

- **办公桌**: 每个助理有自己的桌面和资料；技术上是 agent workspace。
- **随身笔记**: 有些记忆每次都带上，有些只在需要时查；技术上是 bootstrap injection 和 memory tools。
- **工具目录**: 助理先知道有哪些 skill，再按需读说明；技术上是 skills prompt 和 `SKILL.md`。

## Key Terminology

- **Bootstrap files**: `AGENTS.md`、`SOUL.md`、`USER.md`、`MEMORY.md` 等 run 前注入文件。
- **Memory recall**: 按当前问题检索到的相关长期记忆。
- **System prompt**: OpenClaw 自己组装并交给 agent runtime 的系统提示词。

## What This Unit Does

`session-context.js` 展示 session key 如何解析到 workspace，bootstrap 文件如何进入 prompt，memory 如何作为上下文被召回，skills 如何作为能力目录被列出。

## Key Code Walkthrough

- `resolveAgentScope()` 从 `agent:main:telegram:@teal-user` 得到 `main` agent 和 workspace。
- `loadBootstrapFiles()` 按固定顺序加载身份/用户/记忆文件。
- `searchMemory()` 用关键词模拟 memory recall。
- `prepareRunContext()` 输出 agent loop 可以直接使用的 transcript。

## How to Run

```bash
node unit-3-session-context/index.js
```

## Expected Output

输出会显示 agent scope、memory hits，以及传给 agent loop 的 transcript。

## Exercises

### Explain It Back

解释为什么记忆系统主要属于 Session Context，而不是 Reply Delivery。

### Modify It

- 删除 `MEMORY.md`，观察 prompt 中的 missing marker。
- 增加一条更相关的 memory entry，观察排序结果。

## Debug Guide

在 `prepareRunContext()` 里逐步执行，重点看 `agentScope`、`memoryHits` 和 `systemPrompt` 三个对象如何形成。
