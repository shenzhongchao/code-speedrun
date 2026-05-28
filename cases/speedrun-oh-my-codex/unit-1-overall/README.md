# Unit 1: OMX End-to-End

> **Motto**: *One CLI, many moving parts*

## In Plain Language
This unit is the shortest runnable explanation of the whole repository. One script performs a simplified `omx setup`, turns a user prompt into overlay state, starts a durable team runtime, and pushes one dispatch through the native-contract seam.

## Background Knowledge
- **Command router as a receptionist**: The receptionist does not solve the problem; it sends you to the right desk. In technical terms, OMX parses argv once, then hands the request to narrow command handlers.
- **Overlay as a sticky note on a manual**: The base manual stays the same, but each session can add a temporary note. In technical terms, OMX injects marker-bounded runtime context into `AGENTS.md`.
- **Durable state as a shared whiteboard**: Everyone on the team must look at the same board. In technical terms, the leader and workers coordinate through files under `.omx/`.

## Key Terminology
- **Invocation**: The parsed meaning of CLI arguments, such as `launch` or `team`.
- **Overlay**: Session-specific text inserted into `AGENTS.md` so Codex sees current modes, skills, and codebase context.
- **Native boundary**: A narrow interface between JavaScript orchestration and helper binaries, usually expressed as JSON commands or argv arrays.

## What This Unit Does
The script stitches Units 2-6 together with realistic data shapes. It does not try to reproduce every OMX feature. Instead, it proves that the main subsystems can exchange real-looking state without fake narration.

## Key Code Walkthrough
The imports at `index.js:4-23` are the architecture map in miniature: the overall flow depends on the router, setup layer, overlay layer, team runtime, and native boundary. The helper at `index.js:27-58` is the launch-time overlay step. It detects the active skill, writes `.omx/state/skill-active-state.json`, builds a runtime overlay, and merges that overlay into `AGENTS.md`.

The happy path starts at `index.js:60-99`. `parseInvocation()` and `routeInvocation()` handle `setup`, `launch`, and `team` just like the real CLI does, but the handlers are thin and local. The native seam lives at `index.js:101-134`, where the unit queues a dispatch, marks it notified, and then runs the sparkshell-style long-output summarizer.

The final JSON report is assembled at `index.js:136-163`. That report is the fastest way to answer, "What are the moving parts in OMX, and what state does each one own?"

## How to Run
```bash
cd /root/key_projects/learn-codebase/speedrun-oh-my-codex
node unit-1-overall/index.js
```

## Expected Output
You should see a JSON object with four top-level sections: `setup`, `launch`, `team`, and `nativeBoundary`. The `team.phase` field should be `team-exec`, and `launch.skill` should be `team`.

## Exercises
### Explain It Back
Explain why this unit imports sibling units instead of copying their logic inline. What does that teach you about the original repository?

### Modify It
- Change `userPrompt` in `index.js` so the active skill becomes `ralph` instead of `team`.
- Add a second runtime command that marks the dispatch as delivered, then confirm the snapshot backlog changes.

## Debug Guide
### Observation Points
File: `index.js:27`
What to observe: The moment a user prompt becomes an overlay and skill-state file.
Breakpoint or log: Pause before `buildRuntimeOverlay()` and inspect `activation`.

File: `index.js:65`
What to observe: The router handing the same workspace through setup, launch, and team flows.
Breakpoint or log: Step into `routeInvocation()` and compare each parsed invocation.

File: `index.js:101`
What to observe: The native boundary changing from queued dispatch to notified dispatch.
Breakpoint or log: Inspect `runtimeBridge` after each `execRuntimeCommand()` call.

### Common Failures
Symptom: The output never shows `team-exec`.
Cause: The phase-advance lines were removed or commented out.
Fix: Restore the `advancePhase()` calls at `index.js:94-95`.
Verify: Re-run the unit and confirm `team.phase` is `team-exec`.

Symptom: `launch.skill` becomes `default`.
Cause: The sample prompt no longer contains a routed keyword.
Fix: Add `$team`, `$ralph`, or another supported trigger back into `userPrompt`.
Verify: Re-run and confirm `launch.skill` changed.

Symptom: The overlay file is missing from `AGENTS.md`.
Cause: The unit did not complete the overlay write step.
Fix: Check that `applyLaunchOverlay()` still reads and rewrites `AGENTS.md`.
Verify: Open `unit-1-overall/demo-workspace/AGENTS.md` and confirm the marker block is present.

### State Inspection
- Inspect the installed workspace: `find unit-1-overall/demo-workspace -maxdepth 4 -type f | sort`
- Inspect the injected `AGENTS.md`: `sed -n '1,80p' unit-1-overall/demo-workspace/AGENTS.md`
- Inspect the team state: `cat unit-1-overall/demo-workspace/.omx/team/*/phase.json`

### Isolation Testing
- Comment out the team block at `index.js:80-99` and confirm the rest of the flow still works.
- Replace `chooseSparkShellRoute("run git status --short")` with a short command like `echo ok` and confirm the summarizer returns `mode: "raw"`.
- Use the `Unit 1: OMX End-to-End` launcher in the root `.vscode/launch.json` to step through the whole sequence.
