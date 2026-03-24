# Unit 3: Channel Docking

> **Motto**: *Every channel plugs into the same socket*

## In Plain Language

This unit is like a universal power strip. Different devices have different shapes, but once each one gets the right adapter, the wall socket can treat them the same way.

## Background Knowledge

OpenClaw supports many chat surfaces. That only scales if the core gateway does not know every provider's details. The usual pattern is a plugin contract: each provider supplies startup hooks and normalization logic, while the gateway keeps one registry and one lifecycle manager.

Normalization matters because Telegram, Slack, WhatsApp, and others all name fields differently. The channel layer's job is to convert those raw provider events into one common object.

## Key Terminology

- **Plugin registry**: The catalog of available provider adapters.
- **Channel runtime**: The live state for one configured provider account.
- **Normalized inbound event**: A provider message rewritten into shared fields like `text`, `from`, `to`, and `chatType`.
- **Account**: One configured identity inside a provider, such as a Telegram bot or Slack workspace install.

## What This Unit Does

This unit exports a minimal registry, a channel manager, and a Telegram-shaped plugin. The manager starts each configured account, records a runtime snapshot, and exposes `receive()` for converting raw provider events into the normalized shape the rest of the speedrun expects.

The real OpenClaw implementation adds restarts, richer runtime status, and external plugin loading. The core lesson stays the same: channel-specific code ends at the normalization boundary.

## Key Code Walkthrough

- `channel-docking.js:1-24` builds the registry and keeps plugin ordering predictable.
- `channel-docking.js:26-58` is the startup path. It walks configured account IDs, creates runtime state, and calls the plugin's `startAccount()` hook.
- `channel-docking.js:60-86` exposes `startAll()`, `snapshot()`, and `receive()`. `receive()` is the crucial seam because it stamps provider-independent fields onto the normalized event.
- `channel-docking.js:89-115` defines the Telegram demo plugin. It shows exactly which provider-specific knowledge stays inside the plugin.

## How to Run

```bash
cd /root/key_projects/learn-codebase/speedrun-openclaw
npm install
node unit-3-channel-docking/index.js
```

## Expected Output

You should see:

- one runtime snapshot for `telegram:personal`
- one normalized inbound event with `provider: 'telegram'`
- `originatingChannel` and `originatingTo` fields already filled in

## Exercises

- Add a `createSlackPlugin()` function that maps Slack-style raw fields onto the same normalized shape.
- Extend the runtime snapshot with `lastError` and simulate a startup failure for one account.
- Explain It Back: Why should the channel manager know how to start accounts but not how to route or answer messages?

## Debug Guide

### Observation Points

File: `channel-docking.js:12`
What to observe: Registry order and dedupe behavior.
Breakpoint or log: `console.log(sorted.map((plugin) => plugin.id))`

File: `channel-docking.js:33`
What to observe: Each account ID as it turns into a runtime record.
Breakpoint or log: `console.log(channelId, accountId)`

File: `channel-docking.js:69`
What to observe: The moment raw provider data crosses into normalized gateway data.
Breakpoint or log: `console.log(rawEvent, normalized)`

### Common Failures

Symptom: `Unknown channel plugin: telegram`
Cause: The plugin was not registered.
Fix: Include `createTelegramPlugin()` in `createChannelRegistry([...])`.
Verify: `registry.list()` returns `telegram`.

Symptom: No runtimes appear in `snapshot()`
Cause: `startAll()` was not awaited or the account list was empty.
Fix: Await startup and confirm `config.channels.telegram.accounts` has values.
Verify: The snapshot array has one entry.

Symptom: `from` or `to` is `undefined`
Cause: Raw event mapping is incomplete.
Fix: Check `normalizeInbound()` in the plugin.
Verify: The normalized event prints all shared fields.

### State Inspection

- Run `node --inspect unit-3-channel-docking/index.js`.
- Add `console.table(manager.snapshot())` after startup.
- Print `registry.list()` to see plugin order.

### Isolation Testing

- Call `createTelegramPlugin().normalizeInbound(...)` directly from a small REPL snippet.
- Temporarily replace `startAccount()` with a function that throws to explore runtime failure handling.
- Create a registry with two plugins and make sure `startAll()` initializes both.
