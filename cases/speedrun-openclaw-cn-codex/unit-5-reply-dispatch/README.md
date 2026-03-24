# Unit 5: Reply Dispatch

> **Motto**: *先排队，再一次送达*

## 通俗解释

这个单元像一个出货码头，只有一个调度员负责控制所有出站包裹的队列。不同工人都能准备包裹，但决定发货顺序和目的地的地方只有一个。

## 背景知识

回复生成和回复投递相关，但不是同一个职责。生成负责决定“说什么”，投递负责决定“这条消息是否允许发送、是不是重复、应该送到哪里”。OpenClaw 把这两个职责拆开，是为了让回复逻辑保持专注，同时让 transport 逻辑集中管理。

去重也很关键。真实聊天 provider 可能会重试投递，用户也可能重复发送，重连还可能重放历史事件。一个没有 dedupe 的回复系统，即使模型输出正确，也会表现得很不稳定。

## 关键术语

- **Dedupe**: 防止同一条入站消息被处理两次的保护层。
- **Dispatcher**: 拥有出站排队与投递控制权的组件。
- **Final reply**: 最终完成的回复 payload，而不是流式块或 typing 指示。
- **Delivery route**: 出站目标渠道、接收者、账号和可选 thread。

## 这个单元做什么

这个单元导出了一个轻量级内存 dedupe guard、一个 dispatcher、一个简单的规则型回复生成器，以及 `dispatchInboundTurn()`。这个编排函数会先检查重复，再执行 send policy，接着生成回复，最后把最终 payload 交给 dispatcher 投递。

这和真实 OpenClaw 中 `dispatchInboundMessage()` 与更底层 delivery helpers 的职责划分是一致的。真实系统更复杂，但责任形状相同。

## 关键代码走读

- `reply-dispatch.js:1-12` 定义了内存版 dedupe 集合。
- `reply-dispatch.js:14-40` 定义 dispatcher。它负责校验 payload 文本、记录投递，并调用注入的 transport 函数。
- `reply-dispatch.js:42-60` 是模型驱动回复生成的替身。这样你可以先看清“回复边界”，而不需要先引入真正的 LLM runtime。
- `reply-dispatch.js:62-95` 是整条编排主干：去重、策略检查、生成回复、出站投递。

## 如何运行

```bash
cd /root/key_projects/learn-codebase/speedrun-openclaw-cn
npm install
node unit-5-reply-dispatch/index.js
```

## 预期输出

你应该能看到：

- 一个 `skipped: false` 的 dispatch result
- 一条提到 session 状态的 final reply
- 一条目标指向 Telegram 的 delivery record

## 练习

- 用同一个 `messageId` 连续发送两次，确认第二次返回 `reason: "duplicate"`。
- 把 `route.sendPolicy = "deny"`，确认不会产生任何 delivery。
- Explain It Back: 为什么 reply generation 应该返回 payload，而不是直接自己调用 transport？

## 调试指南

### 观察点

File: `reply-dispatch.js:14`
What to observe: transport 执行前 dispatcher 接收到的 payload。
Breakpoint or log: `console.log(payload)`

File: `reply-dispatch.js:42`
What to observe: 哪个分支最终选中了 reply 文本。
Breakpoint or log: `console.log(inboundContext.text, route.sessionKey)`

File: `reply-dispatch.js:69`
What to observe: duplicate guard 与 policy gate 的命中情况。
Breakpoint or log: `console.log(inboundContext.messageId, route.sendPolicy)`

### 常见故障

Symptom: 没有任何 delivery 被记录
Cause: 回复文本为空、message ID 重复，或者 send policy 被拒绝。
Fix: 检查 `dispatchInboundTurn()` 中几个提前返回的分支。
Verify: `dispatcher.getDeliveries()` 至少应该有一条记录。

Symptom: Delivery 发到了错误位置
Cause: `deliverRoute` 在 dispatch 开始前就已经错了。
Fix: 先检查 Unit 4 的输出。
Verify: delivery record 中的 `channel` 与 `to` 应该是预期值。

Symptom: 回复文本和输入不匹配
Cause: 规则型生成器命中了另一条分支。
Fix: 在 `makeRuleBasedReply()` 里打印 `inboundContext.text.toLowerCase()`。
Verify: 你应该能明确看到命中的是哪条分支。

### 状态检查

- 运行 `node --inspect unit-5-reply-dispatch/index.js`。
- 在 demo 文件里加 `console.table(dispatcher.getDeliveries())`。
- 用同一个 `messageId` 连续调用两次 `dispatchInboundTurn()`，直接观察 dedupe 状态。

### 隔离测试

- 把 `makeRuleBasedReply` 替换成一个永远返回 `{ text: "ok" }` 的函数。
- 提供一个会抛错的 `deliver` 函数，模拟后续可能想补的 transport failure handling。
- 用一个 `channel: "internal"` 的假 route 来运行 dispatcher，模拟 webchat 投递。
