# Unit 5: Reply Dispatch

> **Motto**: *Queue first, deliver once*

## In Plain Language

This unit is like a shipping dock with one clerk controlling the outgoing queue. Different workers can prepare packages, but one place decides the order and destination.

## Background Knowledge

Reply generation and reply delivery are related but different jobs. Generation decides what to say. Delivery decides whether the message is allowed, whether it is a duplicate, and where it should go. OpenClaw keeps those concerns separate so the core reply logic can stay focused while transport logic stays centralized.

Dedupe is also important. Real chat providers retry deliveries, users double-send, and reconnects can replay events. A reply system without dedupe will look flaky even if the model output is fine.

## Key Terminology

- **Dedupe**: Guard that prevents the same inbound message from being processed twice.
- **Dispatcher**: Component that owns outbound queueing and delivery.
- **Final reply**: The finished answer payload, as opposed to streaming chunks or typing indicators.
- **Delivery route**: The outbound target channel, recipient, account, and optional thread.

## What This Unit Does

This unit exports a tiny in-memory dedupe guard, a dispatcher, a simple rule-based reply generator, and `dispatchInboundTurn()`. The orchestration function checks duplicates, enforces send policy, asks for a reply, and hands the final payload to the dispatcher.

That mirrors the real OpenClaw split between `dispatchInboundMessage()` and the lower-level delivery helpers. The real system is more complex, but the shape of responsibility is the same.

## Key Code Walkthrough

- `reply-dispatch.js:1-12` defines the in-memory dedupe set.
- `reply-dispatch.js:14-40` defines the dispatcher. It validates payload text, records deliveries, and calls the provided transport function.
- `reply-dispatch.js:42-60` is the stand-in for model-backed reply generation. It lets you see the reply boundary without pulling in any LLM runtime.
- `reply-dispatch.js:62-95` is the orchestration spine: dedupe, policy check, reply generation, and outbound delivery.

## How to Run

```bash
cd /root/key_projects/learn-codebase/speedrun-openclaw
npm install
node unit-5-reply-dispatch/index.js
```

## Expected Output

You should see:

- a dispatch result with `skipped: false`
- one final reply text mentioning the session health
- one delivery record targeting Telegram

## Exercises

- Send the same `messageId` twice and confirm the second call returns `reason: "duplicate"`.
- Make `route.sendPolicy = "deny"` and confirm no delivery is recorded.
- Explain It Back: Why should reply generation return a payload instead of calling the transport directly?

## Debug Guide

### Observation Points

File: `reply-dispatch.js:14`
What to observe: The dispatcher before transport runs.
Breakpoint or log: `console.log(payload)`

File: `reply-dispatch.js:42`
What to observe: Which branch picks the reply text.
Breakpoint or log: `console.log(inboundContext.text, route.sessionKey)`

File: `reply-dispatch.js:69`
What to observe: The duplicate guard and policy gate.
Breakpoint or log: `console.log(inboundContext.messageId, route.sendPolicy)`

### Common Failures

Symptom: No delivery is recorded
Cause: Empty reply text, duplicate message ID, or denied send policy.
Fix: Inspect the early returns in `dispatchInboundTurn()`.
Verify: `dispatcher.getDeliveries()` has one record.

Symptom: Delivery goes to the wrong place
Cause: `deliverRoute` was wrong before dispatch started.
Fix: Check Unit 4 output first.
Verify: The delivery record shows the expected `channel` and `to`.

Symptom: The reply text does not match the input
Cause: The rule-based generator matched a different branch than expected.
Fix: Print `inboundContext.text.toLowerCase()` inside `makeRuleBasedReply()`.
Verify: The selected branch is obvious.

### State Inspection

- Run `node --inspect unit-5-reply-dispatch/index.js`.
- Add `console.table(dispatcher.getDeliveries())` in the demo file.
- Manually call `dispatchInboundTurn()` twice with the same `messageId` to inspect dedupe state.

### Isolation Testing

- Replace `makeRuleBasedReply` with a function that always returns `{ text: "ok" }`.
- Provide a `deliver` function that throws to simulate transport failure handling you may want to add later.
- Run the dispatcher against a fake route with `channel: "internal"` to simulate webchat delivery.
