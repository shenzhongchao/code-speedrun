# Source Map

## Unit 1: Overall

Speedrun:
- `unit-1-overall/index.js`

OpenClaw:
- `src/gateway/server-methods/agent.ts`
- `src/agents/pi-embedded-runner.ts`
- `src/auto-reply/reply/reply-dispatcher.ts`

What to compare:
- `runId/sessionKey/idempotencyKey/source/payloads` 如何贯穿全链路。

## Unit 2: Gateway Entry

Speedrun:
- `unit-2-gateway-entry/entry.js`

OpenClaw:
- `src/gateway/server.impl.ts`
- `src/gateway/server-methods/agent.ts`
- `src/gateway/protocol/`
- `src/channels/plugins/`

What to compare:
- channel raw event 如何 normalize 成统一 envelope。
- remote/local/node 连接如何进入信任边界。

## Unit 3: Session Context

Speedrun:
- `unit-3-session-context/session-context.js`

OpenClaw:
- `src/agents/agent-scope.ts`
- `src/agents/bootstrap-files.ts`
- `src/agents/memory-search.ts`
- `src/agents/pi-embedded-runner/system-prompt.ts`
- `src/agents/pi-embedded-runner/skills-runtime.ts`

What to compare:
- session key 如何解析 agent。
- bootstrap、memory、history、skills 如何进入 prompt。

## Unit 4: Agent Loop

Speedrun:
- `unit-4-agent-loop/agent-loop.js`

OpenClaw:
- `src/agents/pi-embedded-runner.ts`
- `src/agents/pi-embedded-subscribe.ts`
- `src/acp/control-plane/session-actor-queue.ts`
- `src/gateway/server-methods/agent-wait.ts`

What to compare:
- 同 session 排队、不同 session 并行。
- `agent.wait` 等 lifecycle end/error，而不是 tool end。

## Unit 5: Tools Safety

Speedrun:
- `unit-5-tools-safety/tools-safety.js`

OpenClaw:
- `src/agents/pi-embedded-runner/skills-runtime.ts`
- `src/agents/pi-tools.before-tool-call.ts`
- `src/config/types.tools.ts`
- `src/agents/sandbox.ts`
- `src/agents/bash-tools.exec-runtime.ts`

What to compare:
- prompt exposure、hook、policy、sandbox 的职责分层。

## Unit 6: Reply Delivery

Speedrun:
- `unit-6-reply-delivery/reply-delivery.js`

OpenClaw:
- `src/auto-reply/reply/reply-dispatcher.ts`
- `src/auto-reply/reply/block-reply-pipeline.ts`
- `src/auto-reply/reply/dispatch-from-config.ts`

What to compare:
- payload shaping、dedupe、transport retry 和 channel formatting。
