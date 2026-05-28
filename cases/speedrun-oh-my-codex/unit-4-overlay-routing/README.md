# Unit 4: Overlay & Keyword Routing

> **Motto**: *Teach AGENTS at runtime*

## In Plain Language
This unit explains how OMX changes session behavior without hardcoding everything into CLI flags. It looks at the user's text, decides whether a skill should activate, writes that state to disk, and then injects a temporary overlay into `AGENTS.md`.

## Background Knowledge
- **Keyword routing as a metal detector**: The detector looks for a few special signals and ignores the rest. In technical terms, OMX scans the prompt for explicit skill invocations or weighted keywords.
- **Overlay as a removable insert page**: You can slip an insert into a handbook for one meeting and remove it later. In technical terms, runtime context is marker-bounded so it can be replaced safely.

## Key Terminology
- **Skill activation**: A record saying which workflow skill is currently active.
- **Marker-bounded overlay**: Text placed between start and end markers so it can be regenerated without corrupting the base file.
- **Project memory**: Short persisted notes about stack, conventions, or current mode that get surfaced to Codex.

## What This Unit Does
The unit keeps only the part of OMX that matters for understanding the idea: detect a skill, write a `skill-active-state.json` file, build an overlay, and merge that overlay into a demo `AGENTS.md`. That is enough to teach the runtime mental model without pulling in the whole hook system.

## Key Code Walkthrough
`index.js:18-43` is the detection engine. The most important rule is at `index.js:20-29`: an explicit `$team` or `$ralph` invocation beats fuzzy keyword matches. That is why OMX can offer ergonomic keywords without becoming unpredictable.

`index.js:45-62` writes the persisted activation state, which mirrors the real repository's habit of storing mode and skill state under `.omx/`. `index.js:64-93` builds the overlay text and applies it using the marker-bounded replacement strategy.

The runnable demo at `index.js:95-130` creates a tiny `AGENTS.md`, activates `$team`, writes `skill-active-state.json`, and then rewrites the file with the overlay attached.

## How to Run
```bash
cd /root/key_projects/learn-codebase/speedrun-oh-my-codex
node unit-4-overlay-routing/index.js
```

## Expected Output
You should see a JSON object whose `activation.skill` is `team`. The demo workspace should contain both `AGENTS.md` and `.omx/state/skill-active-state.json`.

## Exercises
### Explain It Back
Why is it useful for explicit `$skill` syntax to outrank fuzzy keyword matches?

### Modify It
- Remove the `$team` prefix from the sample input and see which keyword match wins instead.
- Add a new keyword definition for `review` and confirm the detector can activate it.

## Debug Guide
### Observation Points
File: `index.js:18`
What to observe: The branch where explicit skill invocations outrank keyword matches.
Breakpoint or log: Inspect `explicit` and the returned activation object.

File: `index.js:45`
What to observe: The persisted state payload that later OMX components can read.
Breakpoint or log: Inspect `payload` before it is written.

File: `index.js:84`
What to observe: How an existing marker block is removed before a new overlay is appended.
Breakpoint or log: Inspect `withoutExisting` and `overlayText`.

### Common Failures
Symptom: The detector returns `default`.
Cause: The sample text no longer contains a supported explicit invocation or keyword.
Fix: Add `$team`, `$ralph`, or another supported phrase back into the input.
Verify: Re-run and confirm `activation.skill` is not `default`.

Symptom: The overlay duplicates on each run.
Cause: The marker replacement logic was removed or the marker text changed.
Fix: Restore the marker-bounded replacement in `applyOverlay()`.
Verify: Run twice and confirm only one marker block remains in `AGENTS.md`.

Symptom: `skill-active-state.json` is never written.
Cause: The state directory write step was skipped.
Fix: Restore the `writeSkillActivationState()` call in the demo.
Verify: Re-run and confirm the JSON file exists under `.omx/state/`.

### State Inspection
- Inspect the activation file: `cat unit-4-overlay-routing/demo-workspace/.omx/state/skill-active-state.json`
- Inspect the merged `AGENTS.md`: `sed -n '1,80p' unit-4-overlay-routing/demo-workspace/AGENTS.md`

### Isolation Testing
- Run `node --input-type=module -e "import { detectSkillActivation } from './unit-4-overlay-routing/index.js'; console.log(detectSkillActivation('plan this before coding'))"` from the speedrun root.
- Change the overlay input arrays in `buildRuntimeOverlay()` and confirm the rendered block changes.
- Use the `Unit 4: Overlay & Keyword Routing` VS Code launch config to step through the marker replacement.
