# Unit 1: Overall - OpenClaw

> **Motto**: *一条消息，穿过多层边界*

## 通俗解释

这个单元就像看一个包裹穿过整座仓库。你能看到它从哪里进来，被哪条传送带接住，贴上什么标签，最后又从哪里送出去。

## 背景知识

OpenClaw 是一个 control plane。你可以把它理解成很多聊天表面的前台。有些请求来自 web dashboard 或 CLI，有些则来自 Telegram 这样的真实 provider。关键点在于，不要让这两种输入一直走两套完全独立的流水线。系统会很快把它们都收敛成统一的消息形状，让后面的代码尽量保持 channel-agnostic。

Session key 就是对话标签。它告诉 agent 层应该使用哪条记忆通道。在 OpenClaw 里，session key 还会帮助执行一些规则，比如“Slack 群组消息不能回”或者“这个 turn 属于默认 agent”。

## 关键术语

- **Control plane**: 中央协调层。在 OpenClaw 里，gateway 负责路由、channels、nodes 和请求分发。
- **Message envelope**: 一个规范化对象，携带文本、发送者、渠道和路由提示。
- **Session key**: 类似 `agent:main:telegram:direct:@user` 这样的 canonical 字符串，用来命名一条对话通道。
- **Dispatcher**: 拥有投递顺序控制权的组件，用来把“回复生成”和“回复发送”分开。

## 这个单元做什么

这个单元会跑完整的迷你电影。先解析 gateway 启动计划，然后启动一个 Telegram 形状的 channel runtime，接收一条 provider 入站事件，把它转成 session route，再把回复发回去。之后，它还会再跑一次 control plane 发起的 turn，展示 webchat 风格输入也会汇入同一条 routing 和 reply 路径。

这就是本单元最重要的点：OpenClaw 表面很多，但系统中间层依赖的是共享形状和共享决策。

## 关键代码走读

- `index.js:15-46` 创建了迷你配置、启动计划、channel registry 和 reply dispatcher。它映射的是 gateway 启动时先准备好 config、channels 和投递基础设施的真实路径。
- `index.js:48-72` 处理一条 Telegram 风格的入站事件。Channel manager 先规范化事件，`resolveTurnRoute()` 负责附加 session key，`dispatchInboundTurn()` 再生成并投递回复。
- `index.js:74-95` 通过 `buildGatewayChatContext()` 构造 control-plane 请求。这里是最关键的汇合点：直接 gateway 流量会使用和 channel 流量同一套 routing 与 reply 机制。
- `index.js:97-106` 打印最终结果，方便你检查 unit 之间真实传递的数据形状。

## 如何运行

```bash
cd /root/key_projects/learn-codebase/speedrun-openclaw-cn
npm install
node unit-1-overall/index.js
```

## 预期输出

你应该能看到：

- 一个端口为 `18789` 的 gateway boot plan
- 一个正在运行的 Telegram runtime
- 一个 session key 为 `agent:main:telegram:direct:@teal-user` 的 Telegram route
- 一个 session key 为 `agent:main:main` 的 control-plane route
- 两条最终投递记录，一条发往 `telegram`，一条发往 `internal`

## 练习

- 把 `index.js` 里的 Telegram 消息从 `status` 改成 `build`，重新运行并比较回复文本。
- 在 Unit 3 里加入第二个 channel plugin，再在这里导入，使 Unit 1 同时处理两个 provider surface。
- Explain It Back: 用 3-5 句话解释，为什么 channel 输入和 control-plane 输入都要被转成共享的 routing 路径。如果你的解释开始变成“因为框架就是这样做的”，回去重读 `index.js:48-95`。

## 调试指南

### 观察点

File: `index.js:34`
What to observe: 在任何流量进入之前，gateway 的启动决策是什么。
Breakpoint or log: `console.log(plan)`

File: `index.js:48`
What to observe: provider 原始事件穿过 Unit 3 边界后的形状。
Breakpoint or log: `console.log(telegramInbound)`

File: `index.js:61`
What to observe: provider 事件最终拿到了什么 session key 和 delivery route。
Breakpoint or log: `console.log(telegramRoute)`

File: `index.js:89`
What to observe: control plane 发起的第二次 turn 如何走进同一条 dispatch 路径。
Breakpoint or log: `console.log(controlPlaneRoute)`

### 常见故障

Symptom: `Unknown channel plugin: telegram`
Cause: Unit 3 没有把插件接进 registry。
Fix: 检查 `createChannelRegistry([createTelegramPlugin()])`。
Verify: `manager.snapshot()` 会打印出一个 Telegram runtime。

Symptom: `text is required`
Cause: control-plane 请求创建时没有消息正文。
Fix: 给 `buildGatewayChatContext()` 传入非空 `text`。
Verify: control-plane route 会被打印出来。

Symptom: 最终只看到一条 delivery
Cause: 某个 turn 被跳过了，或者被策略拒绝了。
Fix: 检查 message ID 是否重复，并确认 `sendPolicy` 是 `allow`。
Verify: final deliveries 数组里应该有两条记录。

### 状态检查

- 运行 `node --inspect-brk unit-1-overall/index.js`，观察 `telegramInbound`、`telegramRoute` 和 `deliveries`。
- 在 `index.js:105` 下方添加 `console.table(deliveries)`，按表格查看出站记录。
- 在 `startAll()` 前后临时打印 `manager.snapshot()`，观察启动状态如何出现。

### 隔离测试

- 注释掉 control-plane 一半逻辑（`index.js:74-95`），确认 channel 路径仍然可运行。
- 把 `makeRuleBasedReply` 替换成一个永远返回 `"fixed reply"` 的内联函数，隔离“投递”和“回复生成”。
- 用一个假的 route 对象替换导入的 `resolveTurnRoute()`，把 Unit 5 完全从 Unit 4 中隔离出来测试。
