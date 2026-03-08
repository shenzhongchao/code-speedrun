# Unit 2: 消息总线与会话归档

## In Plain Language
把它想成前台分诊台：用户消息先进入“收件箱”，处理后再进入“发件箱”，并且每个用户都有自己的会话档案。

## Background Knowledge
- **异步队列**：像餐厅叫号器，先拿号先处理，生产者和消费者不用同时在线。
- **会话键 (`channel:chat_id`)**：像“平台+房间号”的组合主键，用来把不同来源的消息隔离。
- **会话历史窗口**：真实 nanobot 会按窗口截取最近消息，避免上下文无限增长。

## Key Terminology
- **Message Bus**：消息总线；负责解耦“收消息”和“处理消息”。
- **Inbound / Outbound**：入站消息 / 出站消息。
- **Session**：会话对象；保存某个聊天线程的历史。
- **Session Key**：`channel:chat_id`，会话唯一标识。

## What This Unit Does
这个单元实现了最小版 `MessageBus + SessionStore`。消息先被投递到入站队列，再被消费者取出处理，最后写入出站队列。

它对应 nanobot 的 `nanobot/bus/` 与 `nanobot/session/` 的核心职责：**路由**与**持久化边界**。你会在 Unit 4 看到 AgentLoop 如何依赖这个边界完成一轮对话。

## Key Code Walkthrough
- `runtime_bus.py`：定义 `InboundMessage` / `OutboundMessage`、`MessageBus`、`SessionStore`。
- `runtime_bus.py` 中 `InboundMessage.session_key`：把通道和 chat_id 组合成稳定键。
- `index.py`：演示“发布入站 -> 消费入站 -> 写入 Session -> 发布出站”的最小闭环。

## How to Run
```bash
python unit-2-message-bus/index.py
```

## Expected Output
```text
[Unit2] session_key: telegram:chat-42
[Unit2] history size: 1
[Unit2] outbound: 已记录：今天写周报。
```

## Exercises
1. 把 `SessionStore` 改成同时记录最近更新时间，并在输出中打印。
2. 给 `InboundMessage` 加 `metadata["thread_id"]`，并验证 session_key 策略。
3. **Explain It Back**：用 3-5 句话解释“为什么 nanobot 要用消息总线而不是直接在频道回调里调用 LLM”。

## Debug Guide
### 1. Observation Points
File: `unit-2-message-bus/index.py:19`
What to observe: 入站消息是否真的进入队列。
Breakpoint or log: 在 `await bus.publish_inbound(incoming)` 后打印 `bus.inbound.qsize()`。

File: `unit-2-message-bus/runtime_bus.py:22`
What to observe: session_key 是否稳定。
Breakpoint or log: 打断点观察 `channel/chat_id` 拼接结果。

### 2. Common Failures
Symptom: 脚本卡住不退出。
Cause: 调用了 `consume_inbound()` 但没有先 publish。
Fix: 确认先执行 `publish_inbound`。
Verify: 队列消费后能继续打印 output。

Symptom: 会话历史一直是 0。
Cause: 没有调用 `session.append()`。
Fix: 在消费到消息后立刻追加。
Verify: `history size` 变为 1。

Symptom: 不同聊天串到同一个历史里。
Cause: session_key 规则写错。
Fix: 统一使用 `channel:chat_id`。
Verify: `SessionStore.list_keys()` 显示多个独立 key。

### 3. State Inspection
- 在 `index.py` 增加 `print(sessions.list_keys())` 查看会话索引。
- 用 `print(session.history())` 检查写入结构是否符合后续单元期望。

### 4. Isolation Testing
- 单独运行 `index.py` 即可验证总线逻辑，不依赖 LLM、网络、数据库。
- 可把 `content` 改成任意字符串，观察消息在入/出站中的流转是否稳定。
