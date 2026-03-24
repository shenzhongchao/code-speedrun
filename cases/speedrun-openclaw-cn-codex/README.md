> **源码**: [openclaw](https://github.com/openclaw/openclaw) - 于 2026-03-13 克隆

# Speedrun OpenClaw 中文版

这个 speedrun 把一个很大的 TypeScript monorepo 拆成 5 个可运行单元，沿着 OpenClaw 的核心助理链路学习：

1. Gateway 或 UI 输入进入控制平面。
2. Channel 插件把不同提供方的事件规范化。
3. 路由逻辑把身份信息变成 agent 作用域下的 session key。
4. Reply dispatch 决定是否回复、是否去重，以及把回复送到哪里。

生成的代码刻意保持很小，但每个单元都对应到 OpenClaw 真实架构中的关键边界。

## 快速开始

```bash
cd /root/key_projects/learn-codebase/speedrun-openclaw-cn
npm install
npm run all
```

也可以逐个运行单元：

```bash
node unit-1-overall/index.js
node unit-2-gateway-entry/index.js
node unit-3-channel-docking/index.js
node unit-4-session-routing/index.js
node unit-5-reply-dispatch/index.js
```

## 单元总览表

| 单元 | 标题 | 口号 | 核心概念 |
|------|------|------|----------|
| 1 | Overall | *一条消息，穿过多层边界* | 使用 Unit 2-5 导出的 API 跑完整助理链路 |
| 2 | Gateway Entry | *先规范化，再思考* | CLI 与控制平面请求先变成统一消息形状 |
| 3 | Channel Docking | *所有渠道都插进同一个插座* | Channel 插件如何注册、启动并规范化入站事件 |
| 4 | Session Routing | *身份最终会变成一把 key* | 提供方元数据如何变成 agent 作用域 session 与策略决策 |
| 5 | Reply Dispatch | *先排队，再一次送达* | 去重、生成回复，并通过统一投递口送出 |

## 单元地图

Unit 1: Overall - OpenClaw
  Motto:        一条消息，穿过多层边界
  Concept:      端到端主流程 - 导入并编排 Unit 2-5 的模块
  Teaches:      Gateway 输入与渠道输入如何汇入同一条路由与回复路径
  Source files: `src/cli/gateway-cli/run.ts`, `src/gateway/server.impl.ts`, `src/gateway/server-methods/chat.ts`, `src/gateway/server-channels.ts`, `src/routing/session-key.ts`, `src/auto-reply/dispatch.ts`
  Imports from: Unit 2 (gateway entry), Unit 3 (channel docking), Unit 4 (session routing), Unit 5 (reply dispatch)
  Runs as:      `node unit-1-overall/index.js`
  Prereqs:      None

Unit 2: Gateway Entry
  Motto:        先规范化，再思考
  Concept:      CLI 与控制平面请求会先收敛成统一消息信封
  Teaches:      为什么 OpenClaw 要把 gateway chat/send 请求改写成统一形状
  Source files: `src/entry.ts`, `src/cli/run-main.ts`, `src/cli/program/command-registry.ts`, `src/gateway/server-methods/chat.ts`
  Exports:      `resolveGatewayPlan()`, `buildGatewayChatContext()`
  Runs as:      `node unit-2-gateway-entry/index.js`
  Prereqs:      None

Unit 3: Channel Docking
  Motto:        所有渠道都插进同一个插座
  Concept:      插件注册表与 channel manager 启动账号并产出规范化入站事件
  Teaches:      很不相同的聊天提供方如何挂在统一的 gateway 合同后面
  Source files: `src/channels/plugins/index.ts`, `src/gateway/server-channels.ts`, `src/plugins/runtime/index.ts`
  Exports:      `createChannelRegistry()`, `createChannelManager()`, `createTelegramPlugin()`
  Runs as:      `node unit-3-channel-docking/index.js`
  Prereqs:      None

Unit 4: Session Routing
  Motto:        身份最终会变成一把 key
  Concept:      渠道、对端与 agent 元数据会收敛为 canonical session key 与 send-policy 决策
  Teaches:      OpenClaw 如何按 agent 和会话形状隔离记忆与行为
  Source files: `src/routing/session-key.ts`, `src/agents/agent-scope.ts`, `src/sessions/send-policy.ts`
  Exports:      `buildAgentPeerSessionKey()`, `resolveSessionAgentId()`, `resolveSendPolicy()`, `resolveTurnRoute()`
  Runs as:      `node unit-4-session-routing/index.js`
  Prereqs:      Unit 3 有帮助，因为它提供了入站事件形状

Unit 5: Reply Dispatch
  Motto:        先排队，再一次送达
  Concept:      去重、回复生成与出站投递统一集中在一个 dispatcher 中
  Teaches:      为什么 OpenClaw 要把回复生产与回复投递拆开
  Source files: `src/auto-reply/dispatch.ts`, `src/auto-reply/reply/dispatch-from-config.ts`, `src/auto-reply/reply/reply-dispatcher.ts`
  Exports:      `createInboundDedupe()`, `createReplyDispatcher()`, `makeRuleBasedReply()`, `dispatchInboundTurn()`
  Runs as:      `node unit-5-reply-dispatch/index.js`
  Prereqs:      Unit 4

## 架构图

```text
CLI / Control UI 请求 ----> Unit 2: Gateway entry ---------+
                                                          |
Provider 事件 ----------> Unit 3: Channel docking ------->|
                                                          v
                                                Unit 4: Session routing
                                                          |
                                                          v
                                                Unit 5: Reply dispatch
                                                          |
                                                          v
                                                Telegram / WebChat / 其他表面
```

## 覆盖范围

已覆盖：
- `src/entry.ts`, `src/cli/run-main.ts`, `src/cli/program/`
- `src/gateway/server.impl.ts`, `src/gateway/server-methods/chat.ts`, `src/gateway/server-channels.ts`
- `src/channels/plugins/`
- `src/routing/session-key.ts`, `src/agents/agent-scope.ts`, `src/sessions/send-policy.ts`
- `src/auto-reply/dispatch.ts`, `src/auto-reply/reply/dispatch-from-config.ts`, `src/auto-reply/reply/reply-dispatcher.ts`

跳过：
- `apps/`, `ui/`, `Swabble/` - 这些是 gateway 外围产品壳，不是最窄的助理主链路
- `docs/`, `assets/`, `changelog/` - 文档与打包素材
- `scripts/`, `git-hooks/`, release 文件、Docker 文件 - 构建和发布自动化
- `extensions/`, `packages/`, `skills/` - 很重要，但不在这次最短可运行学习主线内

没有单独拆成 unit，而是穿插进其他 unit：
- `src/config/` - 出现在 Unit 2 和 Unit 4
- `src/plugins/runtime/` - 出现在 Unit 3
- `src/logging/`, `src/infra/` - 在需要解释行为时引用，但不单独成课

对于“理解一次 assistant turn”这个学习目标，没有发现明显架构缺口。当前最大的省略项是平台打包能力与大量可选集成，它们适合在第二轮继续扩展。

## 学习路径

如果你想先看全貌，从 Unit 1 开始。如果你最想理解 OpenClaw 如何把 CLI/UI 请求变成统一形状，从 Unit 2 开始。如果你更关心渠道接入，从 Unit 3 开始。Unit 4 和 Unit 5 是重建一个更小型 OpenClaw 风格助理时最核心的实现主干。

## 验证

已在这台机器上通过下面命令验证：

```bash
node scripts/run-all.js
```

该命令已于 2026-03-13 在 Node `v22.17.0` 下成功运行。
