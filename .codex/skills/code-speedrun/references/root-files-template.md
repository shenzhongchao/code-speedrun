# Root Files Template

Use these patterns for files at `speedrun-<repo-name>/`.

## Root `README.md`

```markdown
# Speedrun: [Project Name]

> **Source**: [repo-name](https://github.com/user/repo) — cloned on YYYY-MM-DD

## What [Project Name] Is
[2-4 sentence plain-language synopsis of the original project.
State what it does, who/what it is for, and name the major subsystems if relevant.]

## What This Speedrun Covers
[1 short paragraph on scope.]

## Quick Start
[Install command]
[How to run Unit 1]
[How to run all units, if applicable]

## Learning Path

| Unit | Title | Motto | Concept |
|------|-------|-------|---------|
| 1 | Overall | *[Motto]* | End-to-end main flow |
| 2 | [Title] | *[Motto]* | [Concept] |

## Architecture At A Glance
[Very short bullet list or diagram.]

## Debugging
[How to use the root `.vscode/launch.json` or equivalent debugger config.]
```

Rules:

- If there is no remote source URL, omit the Source block instead of inventing one.
- The root README must explain the original project before it explains the speedrun scope.
- Keep Quick Start copy-pasteable.
- Make the Learning Path table complete for every unit.
- Keep this file as the single entry point for learners.

## Root `SIMPLIFICATIONS.md`

```markdown
# Simplifications

What was simplified or stubbed compared to the original codebase.
Use this file as the roadmap for restoring real behavior later.

## Unit 1: Overall
- [ ] `database.ts` — replaced with in-memory state, original in `src/db/`
- [ ] Error middleware — removed centralized error path, original in `src/server/middleware/`

## Unit 2: Router
- [ ] Route registry — hardcoded two routes, original in `src/router/`
```

Rules:

- One checkbox per meaningful simplification.
- Each line must say what changed and where the real implementation lives.
- Group strictly by unit.
- Do not hide big omissions in prose. If it matters, give it a checkbox.
