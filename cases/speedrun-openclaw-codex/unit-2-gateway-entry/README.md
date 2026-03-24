# Unit 2: Gateway Entry

> **Motto**: *Normalize before you think*

## In Plain Language

This unit is like a receptionist rewriting messy handwritten notes onto one standard intake form. Once the form is clean, the rest of the office can stop guessing.

## Background Knowledge

CLI entry points are noisy. They include flags, optional commands, defaults, and sometimes values that must be validated before the real work starts. OpenClaw's real entry path does much more than this unit, but the core idea is the same: decide what the process is trying to do and reduce that into a predictable plan.

The second half is request normalization. OpenClaw's gateway methods turn direct requests into a message-shaped object so downstream routing and reply logic can treat them much like provider messages.

## Key Terminology

- **Entry point**: The first executable code path, such as `openclaw.mjs` or `src/entry.ts`.
- **Route-first CLI**: Parsing strategy where the command path is identified early so only the needed command tree is loaded.
- **Message context**: A normalized object that carries the fields later layers need to route and answer a turn.
- **Originating route**: The channel or surface that should receive the reply back.

## What This Unit Does

This unit exports two functions. `resolveGatewayPlan()` turns argv into one startup decision: what command ran, which port to use, and whether replies are expected. `buildGatewayChatContext()` takes a direct gateway request and rewrites it into a message envelope that looks close enough to provider traffic for the rest of the speedrun.

That is the important architectural move. Instead of keeping "webchat logic" and "channel logic" separate all the way down, OpenClaw collapses them early into shared shapes.

## Key Code Walkthrough

- `entry.js:3-14` contains tiny helpers for reading flags and parsing a port. This stands in for the real entry layer's much larger validation pass.
- `entry.js:16-31` is the boot-plan reducer. The most important output fields are `startMode`, `needsGateway`, and `deliverReplies`.
- `entry.js:33-68` is the gateway-to-message bridge. Notice that the output includes `sessionKey`, `provider`, `surface`, `originatingChannel`, and `originatingTo`. Those are the fields Units 4 and 5 need later.

## How to Run

```bash
cd /root/key_projects/learn-codebase/speedrun-openclaw
npm install
node unit-2-gateway-entry/index.js
```

## Expected Output

You should see:

- a gateway plan for command `agent`
- a normalized context with `provider: 'internal'`
- a message ID of `run-demo-1`

## Exercises

- Add support for `--bind <mode>` to `resolveGatewayPlan()` and print it in the example.
- Change `originatingChannel` from `internal` to `telegram` and follow how Unit 4 would route it.
- Explain It Back: Describe why direct gateway chat requests are rewritten into a channel-like object instead of getting their own isolated reply path.

## Debug Guide

### Observation Points

File: `entry.js:16`
What to observe: Which command token won.
Breakpoint or log: `console.log(tokens, command)`

File: `entry.js:19`
What to observe: The port after defaulting and validation.
Breakpoint or log: `console.log(port)`

File: `entry.js:33`
What to observe: The exact input fields that survive normalization.
Breakpoint or log: `console.log(params)`

### Common Failures

Symptom: Port stays `18789` when you expected a custom value
Cause: `--port` was missing or invalid.
Fix: Pass `--port 19090` in the argv example.
Verify: The printed plan shows the new port.

Symptom: `text is required`
Cause: `buildGatewayChatContext()` got an empty message.
Fix: Provide a non-empty `text` string.
Verify: The normalized context prints.

Symptom: Replies later route to the wrong surface
Cause: `originatingChannel` or `originatingTo` was set incorrectly.
Fix: Inspect the normalized context before passing it onward.
Verify: Unit 4 prints the expected `deliverRoute`.

### State Inspection

- Run `node --inspect unit-2-gateway-entry/index.js`.
- Add `debugger;` at `entry.js:16` to step through CLI reduction.
- Add `console.table([plan, ctx])` inside `index.js` for a quick side-by-side of startup decision versus message envelope.

### Isolation Testing

- Call `resolveGatewayPlan(["node", "openclaw", "gateway"])` in a one-line REPL snippet.
- Call `buildGatewayChatContext({ text: "hello" })` from `node --input-type=module`.
- Replace the example argv with an unknown command and decide whether your speedrun should treat it as `request` or reject it.
