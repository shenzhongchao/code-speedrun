# Unit 6: Native Boundaries

> **Motto**: *Keep the native seam narrow*

## In Plain Language
This unit explains how OMX can use native helpers without turning the whole project into a native app. JavaScript sends a small command object across the seam, gets a small event object back, and treats the helper like a specialist tool.

## Background Knowledge
- **Contract as a customs form**: The border crossing is easy when both sides agree on the same fields. In technical terms, the runtime bridge uses stable command and event shapes.
- **Sidecar as a specialist mechanic**: You do not move your whole office into the garage just because one mechanic is good at engines. In technical terms, OMX keeps Rust helpers behind a narrow boundary.
- **Summarizer as a bouncer**: Small outputs go straight through; big noisy outputs get compressed first. In technical terms, sparkshell switches behavior based on output size.

## Key Terminology
- **Runtime command**: A JSON-shaped request like `AcquireAuthority` or `QueueDispatch`.
- **Snapshot**: A compact state view containing authority, backlog, replay, and readiness fields.
- **Spark route**: The classified command form that decides whether output should be summarized.

## What This Unit Does
The unit simulates the two most important native seams in OMX. First, it models a runtime bridge that accepts a few command variants and returns event objects. Second, it models sparkshell-style routing and long-output summarization.

## Key Code Walkthrough
`index.js:12-30` builds the snapshot shape. It mirrors the real repository's idea that JavaScript should be able to read a small compatibility view instead of digging through native internals.

`index.js:32-86` is the core bridge. The comment at `index.js:33-34` is the whole lesson: the seam stays healthy only if the contract stays small and stable. `AcquireAuthority`, `QueueDispatch`, and `MarkNotified` are enough to teach the pattern.

`index.js:100-131` handles sparkshell routing and summarization. The route classifier decides whether a command is likely to produce long output, and the summarizer compresses long output into head/tail metadata.

## How to Run
```bash
cd /root/key_projects/learn-codebase/speedrun-oh-my-codex
node unit-6-native-boundaries/index.js
```

## Expected Output
You should see a JSON object with `events`, `sparkRoute`, and `sparkResult`. The snapshot event should report `ready: true`, and the spark result should use `mode: "summary"` for the long `git status --short` sample.

## Exercises
### Explain It Back
Why is it safer to keep the bridge contract small than to expose every native detail to JavaScript?

### Modify It
- Add support for a `MarkDelivered` command to the demo event sequence and confirm the backlog changes.
- Lower the summarization threshold from `6` to `3` and confirm more outputs get summarized.

## Debug Guide
### Observation Points
File: `index.js:12`
What to observe: How the snapshot is derived from the mutable bridge state.
Breakpoint or log: Inspect `state.dispatches` before and after calling `captureSnapshot()`.

File: `index.js:32`
What to observe: The exact command-to-event mapping inside the bridge.
Breakpoint or log: Step through each `case` in `execRuntimeCommand()`.

File: `index.js:100`
What to observe: The command classification that decides whether output is "long".
Breakpoint or log: Inspect `argv`, `command`, and `subcommand`.

### Common Failures
Symptom: `Unsupported runtime command` is thrown.
Cause: The demo sent a command variant the simplified bridge does not model.
Fix: Add a new `case` to `execRuntimeCommand()` or change the demo input.
Verify: Re-run and confirm the event list completes.

Symptom: The summarizer returns `mode: "raw"` for the git sample.
Cause: The output no longer exceeds the threshold.
Fix: Add more lines to the sample output or lower the threshold.
Verify: Re-run and confirm `mode: "summary"` appears.

Symptom: The snapshot says `ready: false`.
Cause: Authority was never acquired before the snapshot.
Fix: Keep the `AcquireAuthority` command before `CaptureSnapshot`.
Verify: Re-run and confirm the readiness reasons array is empty.

### State Inspection
- Run `node --input-type=module -e "import { createRuntimeBridgeState, execRuntimeCommand, captureSnapshot } from './unit-6-native-boundaries/index.js'; const state=createRuntimeBridgeState(); execRuntimeCommand(state,{command:'AcquireAuthority',owner:'leader',lease_id:'x',leased_until:'2099-01-01'}); console.log(captureSnapshot(state));"` from the speedrun root.

### Isolation Testing
- Replace the sample `git status --short` prompt with `echo ok` and confirm `chooseSparkShellRoute()` returns `shell-native`.
- Add another dispatch record and confirm `pending` and `notified` counts change in the snapshot.
- Use the `Unit 6: Native Boundaries` VS Code launcher and watch the event array grow one command at a time.
