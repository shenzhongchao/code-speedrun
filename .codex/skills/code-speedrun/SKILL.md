---
name: code-speedrun
description: >
  Speedrun any codebase by decomposing it into minimal, independently runnable units — run first,
  read later. Accepts GitHub URLs — clones the repo locally before analysis. Use when the user
  wants to: (1) quickly understand a codebase by running it, not reading it, (2) break down a
  complex project into bite-sized pieces they can execute and debug, (3) understand a codebase
  well enough to build a demo or reimplementation, (4) flatten the learning curve of a large
  or unfamiliar repo. Triggers on phrases like "speedrun this codebase", "learn this codebase",
  "break down this project", "study this repo", "understand this code", "run to learn",
  "decompose for learning", "teach me this codebase", "I want to reimplement this",
  or a GitHub URL like "https://github.com/user/repo".
---

# Code Speedrun

Decompose a codebase into a sequence of self-contained, runnable learning units. Each unit isolates one core concept, runs independently, and includes foundational knowledge and a debugging guide. The end goal: the learner can reimplement a working demo.

All concept explanations, code walkthroughs, and `// LEARN:` comments apply the Feynman method: explain in plain language first, use concrete analogies, then add technical precision. See [references/feynman-method.md](references/feynman-method.md) for detailed patterns and examples.

## Workflow

### Phase 0: Source Acquisition

If the user provides a GitHub URL (or any git remote URL):

1. Clone the repo locally:
   ```bash
   git clone --depth 1 <url> /path/to/<repo-name>
   ```
   Use `--depth 1` for faster cloning unless the user needs full history. Default target: `./<repo-name>`.
2. Record the source URL — it will be referenced in `speedrun-<repo-name>/README.md` (see Phase 3).
3. Proceed to Phase 1 (analyze the cloned directory).

If the user points to a local directory, skip this phase.

**Output location**: The `speedrun-<repo-name>/` directory is always created as a sibling of the source project, not inside it. This avoids polluting the original repo's git state.

```
parent-dir/
├── <repo-name>/                # Original project (untouched)
└── speedrun-<repo-name>/       # Generated learning units
```

### Phase 1: Codebase Analysis

1. Map the project structure — entry points, core modules, data flow, dependencies
2. Identify the runtime: language, framework, build system, key libraries
3. Trace the primary execution path (e.g., request lifecycle, event loop, CLI dispatch)
4. Note external dependencies that units will need to mock or stub

### Phase 2: Decomposition into Learning Units

Split the codebase into 4–8 units following these rules:

- **Overall-first**: Unit 1 must be an end-to-end overview that runs the complete main flow (e.g., request in → process → response out). **Unit 1 imports and calls modules exported by Units 2+**, wiring them into a real orchestration — NOT inline stubs with `print`/`console.log` faking the flow. The learner sees real module boundaries, real imports, and a real dependency graph. Subsequent units zoom into specific areas of this overview.
- **No standalone infrastructure units**: Config, types, logging, and similar infrastructure do NOT get their own unit. Weave them into the units where they're actually used.
- **Single concept**: Each unit (2+) teaches one architectural idea (e.g., "message routing", "container isolation", "state persistence") by zooming into a region of the Unit 1 overview.
- **Independently runnable**: Each unit has its own entry point that can be executed and observed in isolation
- **Cross-references**: Each unit's `// LEARN:` comments and README should reference which other units zoom into related areas (e.g., "→ Unit 4 dives deeper into this")

Produce a unit list in this format:

```
Unit 1: Overall — [Project Name]
  Concept:      End-to-end main flow — imports and orchestrates modules from Units 2+
  Teaches:      [What the learner will understand after this unit]
  Source files: [Key files from the original codebase]
  Imports from: Unit 2 (router), Unit 3 (db), Unit 4 (auth), ...
  Runs as:      [How to execute — e.g., "node unit-1-overall/index.ts"]
  Prereqs:      None

Unit 2: [Title]
  Concept:      [One-line description of the core idea]
  Teaches:      [What the learner will understand after this unit]
  Source files: [Key files from the original codebase]
  Exports:      [What this unit exposes for Unit 1 to import — e.g., "createRouter()"]
  Runs as:      [How to execute — e.g., "node unit-2-<slug>/index.ts"]
  Prereqs:      [Units that must be completed first, or "None"]
```

### Phase 2.5: Coverage Review

Before building units, cross-check the unit list against the codebase to catch gaps:

