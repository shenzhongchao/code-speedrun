# Simplifications

What was simplified or stubbed compared to the original codebase.
Use this file as the roadmap for restoring real behavior later.

## Unit 1: OMX End-to-End
- [ ] The launch path stops after building overlay and summaries; the real Codex spawn flow lives in `src/cli/index.ts`.
- [ ] Team progress is advanced by direct function calls instead of real tmux events and worker heartbeats; the real behavior lives in `src/team/runtime.ts`.

## Unit 2: Command Router
- [ ] Only `launch`, `resume`, `setup`, `team`, `sparkshell`, and `help` are modeled; the full command matrix lives in `src/cli/index.ts`.
- [ ] Unknown-command handling is simplified to a default help route; the real CLI also handles local help ownership and launch fallbacks in `src/cli/index.ts`.

## Unit 3: Setup & Config
- [ ] Only two prompts and two skills are installed; the real asset set lives under `prompts/` and `skills/`.
- [ ] TOML merge logic is reduced to a small managed block; the real selective upsert and cleanup logic lives in `src/config/generator.ts`.

## Unit 4: Overlay & Keyword Routing
- [ ] Keyword detection covers only a tiny subset of the registry; the real trigger set lives in `src/hooks/keyword-registry.ts`.
- [ ] Overlay locking, truncation, and multi-section priority rules are omitted; the real implementation lives in `src/hooks/agents-overlay.ts`.

## Unit 5: Team Runtime
- [ ] Worktrees are represented as planned paths only; the real git worktree provisioning lives in `src/team/worktree.ts`.
- [ ] No tmux panes or worker subprocesses are launched; the real durable coordination logic lives in `src/team/runtime.ts` and `src/team/tmux-session.ts`.

## Unit 6: Native Boundaries
- [ ] Rust runtime and sparkshell behavior are simulated in JavaScript because this workspace does not have Cargo installed; the real binaries live in `crates/omx-runtime/` and `crates/omx-sparkshell/`.
- [ ] Explore routing and output summarization cover only the happy path; the real fallback and hydration logic lives in `src/cli/explore.ts` and `src/cli/sparkshell.ts`.
