# Unit 2: 消息总线

## 用大白话说

这个单元就像邮局的分拣系统。用户从各种聊天平台（Telegram、Discord、微信等）发来的消息，都先投进"收件箱"；Agent 处理完后，把回复投进"发件箱"。邮局（消息总线）负责传递，不关心信的内容。

## 背景知识

**异步队列（asyncio.Queue）**：Python 的 `asyncio.Queue` 是协程安全的先进先出队列。生产者用 `put()` 放入数据，消费者用 `get()` 取出数据。队列为空时，`get()` 会自动挂起当前协程，等有数据了再恢复——不会阻塞其他协程。

**发布-订阅模式（Pub/Sub）**：一种消息传递模式，发送方（Publisher）不直接调用接收方（Subscriber），而是把消息投入中间层（队列/总线）。好处是双方完全解耦——聊天渠道不需要知道 Agent 怎么工作，Agent 也不需要知道消息来自哪个平台。

**dataclass**：Python 3.7+ 的装饰器，自动为类生成 `__init__`、`__repr__` 等方法。用来定义纯数据结构非常简洁。

## 关键术语

- **InboundMessage**：入站消息，从聊天渠道流向 Agent 的消息对象
- **OutboundMessage**：出站消息，从 Agent 流向聊天渠道的回复对象
- **session_key**：会话键，格式为 `channel:chat_id`，用于唯一标识一个对话
- **MessageBus**：消息总线，包含入站和出站两个异步队列的中间层

## 这个单元做了什么

从 nanobot 的 `bus/` 目录提取了消息总线的核心逻辑：

1. **events.py** — 定义了两种消息类型（`InboundMessage` 和 `OutboundMessage`），每条消息都携带渠道、会话 ID、内容等路由信息
2. **bus.py** — 实现了 `MessageBus`，用两个 `asyncio.Queue` 实现双向异步通信
3. **main.py** — 模拟一个完整的消息收发流程

在真实的 nanobot 中，消息总线是所有组件的"交通枢纽"：
- 10+ 个聊天渠道（→ Unit 1 总览中会看到渠道管理器）通过它发送用户消息
- AgentLoop（→ Unit 1）从它消费消息并发布回复
- 子代理（SubagentManager）也通过它通知主 Agent

## 关键代码走读

**events.py — 消息数据结构**

```python
@dataclass
class InboundMessage:
    channel: str      # "telegram", "discord", "cli"
    sender_id: str    # 谁发的
    chat_id: str      # 哪个聊天
    content: str      # 说了什么

    @property
    def session_key(self) -> str:
        return f"{self.channel}:{self.chat_id}"
```

`session_key` 是一个计算属性，把渠道和聊天 ID 拼成唯一标识。为什么不直接用 `chat_id`？因为同一个用户可能同时在 Telegram 和 Discord 上聊天，需要区分。

**bus.py — 双向队列**

```python
class MessageBus:
    def __init__(self):
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()
```

为什么用两个队列而不是一个？因为入站和出站是两个独立的数据流。渠道往 inbound 放消息的同时，Agent 可能正在往 outbound 放回复——互不干扰。

## 运行方式

```bash
cd unit-2-message-bus
python main.py
```

## 预期输出

```
==================================================
Unit 2: 消息总线演示
==================================================

初始状态: 入站队列=0, 出站队列=0
[渠道] 用户发送: 你好，今天天气怎么样？
[渠道] 会话键: telegram:chat_42

[Agent] 收到消息: 你好，今天天气怎么样？
[Agent] 来自: telegram, 发送者: user_001
[Agent] 已回复: 今天晴天，适合出门散步！🌞

[渠道] 收到回复: 今天晴天，适合出门散步！🌞
[渠道] 回复目标: telegram:chat_42
结束状态: 入站队列=0, 出站队列=0

--- 批量消息演示 ---
入站队列积压: 3 条消息
  处理: 帮我查一下航班
  处理: 明天提醒我开会
  处理: 写一首诗
处理完毕，队列剩余: 0
```

## 练习

1. **修改练习**：给 `InboundMessage` 添加一个 `priority` 字段（int 类型，默认 0），然后修改 `MessageBus` 使用 `asyncio.PriorityQueue`，让高优先级消息先被处理。

2. **扩展练习**：实现一个 `FilteredBus`，在 `publish_inbound` 时检查消息内容是否包含敏感词，如果包含则丢弃并打印警告。

3. **用自己的话解释**：不看代码，向一个不懂编程的朋友解释"为什么 nanobot 需要消息总线，而不是让聊天渠道直接调用 Agent"。写下你的解释，然后对照本单元的"用大白话说"部分检查。

## 调试指南

**观察点**：
- 在 `publish_inbound` 和 `consume_inbound` 处加断点，观察消息何时入队、何时出队
- 打印 `bus.inbound_size` 观察队列积压情况

**常见问题**：
- `await bus.consume_inbound()` 永远不返回 → 没有人往 inbound 队列放消息，协程会一直挂起
- 消息顺序不对 → `asyncio.Queue` 是 FIFO（先进先出），检查是否有多个生产者并发写入

**状态检查**：
- `bus.inbound_size` / `bus.outbound_size` 可以随时查看队列深度
- 如果队列持续增长，说明消费者处理速度跟不上生产者
