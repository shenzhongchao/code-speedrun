---
name: code-speedrun
description: >
  Speedrun any codebase by decomposing it into minimal, independently runnable units — run first,
  read later. Accepts GitHub URLs and local directories. Use when the user wants to: (1) quickly
  understand a codebase by running it instead of only reading it, (2) break down a complex project
  into small pieces they can execute and debug, (3) learn a codebase well enough to build a demo
  or reimplementation, (4) flatten the learning curve of a large or unfamiliar repository. Triggers
  on requests like "speedrun this codebase", "learn this repo", "teach me this codebase",
  "break down this project", "run to learn", or a repository URL.
---

# Code Speedrun

Decompose a codebase into self-contained, runnable learning units. The learner should be able to run each unit, inspect it with a debugger, and finish with enough understanding to rebuild a small working version.

Write all explanations, walkthroughs, and `// LEARN:` comments in Feynman style: plain language first, then technical precision. See [references/feynman-method.md](references/feynman-method.md).

Load bundled resources only when needed:

- Use [references/runtime-selection.md](references/runtime-selection.md) after identifying the runtime and toolchain.
- Use [references/unit-readme-template.md](references/unit-readme-template.md) when writing per-unit `README.md` files.
- Use [references/root-files-template.md](references/root-files-template.md) when writing the top-level `README.md` and `SIMPLIFICATIONS.md`.
- Use [references/debug-guide.md](references/debug-guide.md) when writing each unit's Debug Guide and the root `.vscode/launch.json`.
- Use [references/verification-checklist.md](references/verification-checklist.md) before handoff.
- Use `scripts/scaffold_speedrun.py` to generate the directory skeleton when that saves time.
- Use `scripts/verify_speedrun.py` for structural verification before final manual checks.

## Workflow

### Phase 0: Source Acquisition

If the user provides a remote git URL:

1. Resolve the local target directory before cloning. Default target: `./<repo-name>`.
2. If the target directory already exists, do not overwrite it. Reuse it if it is the intended checkout, or pick a different sibling path.
3. Clone shallow by default:
   ```bash
   git clone --depth 1 <url> /path/to/<repo-name>
   ```
4. If clone requires network approval, credentials, submodules, or large-file support, surface that constraint and choose the narrowest workable fallback.
5. If the repo is very large or is a monorepo, scope the speedrun to the relevant subdirectory when possible instead of covering everything.
6. Record the source URL and clone date for the generated root `README.md`.

If the user provides a local directory, skip cloning and analyze that directory directly.

If acquisition fails:

- Prefer a local path the user already has.
- Prefer a scoped subdirectory over a full-repo walkthrough when the repository is too large.
- Do not keep retrying brittle clone/install flows when a local copy or narrower scope will unblock the task.

Create `speedrun-<repo-name>/` as a sibling of the source project, never inside it.

```text
parent-dir/
├── <repo-name>/                # Original project
└── speedrun-<repo-name>/       # Generated learning units
```

### Phase 1: Codebase Analysis

1. Identify the runtime, framework, package manager, test runner, and debugger entry points.
2. Open [references/runtime-selection.md](references/runtime-selection.md) and pick only the section that matches the runtime.
3. Map entry points, core modules, data flow, and key dependencies.
4. Trace the main execution path first, then the most important secondary flows.
5. Mark external boundaries that will need mocks or stubs in learning units.
6. If this is a monorepo, explicitly choose the package or service being speedrun before decomposing units.

### Phase 2: Decomposition into Learning Units

Default to 4-8 units. Go below or above that range only when the codebase size or architecture justifies it, and state the reason in one sentence.

Rules:

- **Overall-first**: Unit 1 is the end-to-end main flow.
- **Real module boundaries**: Unit 1 imports and calls public APIs exported by Units 2+.
- **No fake orchestration**: Do not replace subsystem interactions with `print` or `console.log` narration.
- **Single concept**: Each Unit 2+ teaches one architectural idea.
- **Runnable**: Every unit has its own executable entry point.
- **Infra is woven in**: Config, types, logging, small helpers, and glue code belong inside the units that use them.
- **Exclude low-value areas by default**: Generated code, vendor directories, CI files, benchmarks, and tests do not become standalone units unless they are core to understanding the system.
- **Cross-reference**: READMEs and `// LEARN:` comments should point to related units.

