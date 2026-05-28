# Unit 5: Team Runtime

> **Motto**: *Durable coordination beats ad-hoc fanout*

## In Plain Language
This unit explains why OMX has a separate `team` runtime instead of simply spawning a few agents and hoping for the best. The runtime needs phases, task ownership, worker identities, worktree paths, and a shared state root that survives across turns.

## Background Knowledge
- **Runtime as a project manager's binder**: The binder tracks workers, tasks, and phase changes so nothing is lost between meetings. In technical terms, OMX persists team metadata under `.omx/team/...`.
- **Phase machine as traffic lights**: You are allowed to move only in certain directions. In technical terms, `team-plan -> team-prd -> team-exec -> team-verify` is a constrained state machine.
- **Worktree as a separate desk**: Each worker gets its own desk so edits do not collide. In technical terms, team mode plans a distinct worktree path per worker.

## Key Terminology
- **Team phase**: The current step in the durable execution lifecycle, such as `team-plan` or `team-exec`.
- **Manifest**: Metadata describing the team name, requested task, worker count, and state root.
- **Worktree path**: The filesystem location where an individual worker would operate.

## What This Unit Does
The unit creates a small but realistic team runtime. It sanitizes a team name, builds tasks, assigns those tasks to workers, writes state files under `.omx/team/...`, and then advances the phase into execution to show live progress.

## Key Code Walkthrough
`index.js:17-65` is the phase machine. The important idea is that `advancePhase()` will reject invalid jumps, which mirrors the original repository's attempt to keep multi-step teamwork from drifting into nonsense states.

`index.js:67-111` builds the data that later gets persisted: task list, worker list, inbox paths, and JSON state files. `index.js:134-170` ties that together in `startTeamRuntime()`, including the key lesson at `index.js:167-169`: durable coordination needs a shared state root.

The demo at `index.js:173-191` starts a runtime, advances two phases, marks one task complete and one in progress, and then prints a compact snapshot.

## How to Run
```bash
cd /root/key_projects/learn-codebase/speedrun-oh-my-codex
node unit-5-team-runtime/index.js
```

## Expected Output
You should see a JSON snapshot with `phase: "team-exec"`, `workerCount: 3`, and task counts showing one completed task, one in-progress task, and one pending task.

## Exercises
### Explain It Back
Why is a shared state root under `.omx/team/` better than keeping all team state in memory?

### Modify It
- Increase `workerCount` to `4` and inspect how task assignment spreads across workers.
- Force a `team-fix` loop by calling `advancePhase(runtime.state, "team-fix", "...")` after verification, then study `current_fix_attempt`.

## Debug Guide
### Observation Points
File: `index.js:17`
What to observe: The allowed transition table and the fix-attempt counter.
Breakpoint or log: Step into `advancePhase()` with both valid and invalid targets.

File: `index.js:90`
What to observe: How worker records get their own worktree and inbox paths.
Breakpoint or log: Inspect the worker objects returned by `buildWorkers()`.

File: `index.js:134`
What to observe: The full runtime object right before it is persisted.
Breakpoint or log: Inspect `runtime.manifest`, `runtime.tasks`, and `runtime.workers`.

### Common Failures
Symptom: Transitioning phases throws `Invalid transition`.
Cause: The requested next phase is not allowed from the current phase.
Fix: Follow the legal order defined in `advancePhase()`.
Verify: Re-run with `team-plan -> team-prd -> team-exec`.

Symptom: The snapshot shows all tasks as pending.
Cause: The demo never updated task statuses after starting the runtime.
Fix: Restore the status updates at `index.js:186-187`.
Verify: Re-run and confirm the counts change.

Symptom: Worktree paths look wrong or empty.
Cause: Worker records were not created with the expected state root.
Fix: Check the `stateRoot` passed into `buildWorkers()`.
Verify: Re-run and inspect the `worktrees` array in the JSON snapshot.

### State Inspection
- Inspect the manifest: `cat unit-5-team-runtime/demo-workspace/.omx/team/*/manifest.json`
- Inspect task state: `cat unit-5-team-runtime/demo-workspace/.omx/team/*/tasks.json`
- Inspect worker state: `cat unit-5-team-runtime/demo-workspace/.omx/team/*/workers.json`

### Isolation Testing
- Run `node --input-type=module -e "import { createTeamState, advancePhase } from './unit-5-team-runtime/index.js'; const state=createTeamState('demo'); console.log(advancePhase(state,'team-prd','ok'))"` from the speedrun root.
- Change `buildTasks()` so the second task belongs to `designer` and confirm the manifest still works.
- Use the `Unit 5: Team Runtime` VS Code launcher to watch the runtime object before and after persistence.
