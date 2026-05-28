# Unit 2: Command Router

> **Motto**: *Parse first, branch later*

## In Plain Language
This unit explains how OMX decides what kind of session you are asking for. It turns raw argv into a small, structured meaning so the rest of the system does not need to guess.

## Background Knowledge
- **Parser as a translator**: A translator turns messy speech into a clear message. In technical terms, `parseInvocation()` converts an argument list into a typed command shape.
- **Handler table as a switchboard**: A switchboard does not solve the request; it connects the caller to the right line. In technical terms, `routeInvocation()` maps a command to its handler.

## Key Terminology
- **Launch invocation**: A command meaning "start Codex", even when the user only typed flags.
- **Subcommand**: A named branch like `setup`, `team`, or `sparkshell`.
- **Team args**: The worker-count, agent-type, and task bundle derived from `omx team`.

## What This Unit Does
The unit reproduces the essential OMX CLI parsing rules in one file. It demonstrates the three most important ideas: bare flags become `launch`, `team` needs its own argument normalization, and routing should stay separate from business logic.

## Key Code Walkthrough
`index.js:13-34` normalizes `team` arguments into `workerCount`, `agentType`, and `task`. This mirrors the real CLI's need to turn a compact token like `3:executor` into explicit runtime values.

`index.js:36-80` is the core parser. The rule at `index.js:40-47` is the key OMX mental model: if the first token is missing or starts with `--`, the user is still trying to launch Codex. `index.js:82-93` then routes the parsed result to a handler without knowing what the handler will do.

The demo at `index.js:118-157` runs five sample inputs through the parser and router. Read that block if you want the fastest possible summary of the command surface.

## How to Run
```bash
cd /root/key_projects/learn-codebase/speedrun-oh-my-codex
node unit-2-command-router/index.js
```

## Expected Output
You should see an array of routed examples. The first example should map `["--madmax","--high"]` to `launchWithHud`, and the third example should map `team` input to `teamCommand`.

## Exercises
### Explain It Back
Why does OMX treat `omx --high` as a launch request instead of an unknown command?

### Modify It
- Add support for a new subcommand called `doctor`.
- Change the default team worker count from `3` to `2` and watch how the parsed output changes.

## Debug Guide
### Observation Points
File: `index.js:13`
What to observe: How `3:executor` turns into structured team settings.
Breakpoint or log: Inspect `match` and the returned object from `normalizeTeamArgs()`.

File: `index.js:36`
What to observe: How the first token decides the parse branch.
Breakpoint or log: Log `first` and step through each `if` block with different sample inputs.

File: `index.js:82`
What to observe: The parsed command being handed off to a handler table.
Breakpoint or log: Inspect `handler` before it runs.

### Common Failures
Symptom: `team` input produces an empty task string.
Cause: The task words were not included after the `3:executor` token.
Fix: Pass at least one task word after the staffing token.
Verify: Re-run and confirm `task` is non-empty.

Symptom: `--high` becomes `unknown`.
Cause: The launch fallback branch was changed or removed.
Fix: Restore the `first.startsWith("--")` check at `index.js:42`.
Verify: Re-run and confirm the first demo sample routes to `launchWithHud`.

Symptom: Routing throws `No handler registered`.
Cause: A parsed command no longer has a matching handler in the demo table.
Fix: Add the missing handler or provide a `default` handler.
Verify: Re-run and confirm every sample returns a routed result.

### State Inspection
- Inspect the demo inputs directly in code at `index.js:108-116`.
- Run `node --input-type=module -e "import { parseInvocation } from './unit-2-command-router/index.js'; console.log(parseInvocation(['team','2:planner','draft','scope']))"` from the speedrun root.

### Isolation Testing
- Call `parseInvocation([])` from a Node REPL and confirm it returns `command: "launch"`.
- Call `normalizeTeamArgs(['4:verifier','audit','the','handoff'])` and confirm the parsed staffing values.
- Use the `Unit 2: Command Router` VS Code launch config and step through one sample at a time.
