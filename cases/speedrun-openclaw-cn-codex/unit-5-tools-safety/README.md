# Unit 5: Tools Safety

> **Motto**: *能力必须先过边界*

## In Plain Language

Skills 告诉助理“你可以学会哪些能力”，但真正执行工具前还要经过 hooks、policy 和 sandbox。OpenClaw 的强工具必须能扩展，也必须能被约束。

## Background Knowledge

- **工具说明书**: Skill 是使用工具的说明和入口；技术上是 `SKILL.md` 和 skills runtime。
- **安检口**: 每次工具调用先检查规则；技术上是 tool policy。
- **隔离工作间**: 高风险操作放进受限环境；技术上是 sandbox workspace/exec。

## Key Terminology

- **Skill**: 可发现、可过滤、可注入 prompt 的能力说明。
- **Hook**: 插件在关键生命周期插入逻辑的扩展点。
- **Tool policy**: 决定工具 allow/ask/deny 的规则。
- **Sandbox**: 限制文件、进程、网络或浏览器访问的运行环境。

## What This Unit Does

`tools-safety.js` 展示 eligible skills 如何过滤，`before_tool_call` 如何改写参数，tool policy 如何决定允许/询问/拒绝，sandbox mode 如何阻止 host exec。

## Key Code Walkthrough

- `loadEligibleSkills()` 模拟 bundled/managed/workspace skills 的筛选。
- `createHookRunner()` 顺序执行 hooks。
- `resolveToolPolicy()` 给工具调用做 allow/ask/deny 判断。
- `createGuardedTool()` 把 hook 和 policy 包在真实工具外层。

## How to Run

```bash
node unit-5-tools-safety/index.js
```

## Expected Output

输出会显示 eligible skills，以及被 `before_tool_call` 加上 audit 字段后的工具结果。

## Exercises

### Explain It Back

解释为什么系统提示词里的安全提醒不能替代 tool policy 和 sandbox。

### Modify It

- 把 `calendar.create` 加入 `deny`，观察错误。
- 给 `before_tool_call` 加一个 hook，把提醒时间从 09:00 改成 08:30。

## Debug Guide

在 `createGuardedTool().call()` 内部打断点，按顺序观察 policy、hook、tool call 和 after hook。
