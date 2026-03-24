# Unit 3: Channel Docking

> **Motto**: *所有渠道都插进同一个插座*

## 通俗解释

这个单元像一个万能插线板。不同设备的插头形状不一样，但只要给每个设备配上合适的转接头，墙上的同一个插座就能统一供电。

## 背景知识

OpenClaw 支持很多聊天表面。想让这件事可扩展，核心 gateway 就不能知道每个 provider 的所有细节。常见做法就是 plugin contract：每个 provider 自己提供启动逻辑和规范化逻辑，而 gateway 只维护一个 registry 和一个统一的生命周期管理器。

规范化非常重要，因为 Telegram、Slack、WhatsApp 等 provider 的字段命名都不同。Channel 层的职责就是把这些原始 provider 事件统一成一种公共对象。

## 关键术语

- **Plugin registry**: 可用 provider 适配器的目录。
- **Channel runtime**: 某个已配置 provider account 的运行时状态。
- **Normalized inbound event**: 把 provider 消息重写成共享字段后的入站事件，比如 `text`、`from`、`to`、`chatType`。
- **Account**: provider 中的一个具体身份，比如一个 Telegram bot 或一个 Slack workspace 安装实例。

## 这个单元做什么

这个单元导出一个最小 registry、一个 channel manager 和一个 Telegram 风格插件。Manager 会启动每个配置好的 account，记录 runtime snapshot，并暴露 `receive()`，把 provider 原始事件转换成后续 speedrun 所需的统一形状。

真实 OpenClaw 里还有重启、更多运行态状态字段，以及外部 plugin 加载机制。但最核心的 lesson 不变：channel-specific 代码应该在规范化边界就结束。

## 关键代码走读

- `channel-docking.js:1-24` 构建 registry，并保持 plugin 顺序可预测。
- `channel-docking.js:26-58` 是启动路径。它会遍历配置中的 account ID，创建 runtime state，并调用 plugin 的 `startAccount()` hook。
- `channel-docking.js:60-86` 暴露 `startAll()`、`snapshot()` 和 `receive()`。其中 `receive()` 是最关键的边界，因为它会把 provider 相关字段统一映射到共享事件形状。
- `channel-docking.js:89-115` 定义了 Telegram 演示插件。你可以很清楚地看到，provider-specific 知识被局部封装在插件内部。

## 如何运行

```bash
cd /root/key_projects/learn-codebase/speedrun-openclaw-cn
npm install
node unit-3-channel-docking/index.js
```

## 预期输出

你应该能看到：

- 一个 `telegram:personal` 的 runtime snapshot
- 一个 `provider: 'telegram'` 的规范化入站事件
- 已经填好的 `originatingChannel` 和 `originatingTo`

## 练习

- 加一个 `createSlackPlugin()`，把 Slack 风格原始字段映射到同一种规范化形状。
- 在 runtime snapshot 中加入 `lastError`，并模拟一个 account 启动失败。
- Explain It Back: 为什么 channel manager 应该知道如何启动 account，却不应该知道如何路由或回答消息？

## 调试指南

### 观察点

File: `channel-docking.js:12`
What to observe: registry 顺序和去重行为。
Breakpoint or log: `console.log(sorted.map((plugin) => plugin.id))`

File: `channel-docking.js:33`
What to observe: 每个 account ID 如何变成一个 runtime record。
Breakpoint or log: `console.log(channelId, accountId)`

File: `channel-docking.js:69`
What to observe: provider 原始数据穿过边界后如何变成统一 gateway 数据。
Breakpoint or log: `console.log(rawEvent, normalized)`

### 常见故障

Symptom: `Unknown channel plugin: telegram`
Cause: 插件没有注册。
Fix: 在 `createChannelRegistry([...])` 中包含 `createTelegramPlugin()`。
Verify: `registry.list()` 返回 `telegram`。

Symptom: `snapshot()` 里看不到 runtime
Cause: `startAll()` 没有被等待，或者 account 列表为空。
Fix: 使用 `await` 启动，并确认 `config.channels.telegram.accounts` 有值。
Verify: snapshot 数组里至少有一项。

Symptom: `from` 或 `to` 是 `undefined`
Cause: 原始事件映射不完整。
Fix: 检查插件里的 `normalizeInbound()`。
Verify: 打印出的规范化事件包含全部共享字段。

### 状态检查

- 运行 `node --inspect unit-3-channel-docking/index.js`。
- 启动后加一行 `console.table(manager.snapshot())`。
- 打印 `registry.list()`，查看 plugin 顺序。

### 隔离测试

- 直接在小 REPL 片段里调用 `createTelegramPlugin().normalizeInbound(...)`。
- 临时把 `startAccount()` 改成抛错函数，观察 runtime failure 行为。
- 创建一个包含两个插件的 registry，确认 `startAll()` 会初始化二者。