1. **Re-scan the source tree** — list all top-level directories and key files. For each, confirm it is either (a) covered by a unit, or (b) intentionally excluded as infrastructure woven into another unit.
2. **Trace secondary flows** — beyond the primary execution path, check for important secondary flows (error handling, background jobs, migrations, CLI subcommands, webhook handlers, etc.). If any are core to understanding the project, add a unit or expand an existing one.
3. **Check the dependency graph** — review imports/requires across modules. If a heavily-imported module isn't covered by any unit, it's likely a gap.
4. **Output a coverage summary**:

```
Coverage:
  ✅ Covered:  src/router/, src/db/, src/auth/ (Units 1-4)
  ⏭️ Skipped:  src/scripts/, src/migrations/ (infra, woven into Unit 3)
  ⚠️ Gap:      src/webhooks/ — adding as Unit 5
```

If gaps are found, revise the unit list before proceeding to Phase 3.

### Phase 3: Build Each Learning Unit

**Build order**: Build Units 2+ first, then build Unit 1 last. Each Unit 2+ must export a clean public API (function, class, or object). Unit 1 imports these exports and wires them into the end-to-end flow.

For each unit, create a standalone directory `speedrun-<repo-name>/unit-N-<slug>/` containing (Unit 1 is always `unit-1-overall/`):

#### 1. README.md — Foundational Knowledge + Guide

Apply the Feynman method throughout (see [references/feynman-method.md](references/feynman-method.md)):
- Background Knowledge and What This Unit Does: lead with a plain-language analogy before any technical detail
- Key Code Walkthrough: use the simplification checkpoints — every paragraph must pass the "could a junior dev follow this?" test
- Exercises: include at least one "Explain It Back" exercise alongside modification exercises

```markdown
# Unit N: [Title]

## In Plain Language
[1-2 sentences a non-programmer could understand. Use a concrete analogy
to anchor the concept. Example: "This unit is like a mail sorting room —
messages arrive, get sorted by type, and forwarded to the right desk."]

## Background Knowledge
[Foundational concepts needed for this unit. Start each concept with a
plain-language analogy, then add technical precision. Cover relevant CS
concepts, design patterns, protocol details, or library APIs. Assume a
competent developer unfamiliar with this domain. Be concise — link
externally for deep dives.]

## Key Terminology
[Define domain-specific and project-specific terms used in this unit.
Include abbreviations, protocol names, pattern names, and any jargon
the learner will encounter in the code. Format as a definition list:]

- **Term**: Plain-language explanation. If the term originates from a
  specific domain (e.g., distributed systems, compiler theory), note
  the domain and why it matters here.
- **Abbreviation (Full Name)**: What it stands for and its role in
  this context.

## What This Unit Does
[1-2 paragraphs: what this slice accomplishes and why it exists.
Open with the analogy from "In Plain Language", then explain how
the code realizes it.]

## Key Code Walkthrough
[Annotated explanation of important code paths. Reference specific files
and lines within the unit. For each non-obvious design decision, explain
the "why" — what trade-off was made and what alternative was rejected.
Apply simplification checkpoints: no undefined terms, no hand-waving.]

## How to Run
[Exact commands to install deps, build, and run.]

## Expected Output
[What correct execution looks like. Include sample terminal output.]

## Exercises
[2-3 small modifications to deepen understanding, plus at least one
"Explain It Back" exercise — see references/feynman-method.md §3.]

## Debug Guide
[Unit-specific debugging — see references/debug-guide.md for the pattern.]
```

#### 2. Source Code — Minimal Extraction

**Units 2+ — Export a public API**: Each unit must export its core functionality so Unit 1 can import it. The unit's own entry point (e.g., `index.ts`) demonstrates the concept in isolation by calling its own exports with sample data.

**Unit 1 — Import, don't fake**: Unit 1 imports from sibling unit directories using relative paths (e.g., `../unit-2-router/router`). It wires these imports into the end-to-end flow. The learner sees real module boundaries and real data flowing between subsystems.

NEVER do this in Unit 1 (faking the flow with print statements):
```typescript
// ❌ WRONG — teaches nothing about real module boundaries
console.log("→ Routing request to handler...");
console.log("→ Querying database...");
console.log("→ Authenticating user...");
console.log("✓ Response sent");
```

Do this instead (real imports, real orchestration):
```typescript
// ✅ CORRECT — Unit 1 imports and orchestrates real modules
import { createRouter } from "../unit-2-router/router";
import { createDB } from "../unit-3-database/db";
import { authenticate } from "../unit-4-auth/auth";

const db = createDB();
const router = createRouter();

// LEARN: This is the actual request lifecycle — each step calls
// a real module that you'll explore in depth in later units.
const user = authenticate(request);        // → Unit 4 dives deeper
const handler = router.match(request.path); // → Unit 2 dives deeper
const data = handler(db);                   // → Unit 3 dives deeper
```

