# Simplifications

What was simplified or stubbed in each unit compared to the original codebase.
Use this as a checklist to progressively restore real implementations.

> **Tip**: You can ask a coding agent to expand any item below against the original repo, for example:
> "Restore real gateway auth handling in unit-2 by referencing ../openclaw/src/gateway/server-methods/chat.ts"

## Unit 1: Overall

- [ ] Gateway boot uses a plain object config instead of `loadConfig()` and startup validation (`src/gateway/server.impl.ts`, `src/config/config.ts`)
- [ ] Only one built-in channel plugin is wired in; real OpenClaw dynamically loads many providers (`src/channels/plugins/`, `src/gateway/server-channels.ts`)
- [ ] Reply generation is rule-based text, not model-backed agent execution (`src/auto-reply/reply.ts`, `src/agents/`)
- [ ] Transcript persistence, abort control, and tool events are removed (`src/gateway/server-methods/chat.ts`, `src/gateway/chat-abort.ts`)

## Unit 2: Gateway Entry

- [ ] CLI parsing is reduced to one command token plus `--port`; real OpenClaw has route-first parsing, lazy command registration, and profiles (`src/entry.ts`, `src/cli/run-main.ts`, `src/cli/program/`)
- [ ] Runtime guards, compile-cache setup, and process respawn logic are omitted (`src/entry.ts`, `src/openclaw.mjs`)
- [ ] Gateway chat context only keeps fields needed for the speedrun; real contexts include attachments, provenance, capabilities, and auth data (`src/gateway/server-methods/chat.ts`)

## Unit 3: Channel Docking

- [ ] Plugin registry is local in-memory data, not the live plugin runtime registry (`src/channels/plugins/index.ts`, `src/plugins/runtime/index.ts`)
- [ ] Channel startup records a healthy runtime but does not keep background tasks or backoff restarts (`src/gateway/server-channels.ts`)
- [ ] Provider normalization is hardcoded for a Telegram-shaped demo event (`src/telegram/`, `src/channels/plugins/`)

## Unit 4: Session Routing

- [ ] Session key logic covers direct and group shapes only; real OpenClaw also supports threads, ACP, cron, and subagents (`src/routing/session-key.ts`, `src/sessions/session-key-utils.ts`)
- [ ] Agent selection only checks explicit or default agent IDs (`src/agents/agent-scope.ts`)
- [ ] Send policy rules are simple channel/chat-type matches, not the full config-driven matcher (`src/sessions/send-policy.ts`)

## Unit 5: Reply Dispatch

- [ ] Dedupe is an in-memory `Set` instead of the broader inbound-deduping behavior (`src/auto-reply/reply/inbound-dedupe.ts`, `src/auto-reply/reply/dispatch-from-config.ts`)
- [ ] Dispatcher only handles final text payloads; streaming, typing, tool results, and TTS are omitted (`src/auto-reply/reply/reply-dispatcher.ts`, `src/tts/tts.ts`)
- [ ] Reply generation is synchronous and local; real OpenClaw fans into command handling, model selection, hooks, and route-reply (`src/auto-reply/reply/`, `src/hooks/`)
