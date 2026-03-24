> **Source**: [openclaw](https://github.com/openclaw/openclaw) — cloned on 2026-03-13

# Speedrun OpenClaw

This speedrun turns a very large TypeScript monorepo into five runnable units that follow the core assistant path:

1. Gateway or UI input enters the control plane.
2. Channel plugins normalize provider-specific events.
3. Routing turns identity into an agent-scoped session key.
4. Reply dispatch decides whether to answer, dedupe, and deliver.

The generated code is intentionally small, but each unit points back to the real OpenClaw seams that inspired it.

## Quick Start

```bash
cd /root/key_projects/learn-codebase/speedrun-openclaw
npm install
npm run all
```

You can also run units one at a time:

```bash
node unit-1-overall/index.js
node unit-2-gateway-entry/index.js
node unit-3-channel-docking/index.js
node unit-4-session-routing/index.js
node unit-5-reply-dispatch/index.js
```

## Unit Table

| Unit | Title | Motto | Concept |
|------|-------|-------|---------|
| 1 | Overall | *One message, many seams* | End-to-end assistant turn using the exported APIs from Units 2-5 |
| 2 | Gateway Entry | *Normalize before you think* | CLI and control-plane requests become one shared message shape |
| 3 | Channel Docking | *Every channel plugs into the same socket* | Channel plugins register, start, and normalize inbound events |
| 4 | Session Routing | *Identity becomes a key* | Provider metadata becomes an agent-scoped session and policy decision |
| 5 | Reply Dispatch | *Queue first, deliver once* | Deduplicate, generate a reply, and send it through one delivery dock |

## Unit Map

Unit 1: Overall - OpenClaw
  Motto:        One message, many seams
  Concept:      End-to-end main flow - imports and orchestrates modules from Units 2-5
  Teaches:      How gateway input and channel input converge on the same routing and reply path
  Source files: `src/cli/gateway-cli/run.ts`, `src/gateway/server.impl.ts`, `src/gateway/server-methods/chat.ts`, `src/gateway/server-channels.ts`, `src/routing/session-key.ts`, `src/auto-reply/dispatch.ts`
  Imports from: Unit 2 (gateway entry), Unit 3 (channel docking), Unit 4 (session routing), Unit 5 (reply dispatch)
  Runs as:      `node unit-1-overall/index.js`
  Prereqs:      None

Unit 2: Gateway Entry
  Motto:        Normalize before you think
  Concept:      CLI and control-plane requests are reduced to one message envelope
  Teaches:      Why OpenClaw converts gateway chat/send calls into channel-shaped contexts
  Source files: `src/entry.ts`, `src/cli/run-main.ts`, `src/cli/program/command-registry.ts`, `src/gateway/server-methods/chat.ts`
  Exports:      `resolveGatewayPlan()`, `buildGatewayChatContext()`
  Runs as:      `node unit-2-gateway-entry/index.js`
  Prereqs:      None

Unit 3: Channel Docking
  Motto:        Every channel plugs into the same socket
  Concept:      Plugin registry plus channel manager starts accounts and emits normalized inbound events
  Teaches:      How very different chat providers fit behind one gateway-facing contract
  Source files: `src/channels/plugins/index.ts`, `src/gateway/server-channels.ts`, `src/plugins/runtime/index.ts`
  Exports:      `createChannelRegistry()`, `createChannelManager()`, `createTelegramPlugin()`
  Runs as:      `node unit-3-channel-docking/index.js`
  Prereqs:      None

Unit 4: Session Routing
  Motto:        Identity becomes a key
  Concept:      Channel, peer, and agent metadata become a canonical session key and send-policy decision
  Teaches:      How OpenClaw isolates memory and behavior per agent and conversation shape
  Source files: `src/routing/session-key.ts`, `src/agents/agent-scope.ts`, `src/sessions/send-policy.ts`
  Exports:      `buildAgentPeerSessionKey()`, `resolveSessionAgentId()`, `resolveSendPolicy()`, `resolveTurnRoute()`
  Runs as:      `node unit-4-session-routing/index.js`
  Prereqs:      Unit 3 helps because it supplies the inbound shape

Unit 5: Reply Dispatch
  Motto:        Queue first, deliver once
  Concept:      Dedupe, reply generation, and outbound delivery are centralized in one dispatcher
  Teaches:      Why OpenClaw keeps reply production separate from reply delivery
  Source files: `src/auto-reply/dispatch.ts`, `src/auto-reply/reply/dispatch-from-config.ts`, `src/auto-reply/reply/reply-dispatcher.ts`
  Exports:      `createInboundDedupe()`, `createReplyDispatcher()`, `makeRuleBasedReply()`, `dispatchInboundTurn()`
  Runs as:      `node unit-5-reply-dispatch/index.js`
  Prereqs:      Unit 4

## Architecture Diagram

```text
CLI / Control UI request ---> Unit 2: Gateway entry ---------+
                                                             |
Provider event ---------> Unit 3: Channel docking ---------->|
                                                             v
                                                   Unit 4: Session routing
                                                             |
                                                             v
                                                   Unit 5: Reply dispatch
                                                             |
                                                             v
                                                   Telegram / WebChat / other surface
```

## Coverage

Covered:
- `src/entry.ts`, `src/cli/run-main.ts`, `src/cli/program/`
- `src/gateway/server.impl.ts`, `src/gateway/server-methods/chat.ts`, `src/gateway/server-channels.ts`
- `src/channels/plugins/`
- `src/routing/session-key.ts`, `src/agents/agent-scope.ts`, `src/sessions/send-policy.ts`
- `src/auto-reply/dispatch.ts`, `src/auto-reply/reply/dispatch-from-config.ts`, `src/auto-reply/reply/reply-dispatcher.ts`

Skipped:
- `apps/`, `ui/`, `Swabble/` - product shells around the gateway, not the narrow assistant turn
- `docs/`, `assets/`, `changelog/` - documentation and packaging material
- `scripts/`, `git-hooks/`, release files, Docker files - build and distribution automation
- `extensions/`, `packages/`, `skills/` - important ecosystem surfaces, but outside the shortest runnable spine

Woven into other units instead of teaching separately:
- `src/config/` - shows up in Unit 2 and Unit 4
- `src/plugins/runtime/` - shows up in Unit 3
- `src/logging/`, `src/infra/` - referenced where behavior needs them, but not isolated as standalone lessons

No major architectural gap was found for the "assistant turn" learning goal. The main omission is platform packaging and the many optional integrations, which would be a second pass after this speedrun.

## Learning Path

Start with Unit 1 if you want the whole movie first. Start with Unit 2 if you want to see how OpenClaw turns CLI and UI requests into a common shape. Start with Unit 3 if you are most interested in provider integrations. Units 4 and 5 are the key implementation spine for re-creating a smaller OpenClaw-like assistant.

## Verification

Verified on this machine with:

```bash
node scripts/run-all.js
```

That command ran successfully on 2026-03-13 using Node `v22.17.0`.
