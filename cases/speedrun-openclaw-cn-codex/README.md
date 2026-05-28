> **源码**: [openclaw](https://github.com/openclaw/openclaw) - 于 2026-03-13 克隆

# Speedrun OpenClaw 中文版

OpenClaw 是一个 local-first 的个人 AI 助理平台。它能接入 Telegram、Slack、Discord、WebChat、macOS/iOS/Android nodes 等表面，但这些表面不是产品核心；Gateway 只是控制平面，真正的核心是一次 agent run 如何把消息变成上下文、模型推理、工具调用、流式事件、持久化和最终回复。

这个 speedrun 围绕“一个真实 assistant turn”重做成 6 个可运行单元。Unit 1 先跑完整链路；Unit 2-6 再分别拆开 Gateway、session/workspace/context/memory、agent loop、tools/skills/hooks/safety、reply delivery。

## 快速开始

```bash
cd /root/key_projects/learn-codebase/cases/speedrun-openclaw-cn-codex
npm run all
```

默认运行使用离线规则后端，方便学习队列、tool events 和投递边界。要接入真实 LLM，先创建本地 `.env`：

```bash
cp .env.example .env
```

然后填写 OpenAI-compatible 配置：

```bash
OPENCLAW_USE_REAL_LLM=true
OPENCLAW_LLM_SDK=openai
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-mini
```

`OPENCLAW_LLM_SDK=openai` 使用官方 `openai` SDK 走 Chat Completions；`OPENCLAW_LLM_SDK=pi` 使用 `@mariozechner/pi-agent-core` + `@mariozechner/pi-ai` 的 Pi Agent 边界。两种模式都读取同一套 OpenAI-compatible 环境变量。

```bash
npm run llm:unit4
npm run llm:overall
```

也可以逐个运行单元：

```bash
node unit-1-overall/index.js
node unit-2-gateway-entry/index.js
node unit-3-session-context/index.js
node unit-4-agent-loop/index.js
node unit-5-tools-safety/index.js
node unit-6-reply-delivery/index.js
```

## 单元总览表

| 单元 | 标题 | 口号 | 核心概念 |
|------|------|------|----------|
| 1 | Overall | *一次 turn，穿过整个助理内核* | 使用 Unit 2-6 导出的 API 跑完整 assistant turn |
| 2 | Gateway Entry | *Gateway 收信，不替 agent 思考* | WS/CLI/channel 输入如何收敛成 `agent` 请求 |
| 3 | Session Context | *上下文先决定助理是谁* | session、workspace、bootstrap、memory、skills 如何进入 run |
| 4 | Agent Loop | *同一会话，一次只跑一个脑回路* | 队列、生命周期、tool events、assistant payload 和 `agent.wait` |
| 5 | Tools Safety | *能力必须先过边界* | skills 发现、hooks、tool policy、sandbox 如何约束工具 |
| 6 | Reply Delivery | *运行结束后才投递* | 去重、NO_REPLY 抑制、渠道 transport 和最终投递 |

## 单元地图

Unit 1: Overall - OpenClaw
  Motto:        一次 turn，穿过整个助理内核
  Concept:      端到端主流程 - 导入并编排 Unit 2-6 的模块
  Teaches:      OpenClaw 的核心不是 Gateway 转发，而是 local-first agent runtime
  Source files: `src/gateway/server-methods/agent.ts`, `src/agents/pi-embedded-runner.ts`, `src/agents/pi-embedded-subscribe.ts`, `src/agents/pi-embedded-runner/system-prompt.ts`, `src/agents/pi-embedded-runner/skills-runtime.ts`, `src/agents/pi-tools.before-tool-call.ts`, `src/auto-reply/reply/reply-dispatcher.ts`
  Imports from: Unit 2 (gateway entry), Unit 3 (session context), Unit 4 (agent loop), Unit 5 (tools safety), Unit 6 (reply delivery)
  Runs as:      `node unit-1-overall/index.js`
  Prereqs:      None

Unit 2: Gateway Entry
  Motto:        Gateway 收信，不替 agent 思考
  Concept:      控制平面和渠道事件先收敛为统一 `agent` 请求
  Teaches:      为什么 Gateway 是本地控制平面，而不是助理的大脑
  Source files: `src/gateway/server.impl.ts`, `src/gateway/server-methods/agent.ts`, `src/gateway/protocol/`, `src/channels/plugins/`
  Exports:      `resolveGatewayPlan()`, `createGatewayControlPlane()`, `createTelegramChannel()`
  Runs as:      `node unit-2-gateway-entry/index.js`
  Prereqs:      None

Unit 3: Session Context
  Motto:        上下文先决定助理是谁
  Concept:      session key 选择 agent/workspace，然后组装 bootstrap、memory、skills 和 system prompt
  Teaches:      记忆系统为什么属于 context/workspace 层，而不是 reply dispatch
  Source files: `src/agents/agent-scope.ts`, `src/agents/bootstrap-files.ts`, `src/agents/memory-search.ts`, `src/agents/pi-embedded-runner/system-prompt.ts`, `src/agents/pi-embedded-runner/skills-runtime.ts`
  Exports:      `prepareRunContext()`, `resolveAgentScope()`, `searchMemory()`, `buildSystemPrompt()`
  Runs as:      `node unit-3-session-context/index.js`
  Prereqs:      Unit 2 的请求形状有帮助

Unit 4: Agent Loop
  Motto:        同一会话，一次只跑一个脑回路
  Concept:      agent run 序列化、发 lifecycle/tool/assistant 事件，并支持 `agent.wait`
  Teaches:      intake -> context -> model/tool -> stream -> final payload 的主执行路径
  Source files: `src/agents/pi-embedded-runner.ts`, `src/agents/pi-embedded-subscribe.ts`, `src/acp/control-plane/session-actor-queue.ts`, `src/gateway/server-methods/agent-wait.ts`
  Exports:      `createAgentRuntime()`, `createSessionLane()`, `runEmbeddedAgent()`
  Runs as:      `node unit-4-agent-loop/index.js`
  Prereqs:      Unit 3

Unit 5: Tools Safety
  Motto:        能力必须先过边界
  Concept:      skills 只提供能力入口；真正执行前还要经过 hooks、policy 和 sandbox
  Teaches:      OpenClaw 如何把强工具做成可扩展但可约束的能力
  Source files: `src/agents/pi-embedded-runner/skills-runtime.ts`, `src/agents/pi-tools.before-tool-call.ts`, `src/config/types.tools.ts`, `src/agents/sandbox.ts`, `src/agents/bash-tools.exec-runtime.ts`
  Exports:      `loadEligibleSkills()`, `createHookRunner()`, `createGuardedTool()`, `resolveToolPolicy()`
  Runs as:      `node unit-5-tools-safety/index.js`
  Prereqs:      Unit 3 和 Unit 4

Unit 6: Reply Delivery
  Motto:        运行结束后才投递
  Concept:      agent payload 被整理、去重、抑制，再交给渠道 transport
  Teaches:      回复投递是 agent loop 的后处理边界，不应该重新决定 agent 行为
  Source files: `src/auto-reply/reply/reply-dispatcher.ts`, `src/auto-reply/reply/block-reply-pipeline.ts`, `src/auto-reply/reply/dispatch-from-config.ts`
  Exports:      `createInboundDedupe()`, `shapeReply()`, `createReplyDelivery()`, `deliverRunResult()`
  Runs as:      `node unit-6-reply-delivery/index.js`
  Prereqs:      Unit 4

## 架构图

```text
Telegram / WebChat / CLI
          |
          v
Unit 2: Gateway entry
          |
          v
Unit 3: Session context
  agent scope + workspace + bootstrap + memory + skills
          |
          v
Unit 4: Agent loop
  lifecycle stream + tool stream + assistant stream + agent.wait
          |
          v
Unit 5: Tools safety
  skills + hooks + policy + sandbox
          |
          v
Unit 6: Reply delivery
  dedupe + shaping + channel transport
```

## 覆盖范围

已覆盖：
- `src/gateway/` 的本地控制平面职责
- `src/channels/plugins/` 的入站规范化思路
- `src/agents/agent-scope.ts`、bootstrap/context/system prompt 的 run 前准备
- `src/agents/memory-search.ts` 和 memory 作为上下文/工具能力的定位
- `src/agents/pi-embedded-runner*` 的 agent loop、队列、stream、wait 思路
- OpenAI-compatible LLM adapter、Pi Agent SDK 入口和模型 tool_calls 到 guarded tool 的往返
- `src/agents/pi-embedded-runner/skills-runtime.ts`、`src/agents/pi-tools.before-tool-call.ts`、tool policy、sandbox 的能力边界
- `src/auto-reply/reply/*` 的最终投递边界

跳过：
- OAuth、provider failover、usage tracking 和生产级 retry
- 真实 WebSocket server、TypeBox schema/codegen、pairing signature
- 真实 Telegram/Slack/Discord SDK 和所有移动端/macOS app
- 真实 transcript store、compaction、media pipeline、TTS、Canvas/A2UI
- ACP/subagents/cron/nodes 的完整协议

## 学习路径

如果你只想知道 OpenClaw 的核心技术，从 Unit 1 跑一遍，然后读 Unit 3 和 Unit 4。Unit 3 解释“助理是谁、知道什么、能用什么”；Unit 4 解释“助理如何真正跑起来”。Gateway、tools safety 和 reply delivery 是把这个内核接到真实世界的边界。

## 验证

本产物应通过：

```bash
npm run all
npm test
```
