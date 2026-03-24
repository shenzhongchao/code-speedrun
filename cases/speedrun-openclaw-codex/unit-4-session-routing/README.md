# Unit 4: Session Routing

> **Motto**: *Identity becomes a key*

## In Plain Language

This unit is like assigning every conversation its own mailbox. Once the right label is on the box, you always know where future letters for that conversation belong.

## Background Knowledge

Large chat systems need more than "reply to whoever just spoke." They also need isolation: which agent owns the turn, which memory store should be used, and whether this kind of conversation is even allowed to answer. OpenClaw expresses those decisions with canonical session keys and send policies.

A session key is not just an ID. It is a compact routing sentence. `agent:main:telegram:direct:@teal-user` means: use the `main` agent, on Telegram, in a direct chat, for that peer.

## Key Terminology

- **Canonical**: One normalized format that all equivalent inputs collapse into.
- **Agent scope**: Which agent's memory, config, and tools should apply.
- **Send policy**: The allow-or-deny rule for replying from a given session.
- **Direct vs group chat**: Whether the peer is one person or a shared room/channel.

## What This Unit Does

This unit exports small versions of the three routing jobs OpenClaw performs all the time. It builds canonical session keys, chooses the active agent ID, and checks whether a reply is allowed. Then `resolveTurnRoute()` bundles those decisions into one object that Unit 5 can consume.

This is the narrowest, most reusable part of the speedrun. If you wanted to rebuild a smaller OpenClaw clone, this is one of the first layers you would keep.

## Key Code Walkthrough

- `session-routing.js:4-20` defines the canonical session-key builder. The important rule is that all tokens are lowercased before becoming part of the key.
- `session-routing.js:22-31` resolves the active agent. It prefers an explicit agent, then falls back to the session key, then finally to config default.
- `session-routing.js:33-50` evaluates send-policy rules. The speedrun keeps only channel and chat-type matching because that is enough to show the pattern.
- `session-routing.js:52-87` ties everything together and emits the final `deliverRoute`.

## How to Run

```bash
cd /root/key_projects/learn-codebase/speedrun-openclaw
npm install
node unit-4-session-routing/index.js
```

## Expected Output

You should see:

- a direct-message session key for Telegram
- a resolved route pointing replies back to `@teal-user`
- a denied policy for Slack group messages

## Exercises

- Extend `buildAgentPeerSessionKey()` with a thread suffix such as `:thread:release-war-room`.
- Add a second agent to the config and pass `preferredAgentId: "ops"` into `resolveTurnRoute()`.
- Explain It Back: Why is a session key more useful than storing separate `agentId`, `channel`, and `peerId` fields everywhere?

## Debug Guide

### Observation Points

File: `session-routing.js:9`
What to observe: The canonical key that comes out of the builder.
Breakpoint or log: `console.log(params, sessionKey)`

File: `session-routing.js:22`
What to observe: Which source picked the agent ID.
Breakpoint or log: `console.log(preferredAgentId, sessionKey, config.agents?.default)`

File: `session-routing.js:33`
What to observe: Which send-policy rule matched.
Breakpoint or log: `console.log(rule, channel, chatType)`

### Common Failures

Symptom: Session key has unexpected uppercase or spaces
Cause: A token was not normalized.
Fix: Route all user input through `normalizeToken()`.
Verify: The printed key is lowercase.

Symptom: Replies are denied when they should be allowed
Cause: A policy rule matched too broadly.
Fix: Inspect `config.session.sendPolicy.rules`.
Verify: `resolveSendPolicy()` returns `allow` for the target case.

Symptom: Replies go to the wrong peer
Cause: `originatingTo` or `from` was missing from inbound data.
Fix: Inspect the inbound event from Unit 2 or Unit 3.
Verify: `deliverRoute.to` matches the intended recipient.

### State Inspection

- Step through `resolveTurnRoute()` with `node --inspect`.
- Add `console.table([resolveTurnRoute(...)])` in `index.js`.
- Manually vary `chatType` between `direct` and `group` to see the key shape change.

### Isolation Testing

- Call `buildAgentPeerSessionKey()` with hardcoded values from the Node REPL.
- Run `resolveSendPolicy()` with different rule arrays to test only policy logic.
- Feed a Unit 2 context and a Unit 3 context into `resolveTurnRoute()` and compare the outputs.
