# Unit 4: Session Routing

> **Motto**: *身份最终会变成一把 key*

## 通俗解释

这个单元像给每段对话分配一个专属邮箱。只要标签贴对了，后面的每一封信都会知道该投到哪个格子里。

## 背景知识

大型聊天系统不只是“谁刚说话就回谁”这么简单。它还需要隔离：这个 turn 属于哪个 agent、应该进入哪个 memory store、这种会话类型是否允许回复。OpenClaw 用 canonical session key 和 send policy 来表达这些决策。

Session key 不只是一个 ID，它更像一句压缩后的路由语句。`agent:main:telegram:direct:@teal-user` 的意思是：使用 `main` agent，在 Telegram 上，处理一段 direct chat，对端是这个用户。

## 关键术语

- **Canonical**: 所有等价输入最终收敛到同一种规范格式。
- **Agent scope**: 当前 turn 应该应用哪个 agent 的记忆、配置和工具。
- **Send policy**: 当前 session 是否允许回复的 allow/deny 规则。
- **Direct vs group chat**: 对端是一位用户，还是一个共享房间/频道。

## 这个单元做什么

这个单元导出了 OpenClaw 高频使用的三个路由动作的简化版：构造 canonical session key、决定活动 agent ID、判断是否允许回复。最后由 `resolveTurnRoute()` 把这些决策打包成一个对象，交给 Unit 5 使用。

这是整个 speedrun 里最窄、最通用的一层。如果你想重建一个更小的 OpenClaw clone，这一层通常会最先被保留下来。

## 关键代码走读

- `session-routing.js:4-20` 定义了 canonical session-key builder。最重要的规则是：所有 token 在进入 key 之前都会转成小写。
- `session-routing.js:22-31` 决定 active agent。优先级依次是显式 agent、session key 中的 agent、最后才是配置里的默认 agent。
- `session-routing.js:33-50` 评估 send-policy 规则。这个 speedrun 只保留了 channel 和 chat-type 匹配，因为这已经足够展示模式。
- `session-routing.js:52-87` 把前面的决策整合起来，并生成最终的 `deliverRoute`。

## 如何运行

```bash
cd /root/key_projects/learn-codebase/speedrun-openclaw-cn
npm install
node unit-4-session-routing/index.js
```

## 预期输出

你应该能看到：

- 一个给 Telegram direct message 使用的 session key
- 一个把回复指回 `@teal-user` 的 route
- 一条针对 Slack group message 的 deny 策略结果

## 练习

- 给 `buildAgentPeerSessionKey()` 加一个 thread 后缀，比如 `:thread:release-war-room`。
- 在配置里加入第二个 agent，并把 `preferredAgentId: "ops"` 传给 `resolveTurnRoute()`。
- Explain It Back: 为什么 session key 比到处单独存 `agentId`、`channel` 和 `peerId` 更有用？

## 调试指南

### 观察点

File: `session-routing.js:9`
What to observe: builder 产出的 canonical key 长什么样。
Breakpoint or log: `console.log(params, sessionKey)`

File: `session-routing.js:22`
What to observe: 哪个来源最终决定了 agent ID。
Breakpoint or log: `console.log(preferredAgentId, sessionKey, config.agents?.default)`

File: `session-routing.js:33`
What to observe: 哪条 send-policy 规则命中了。
Breakpoint or log: `console.log(rule, channel, chatType)`

### 常见故障

Symptom: Session key 里出现意外的大写或空格
Cause: 某个 token 没有规范化。
Fix: 所有用户输入都应走 `normalizeToken()`。
Verify: 打印出的 key 全是小写。

Symptom: 本该允许的回复被拒绝了
Cause: 某条 policy 规则匹配范围过宽。
Fix: 检查 `config.session.sendPolicy.rules`。
Verify: `resolveSendPolicy()` 会为目标 case 返回 `allow`。

Symptom: 回复发给了错误的 peer
Cause: 入站数据里的 `originatingTo` 或 `from` 缺失。
Fix: 回头检查 Unit 2 或 Unit 3 输出的 inbound event。
Verify: `deliverRoute.to` 应该等于预期接收者。

### 状态检查

- 用 `node --inspect` 单步执行 `resolveTurnRoute()`。
- 在 `index.js` 里加 `console.table([resolveTurnRoute(...)])`。
- 手动切换 `chatType` 为 `direct` 和 `group`，观察 key 形状如何变化。

### 隔离测试

- 在 Node REPL 里直接调用 `buildAgentPeerSessionKey()`。
- 用不同规则数组运行 `resolveSendPolicy()`，只测试策略逻辑。
- 分别把 Unit 2 的 context 和 Unit 3 的 context 传给 `resolveTurnRoute()`，对比输出差异。
