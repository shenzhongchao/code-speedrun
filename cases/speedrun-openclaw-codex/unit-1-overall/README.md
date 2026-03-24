# Unit 1: Overall - OpenClaw

> **Motto**: *One message, many seams*

## In Plain Language

This unit is like watching a package move through an entire warehouse. You see where it arrives, which belt picks it up, which label gets attached, and where it leaves.

## Background Knowledge

OpenClaw is a control plane. Think of it as the front desk for many chat surfaces. Some requests come from a web dashboard or CLI, while others come from a real provider like Telegram. The trick is not to keep separate pipelines forever. The system quickly converts both kinds of input into a shared message shape so downstream code can stay mostly channel-agnostic.

A session key is the conversation label. It tells the agent layer which memory lane to use. In OpenClaw, session keys also help enforce rules like "group replies on Slack are denied by policy" or "this turn belongs to the default agent."

## Key Terminology

- **Control plane**: The central coordinator. In OpenClaw, the gateway owns routing, channels, nodes, and request dispatch.
- **Message envelope**: One normalized object that carries text, sender, channel, and routing hints.
- **Session key**: A canonical string such as `agent:main:telegram:direct:@user` that names a conversation lane.
- **Dispatcher**: The component that owns delivery order and keeps reply production separate from reply transport.

## What This Unit Does

This unit runs the full miniature movie. First it resolves a gateway boot plan, then it starts a Telegram-shaped channel runtime, receives an inbound provider event, turns that event into a session route, and dispatches a reply back out. After that, it runs a second turn from the control plane to show that direct webchat-style input converges on the same routing and reply path.

That convergence is the big lesson. OpenClaw has many surfaces, but the center of the system depends on shared shapes and shared decisions.

## Key Code Walkthrough

- `index.js:15-46` creates the tiny config, boot plan, channel registry, and reply dispatcher. This mirrors the real gateway startup path where config, channels, and delivery infrastructure are prepared before traffic arrives.
- `index.js:48-72` handles a Telegram-like inbound event. The channel manager normalizes the event, `resolveTurnRoute()` attaches a session key, and `dispatchInboundTurn()` produces and delivers the answer.
- `index.js:74-95` builds a control-plane request with `buildGatewayChatContext()`. This is the important convergence point: direct gateway traffic uses the same routing and reply machinery.
- `index.js:97-106` prints the final artifacts so you can inspect the exact shapes passed between units.

## How to Run

```bash
cd /root/key_projects/learn-codebase/speedrun-openclaw
npm install
node unit-1-overall/index.js
```

## Expected Output

You should see:

- a gateway boot plan with port `18789`
- one running Telegram runtime
- a Telegram route with session key `agent:main:telegram:direct:@teal-user`
- a control-plane route with session key `agent:main:main`
- two final deliveries, one to `telegram` and one to `internal`

## Exercises

- Change the Telegram message in `index.js` so it mentions `build` instead of `status`, then rerun and compare the reply text.
- Add a second channel plugin in Unit 3 and import it here so Unit 1 handles two provider surfaces.
- Explain It Back: In 3-5 sentences, explain why both channel input and control-plane input are converted into one shared routing path. If your explanation starts drifting into "because the framework does it," re-read `index.js:48-95`.

## Debug Guide

### Observation Points

File: `index.js:34`
What to observe: The gateway boot decision before any traffic exists.
Breakpoint or log: `console.log(plan)`

File: `index.js:48`
What to observe: The raw provider event crossing the Unit 3 boundary.
Breakpoint or log: `console.log(telegramInbound)`

File: `index.js:61`
What to observe: The exact session key and delivery route chosen for the provider event.
Breakpoint or log: `console.log(telegramRoute)`

File: `index.js:89`
What to observe: The second turn entering the same dispatch path from the control plane.
Breakpoint or log: `console.log(controlPlaneRoute)`

### Common Failures

Symptom: `Unknown channel plugin: telegram`
Cause: Unit 3 was not wired into the registry.
Fix: Check the `createChannelRegistry([createTelegramPlugin()])` call.
Verify: `manager.snapshot()` prints one Telegram runtime.

Symptom: `text is required`
Cause: The control-plane request was created without a message body.
Fix: Pass a non-empty `text` field to `buildGatewayChatContext()`.
Verify: The control-plane route is printed.

Symptom: Only one delivery appears
Cause: One turn was skipped or denied.
Fix: Check message IDs for duplicates and make sure `sendPolicy` stays `allow`.
Verify: The final deliveries array has two records.

### State Inspection

- Run `node --inspect-brk unit-1-overall/index.js` and watch `telegramInbound`, `telegramRoute`, and `deliveries`.
- Add `console.table(deliveries)` below `index.js:105` to see the outbound records in one row-per-delivery view.
- Temporarily print `manager.snapshot()` before and after `startAll()` to see startup state appear.

### Isolation Testing

- Comment out the control-plane half (`index.js:74-95`) and confirm the channel path still works.
- Replace `makeRuleBasedReply` with an inline function that always returns `"fixed reply"` to isolate delivery from reply generation.
- Swap the imported `resolveTurnRoute()` with a fake object to test Unit 5 in total isolation from Unit 4.
