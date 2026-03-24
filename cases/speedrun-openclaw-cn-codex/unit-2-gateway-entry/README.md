# Unit 2: Gateway Entry

> **Motto**: *先规范化，再思考*

## 通俗解释

这个单元就像一个前台把凌乱的手写纸条改抄成统一的入库表单。只要表单格式统一了，后面的办公室就不需要再猜每个字段代表什么。

## 背景知识

CLI entry point 天生很吵。里面会有 flags、可选命令、默认值，以及一些必须先校验才能继续的参数。真实 OpenClaw 的入口远比这个单元复杂，但核心思想一样：先判断进程到底想做什么，再把它压缩成一个稳定的启动计划。

第二部分是请求规范化。OpenClaw 的 gateway methods 会把直接请求改写成一个 message-shaped 对象，让后续的 routing 和 reply 逻辑像处理 provider 消息一样处理它。

## 关键术语

- **Entry point**: 最先执行的代码入口，比如 `openclaw.mjs` 或 `src/entry.ts`。
- **Route-first CLI**: 先识别命令路径，再只加载需要的命令树的解析策略。
- **Message context**: 一个规范化对象，携带后续路由与回复所需字段。
- **Originating route**: 回复应该发回去的渠道或表面。

## 这个单元做什么

这个单元导出两个函数。`resolveGatewayPlan()` 把 argv 压缩成一次启动决策：运行了什么命令、使用哪个端口、是否期待回复。`buildGatewayChatContext()` 则把一次直接 gateway 请求改写成 message envelope，让它足够像 provider 流量，以便后续 speedrun 复用同一套逻辑。

这就是最重要的架构动作。OpenClaw 不会让“webchat 逻辑”和“channel 逻辑”一直分岔到底，而是尽早收敛成共享的数据形状。

## 关键代码走读

- `entry.js:3-14` 是读取 flag 和解析端口的小工具。它对应真实入口层更大规模的校验流程。
- `entry.js:16-31` 是 boot-plan reducer。最重要的输出字段是 `startMode`、`needsGateway` 和 `deliverReplies`。
- `entry.js:33-68` 是把 gateway 请求改写成 message context 的桥接层。注意输出里有 `sessionKey`、`provider`、`surface`、`originatingChannel` 和 `originatingTo`，这些字段会在 Unit 4 和 Unit 5 中继续使用。

## 如何运行

```bash
cd /root/key_projects/learn-codebase/speedrun-openclaw-cn
npm install
node unit-2-gateway-entry/index.js
```

## 预期输出

你应该能看到：

- 一个 command 为 `agent` 的 gateway plan
- 一个 `provider: 'internal'` 的规范化 context
- 一个 `run-demo-1` 的 message ID

## 练习

- 给 `resolveGatewayPlan()` 增加 `--bind <mode>` 支持，并在示例里打印出来。
- 把 `originatingChannel` 从 `internal` 改成 `telegram`，然后继续观察 Unit 4 会怎么路由。
- Explain It Back: 描述为什么直接 gateway chat 请求要被改写成 channel-like 对象，而不是走一条完全独立的 reply 路径。

## 调试指南

### 观察点

File: `entry.js:16`
What to observe: 最终选中了哪个命令 token。
Breakpoint or log: `console.log(tokens, command)`

File: `entry.js:19`
What to observe: 默认值和校验处理后的端口。
Breakpoint or log: `console.log(port)`

File: `entry.js:33`
What to observe: 规范化之后到底保留了哪些输入字段。
Breakpoint or log: `console.log(params)`

### 常见故障

Symptom: 端口仍然是 `18789`，而你本来期待自定义值
Cause: `--port` 没传，或者值非法。
Fix: 在 argv 示例里传 `--port 19090`。
Verify: 输出计划里会显示新的端口。

Symptom: `text is required`
Cause: `buildGatewayChatContext()` 拿到了空消息。
Fix: 提供一个非空 `text` 字符串。
Verify: 规范化后的 context 会被打印出来。

Symptom: 后续回复路由到了错误的 surface
Cause: `originatingChannel` 或 `originatingTo` 设置错了。
Fix: 在传递给后续单元前先检查规范化后的 context。
Verify: Unit 4 会打印出预期的 `deliverRoute`。

### 状态检查

- 运行 `node --inspect unit-2-gateway-entry/index.js`。
- 在 `entry.js:16` 放一个 `debugger;`，逐步观察 CLI 收敛过程。
- 在 `index.js` 里加 `console.table([plan, ctx])`，并排查看启动决策和消息信封。

### 隔离测试

- 在一行 REPL 里调用 `resolveGatewayPlan(["node", "openclaw", "gateway"])`。
- 通过 `node --input-type=module` 调用 `buildGatewayChatContext({ text: "hello" })`。
- 把示例 argv 改成未知命令，思考 speedrun 应该把它当成 `request` 还是直接拒绝。