General rules for all units:
- Extract only code relevant to this unit's concept
- Simplify: remove unrelated error handling, feature flags, irrelevant abstractions
- Add `// LEARN:` comments at key points using the three-layer format from [references/feynman-method.md](references/feynman-method.md): analogy → what → why. Not every comment needs all three layers — use judgment based on complexity.
- Stub external dependencies (third-party APIs, databases, network calls) with mocks returning realistic data shapes. Stubs are for external boundaries — NOT for inter-unit dependencies.

#### 3. Shared Configuration at `speedrun-<repo-name>/` Level

All shared configuration lives in the `speedrun-<repo-name>/` root — not duplicated per unit:

- **`speedrun-<repo-name>/package.json`** (or `requirements.txt`, `Cargo.toml`, etc.) — single dependency manifest for all units. One install command covers everything.
- **`speedrun-<repo-name>/.vscode/launch.json`** — unified debug config with a named entry per unit plus a "Run Current File" entry. The user opens `speedrun-<repo-name>/` in VS Code once and can debug any unit from the dropdown.
- Per-unit directories must NOT contain their own `package.json`, `.vscode/`, or equivalent. Keep them as pure source + README.
- **`speedrun-<repo-name>/README.md`** — top-level overview listing all units, learning path, quick-start commands (`npm install` / `npm run all`), and a brief architecture diagram. This is the single entry point for learners. If the codebase was cloned from a remote URL, include a "Source" section at the top:
  ```markdown
  > **Source**: [repo-name](https://github.com/user/repo) — cloned on YYYY-MM-DD
  ```
- **`speedrun-<repo-name>/SIMPLIFICATIONS.md`** — a checklist documenting every simplification made across all units. This serves two purposes: (a) the learner knows exactly what was omitted, (b) it's a ready-made expansion roadmap. Format:

  ```markdown
  # Simplifications

  What was simplified or stubbed in each unit compared to the original codebase.
  Use this as a checklist to progressively restore real implementations.

  > **Tip**: You can ask a coding agent (Claude Code, Cursor, etc.) to expand
  > any item below. Point it at the original project and this speedrun, e.g.:
  > "Restore real [feature] in unit-3 by referencing ../<repo-name>/src/[file]"

  ## Unit 1: Overall
  - [ ] `database.ts` — stubbed with in-memory object, real impl uses PostgreSQL (`src/db/`)
  - [ ] `auth.ts` — returns hardcoded user, real impl uses JWT (`src/auth/`)
  - [ ] Error handling — removed all try/catch, real impl has centralized error middleware

  ## Unit 2: [Title]
  - [ ] `cache.ts` — stubbed with Map, real impl uses Redis (`src/cache/`)
  - [ ] ...
  ```

  Rules for this file:
  - One checkbox per simplification
  - Each item: what was simplified, how it was simplified, and where the real implementation lives in the original codebase (relative path)
  - Group by unit
  - Keep entries concise — one line each

### Phase 4: Verification

Run every unit sequentially and confirm each completes without errors.

## Debugging Patterns

When writing the Debug Guide section for each unit, follow the patterns in [references/debug-guide.md](references/debug-guide.md). Cover:

1. **Observation points** — where to add logs or breakpoints to see the concept in action
2. **Common failures** — what goes wrong and how to diagnose
3. **State inspection** — how to examine runtime state (variables, DB, network)
4. **Isolation testing** — how to test this unit's logic without the rest of the system

## Principles

- **Feynman-first**: Every explanation starts in plain language with a concrete analogy. Technical precision is layered on top, never leads. If you can't explain it simply, the explanation isn't ready.
- **Overall → Zoom-in**: Start with the full picture (Unit 1 overall), then zoom into each subsystem. Never start with config or infrastructure.
- **Runnable over readable**: Every unit must execute. A unit that only explains is incomplete.
- **Minimal extraction**: Copy the least code possible. Stub everything else.
- **Real data shapes**: Mocks return data matching the real system's shape, not `{ foo: "bar" }`.
- **Debug-first**: Each unit should be easier to debug than the full codebase. That's the whole point.
- **Terminology-rich**: Never assume the learner knows domain jargon. Every unit must define specialized terms (protocol names, pattern names, abbreviations, framework-specific concepts) in its Key Terminology section before using them in code or explanations.
- **Explain-it-back**: Each unit includes at least one exercise where the learner must articulate a concept in their own words. This surfaces understanding gaps that code-modification exercises miss.