Produce a unit list in this format:

```text
Unit 1: Overall — [Project Name]
  Motto:        [Short memorable phrase]
  Concept:      End-to-end main flow — imports and orchestrates Units 2+
  Teaches:      [What the learner will understand]
  Source files: [Key original files]
  Imports from: Unit 2 (router), Unit 3 (db), Unit 4 (auth)
  Runs as:      [Exact command]
  Prereqs:      None

Unit 2: [Title]
  Motto:        [Short memorable phrase]
  Concept:      [One-line core idea]
  Teaches:      [What the learner will understand]
  Source files: [Key original files]
  Exports:      [Public API imported by Unit 1]
  Runs as:      [Exact command]
  Prereqs:      [Units or None]
```

### Phase 2.5: Coverage Review

Before building units, cross-check the unit list against the source tree:

1. Re-scan top-level directories and key files. Mark each as covered, intentionally woven into another unit, or intentionally excluded.
2. Trace important secondary flows: error handling, jobs, migrations, webhooks, CLI subcommands, background workers, schedulers.
3. Check the dependency graph. If a heavily imported module is missing from the plan, decide whether to add a unit or explicitly weave it into an existing one.
4. Output a short coverage summary before proceeding.

If a meaningful gap remains, revise the unit list first.

### Phase 3: Build the Speedrun

If it helps, scaffold the directory first with `scripts/scaffold_speedrun.py`, then fill in the actual content.

Build Units 2+ first. Build Unit 1 last so it imports real public APIs from the other units.

For each unit:

1. Create `speedrun-<repo-name>/unit-N-<slug>/`.
2. Write `README.md` using [references/unit-readme-template.md](references/unit-readme-template.md).
3. Extract the minimum code needed to teach that concept.
4. Add `// LEARN:` comments only at non-obvious points.
5. Stub only external boundaries. Do not stub inter-unit dependencies.
6. Give the unit an entry point that runs in isolation with sample data.

For Unit 1 specifically:

- Import sibling units with real relative/module imports.
- Demonstrate real data flowing across units.
- Do not narrate subsystem behavior with placeholder logging.

At the speedrun root:

- Keep one shared dependency manifest for the whole speedrun.
- Keep one `.vscode/launch.json` with a named entry per unit plus a `Run Current File` entry.
- Keep unit directories as source plus `README.md`; do not add per-unit `.vscode/` or dependency manifests.
- Write the root `README.md` and `SIMPLIFICATIONS.md` using [references/root-files-template.md](references/root-files-template.md).

### Phase 4: Verification

Run `scripts/verify_speedrun.py <speedrun-dir>` first for structural checks.

Then apply the manual acceptance checklist in [references/verification-checklist.md](references/verification-checklist.md). Do not call the speedrun complete unless all of these are true:

- Every documented run command works from the stated directory.
- Unit 1 really imports and orchestrates Units 2+.
- The root debug configuration points at real unit entry points.
- `SIMPLIFICATIONS.md` lists all meaningful stubs and omissions.
- The generated explanations match the extracted code, not the original repo's complexity.

## Principles

- **Feynman-first**: Explain simply before being precise.
- **Runnable over readable**: Every unit must execute.
- **Overall then zoom-in**: Start with the full picture, then drill into subsystems.
- **Minimal extraction**: Copy the least code necessary to preserve the concept.
- **Real data shapes**: Mock realistic structures, not toy placeholders.
- **Debug-first**: The speedrun must be easier to inspect than the original codebase.
- **Terminology-rich**: Define domain-specific jargon before using it.
- **Explicit simplifications**: Every omission should be traceable in `SIMPLIFICATIONS.md`.
- **Runtime-aware**: Shape commands, debugger config, and file layout to the actual runtime, not a default Node.js mental model.
