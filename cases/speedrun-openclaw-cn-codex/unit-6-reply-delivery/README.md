# Unit 6: Reply Delivery

> **Motto**: *运行结束后才投递*

## In Plain Language

Agent loop 结束后，OpenClaw 才把 payload 变成可发送的消息。Reply delivery 负责去重、抑制空回复、选择渠道 transport，但不重新决定助理要做什么。

## Background Knowledge

- **邮局**: 只负责把已经写好的信送到正确地址；技术上是 channel transport。
- **防重章**: 同一封信重试不能发两遍；技术上是 inbound/idempotency dedupe。
- **空信拦截**: 有时 agent 明确不回复；技术上是 `NO_REPLY` 和空 payload suppression。

## Key Terminology

- **Transport**: 某个渠道的发送实现，比如 Telegram/WebChat。
- **Payload shaping**: 把 agent payload 整理成渠道可发送文本。
- **Dedupe**: 防止重试导致重复发消息。

## What This Unit Does

`reply-delivery.js` 接收 Unit 4 的 run result，过滤 text payload，移除 `NO_REPLY`，按 source 选择 transport 并发送。

## Key Code Walkthrough

- `createInboundDedupe()` 用 Set 模拟幂等去重。
- `shapeReply()` 把 payloads 合并成最终文本。
- `createReplyDelivery()` 按 channel 选择 transport。
- `deliverRunResult()` 把去重、shaping 和投递串起来。

## How to Run

```bash
node unit-6-reply-delivery/index.js
```

## Expected Output

输出会显示 delivery result 和实际发送出去的消息数组。

## Exercises

### Explain It Back

解释为什么 Reply Delivery 不应该重新调用模型或改写 agent 决策。

### Modify It

- 把 payload 文本改成 `NO_REPLY`，观察返回 `suppressed`。
- 重复调用 `deliverRunResult()` 两次，观察第二次返回 `duplicate`。

## Debug Guide

在 `shapeReply()` 和 `delivery.deliver()` 上打断点，看 payload 如何变成 transport message。
