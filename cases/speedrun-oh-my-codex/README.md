# Speedrun: oh-my-codex

Languages: [English](./README.md) | [简体中文](./README_zh.md)

> **Source**: [oh-my-codex](https://github.com/Yeachan-Heo/oh-my-codex) — cloned on 2026-04-07

## What oh-my-codex Is
oh-my-codex, usually shortened to OMX, is a workflow layer around OpenAI Codex CLI. It keeps Codex as the execution engine, then adds reusable prompts and skills, runtime overlays for `AGENTS.md`, durable `.omx/` state, and a tmux/worktree-backed team mode when one session is not enough. The original repository is mostly Node/TypeScript CLI code, with a few Rust crates used as narrow native sidecars for runtime contracts and shell-oriented helpers.

## What This Speedrun Covers
This speedrun focuses on the main architectural spine: how the `omx` entrypoint parses commands, installs its working layer, injects runtime context, starts durable team execution, and talks to native helpers through stable contracts. It intentionally leaves out docs, missions, playground demos, release tooling, and many optional subcommands so you can learn the core flow without reading the whole repository.

## Quick Start
```bash
cd /root/key_projects/learn-codebase/speedrun-oh-my-codex
npm install
node unit-1-overall/index.js
```

There are no external package dependencies in this speedrun, so `npm install` is mostly a quick environment sanity check.

Run any unit directly:

```bash
node unit-2-command-router/index.js
node unit-3-setup-config/index.js
node unit-4-overlay-routing/index.js
node unit-5-team-runtime/index.js
node unit-6-native-boundaries/index.js
```

## Learning Path

| Unit | Title | Motto | Concept |
|------|-------|-------|---------|
| 1 | OMX End-to-End | *One CLI, many moving parts* | End-to-end main flow |
| 2 | Command Router | *Parse first, branch later* | Turn argv into OMX command intent |
| 3 | Setup & Config | *Install the working layer* | Install prompts, skills, hooks, and managed config |
| 4 | Overlay & Keyword Routing | *Teach AGENTS at runtime* | Detect skills and inject session-specific overlay text |
| 5 | Team Runtime | *Durable coordination beats ad-hoc fanout* | Persist workers, tasks, phases, and worktree paths |
| 6 | Native Boundaries | *Keep the native seam narrow* | Talk to runtime and sparkshell helpers through contracts |

## Architecture At A Glance
- Unit 2 explains why `omx --madmax --high` is still just a normal launch command.
- Unit 3 shows that `omx setup` is really an installer for a filesystem layout, not just a TOML writer.
- Unit 4 shows how OMX treats `AGENTS.md` as a runtime surface, not a static document.
- Unit 5 shows why `omx team` needs durable state under `.omx/` instead of loose in-memory fanout.
- Unit 6 shows how Rust helpers stay behind narrow JSON and argv contracts.

## Debugging
Open `/root/key_projects/learn-codebase/speedrun-oh-my-codex` in VS Code and use the root [.vscode/launch.json](./.vscode/launch.json) configurations. Each unit has its own named launch target, and `Run Current File` works for quick step-through debugging when you want to instrument a single extracted file.
