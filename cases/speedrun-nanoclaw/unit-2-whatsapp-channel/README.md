# Unit 2: WhatsApp 通道 — 消息收发与连接管理

## 用大白话说

这个单元就像一个电话接线员：负责接听电话（接收 WhatsApp 消息）、转接电话（把消息传给系统）、回拨电话（发送回复）。如果电话线断了，接线员会自动重新接上。

## 背景知识

NanoClaw 使用 [Baileys](https://github.com/WhiskeySockets/Baileys) 库连接 WhatsApp。Baileys 是一个非官方的 WhatsApp Web API 客户端，它模拟浏览器端的 WhatsApp Web 来收发消息。

关键设计：NanoClaw 实现了一个 `Channel` 接口抽象，WhatsApp 只是其中一种实现。这意味着可以轻松添加 Telegram、Slack 等其他通道（事实上社区已经通过 skills 实现了）。

**为什么用轮询而不是推送？** Baileys 本身是事件驱动的（收到消息会触发回调），但 NanoClaw 在此之上加了一层轮询：消息先存入 SQLite，然后主循环定期检查。这样做的好处是：即使进程崩溃重启，未处理的消息不会丢失。

## 关键术语

- **Baileys**: 非官方 WhatsApp Web API 库，通过 WebSocket 连接 WhatsApp 服务器
- **Channel 接口**: NanoClaw 的通道抽象，定义了 `connect()`、`sendMessage()`、`isConnected()` 等方法
- **JID (Jabber ID)**: WhatsApp 的聊天标识。`xxx@s.whatsapp.net` 是私聊，`xxx@g.us` 是群聊
- **LID (Linked ID)**: WhatsApp 的新式用户标识，需要翻译成传统的手机号 JID
- **fromMe**: 消息是否由当前登录的账号发送，用于区分用户消息和机器人消息
- **Presence**: WhatsApp 的在线状态协议，包括"正在输入"指示器

## 这个单元做了什么

模拟了 WhatsApp 通道的核心行为：
1. 连接和断线重连
2. 消息接收和分发
3. 消息发送（带助手名前缀）
4. 断线时的消息队列
5. 触发词匹配和过滤

## 关键代码走读

### Channel 接口
所有通道必须实现 5 个方法：`connect()`、`sendMessage()`、`isConnected()`、`ownsJid()`、`disconnect()`。`ownsJid()` 用于路由——当系统要发消息到某个 JID 时，它会遍历所有通道找到"拥有"这个 JID 的那个。

### 消息前缀
当助手和用户共用一个 WhatsApp 号码时，机器人的回复会加上 `Andy: ` 前缀，这样用户能区分哪些是机器人说的。如果助手有自己的号码（`ASSISTANT_HAS_OWN_NUMBER=true`），则不加前缀。

### 断线重连
连接断开时，如果不是因为"被登出"（`DisconnectReason.loggedOut`），就自动重连。重连期间的消息会被放入 `outgoingQueue`，连接恢复后自动刷新发送。

## 运行方式

```bash
npm run unit2
```

## 预期输出

```
[通道] WhatsApp 通道已创建
[通道] 连接中...
[通道] 已连接
[通道] ownsJid("chat@g.us") = true
[通道] ownsJid("tg:12345") = false
--- 模拟收到群聊消息 ---
[回调] 收到消息: chat-group@g.us, 发送者: 李四, 内容: "@Andy 帮我查一下"
--- 模拟收到私聊消息 ---
[回调] 收到消息: user@s.whatsapp.net, 发送者: 王五, 内容: "你好"
--- 发送回复 ---
[通道] 发送: chat-group@g.us <- "Andy: 好的，我来查一下"
--- 模拟断线 ---
[通道] 连接断开
[通道] 断线期间发送消息...
[通道] 消息已加入队列 (队列长度: 1)
--- 模拟重连 ---
[通道] 已重连
[通道] 刷新队列: 发送 1 条积压消息
[通道] 队列消息已发送: user@s.whatsapp.net
--- 演示结束 ---
```

## 练习

1. **添加消息过滤**: 修改 `onMessage` 回调，只处理包含文字内容的消息（跳过图片、视频等）
2. **实现 Telegram 通道**: 创建一个 `TelegramChannel` 类实现 `Channel` 接口，`ownsJid()` 检查 `tg:` 前缀
3. **用自己的话解释**: 为什么 NanoClaw 要在消息前加 `Andy:` 前缀？如果不加会出什么问题？

## 调试指南

- **观察点**: 在 `sendMessage()` 中打断点，观察 `connected` 状态如何决定是直接发送还是入队
- **常见问题**: 如果消息发不出去，检查 `isConnected()` 返回值和 `outgoingQueue` 长度
- **状态检查**: 打印 `outgoingQueue` 数组，确认断线期间的消息是否正确积压
