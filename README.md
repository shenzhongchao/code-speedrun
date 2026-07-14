# Code Speedrun

> Everything to Nano

Turn complex codebases into minimal, runnable learning units. Here, "Nano" means the smallest unit you can run, inspect, and actually understand.

An AI skill that decomposes any codebase into minimal, independently runnable units — so you can understand a project by running it, not reading it.

## Why

Reading code is slow. Reading documentation is slower. Tools like DeepWiki generate thorough codebase analyses, but passively reading walls of text gives almost no feedback — it's easy to zone out within minutes.

The real "aha" moments come from running code and seeing what happens. A breakpoint hit, a log printed, an output changed — that's instant feedback. That's what keeps you engaged.

Code Speedrun flips the approach: instead of reading a codebase top-down, it extracts a sequence of bite-sized units you can execute, modify, and debug. Unit 1 gives you the full picture as a stubbed end-to-end flow you can run in seconds. Each subsequent unit zooms into one subsystem. You build understanding through doing, not reading.

## How It Works

1. Point it at a GitHub URL or local directory
2. It analyzes the codebase and decomposes it into 4–8 runnable units
3. Each unit is a standalone mini-project with its own entry point, README, and debug config
4. Unit 1 is always an end-to-end overview — the complete main flow with stubs
5. Units 2+ zoom into specific subsystems (routing, storage, auth, etc.)

Output structure:

```
speedrun-<repo-name>/
├── README.md                  # Learning path & quick start
├── package.json               # Shared dependencies
├── .vscode/launch.json        # Debug config for all units
├── unit-1-overall/            # End-to-end flow with stubs
│   ├── README.md
│   └── index.ts
├── unit-2-<slug>/             # Zoom into subsystem A
│   ├── README.md
│   └── ...
└── unit-N-<slug>/             # Zoom into subsystem N
    ├── README.md
    └── ...
```

## Key Design Decisions

- **Run first, read later** — every unit has an entry point you can execute before reading a single line of explanation
- **Overall → Zoom-in** — Unit 1 builds the global mental model; subsequent units fill in details
- **Feynman method** — all explanations start with plain-language analogies, then layer on technical precision
- **Debug-friendly** — VS Code launch configs included; each unit is easier to debug than the original codebase
- **Explain It Back** — each unit includes exercises where you articulate concepts in your own words, surfacing gaps that code-modification exercises miss

## Usage

This is a skill for [Claude Code](https://docs.anthropic.com/en/docs/claude-code). To use it:

copy .claude/skills/code-speedrun to .claude/skills/ in your project dir or to ~/.claude/skills/, and launch claude:

```
speedrun this codebase: https://github.com/user/repo
```

Or point it at a local directory:

```
break down ./my-project for learning
```

## Case Study: Protenix (Protein Structure Prediction)

[Protenix](https://github.com/bytedance/Protenix) is a production-grade protein structure prediction system similar to AlphaFold3 — ~50k lines of Python/PyTorch with custom CUDA kernels, diffusion-based coordinate generation, and multi-chain complex handling.

Code Speedrun decomposed it into 7 runnable units:

| Unit | Topic | What You Learn |
|------|-------|----------------|
| 1 | End-to-end overview | Full prediction pipeline with stubs |
| 2 | Data pipeline | Protein sequence → tokens → feature tensors |
| 3 | Input embedding | AtomAttentionEncoder + relative position encoding |
| 4 | Pairformer | Triangle attention + triangle multiplicative updates |
| 5 | Diffusion module | Denoising diffusion for 3D coordinate generation |
| 6 | Confidence & output | pLDDT/PAE/PTM quality assessment |
| 7 | Training loop | Full forward path + loss functions + label permutation + EMA |

Each unit runs in seconds with `python unit-N-<slug>/main.py` — no GPU, no 50GB model weights, no database downloads. The generated `speedrun-Protenix/` also includes a [simplification checklist](Protenix/SIMPLIFICATIONS.md) mapping every shortcut back to the original source files, so you can progressively expand each unit toward the real implementation with AI coding tools.

## Case Study: DeerFlow (Super Agent Harness)

[DeerFlow](https://github.com/bytedance/deer-flow) is an open-source super agent harness — not a chatbot UI, not a single-turn agent demo, but a backend framework that orchestrates LLMs, tool calls, subagents, memory, sandboxes, and skills into a coherent runtime. Its backend (~Python/LangGraph) is the brain; the Next.js frontend is just the face.

Code Speedrun decomposed the backend into 10 runnable units:

| Unit | Topic | What You Learn |
|------|-------|----------------|
| 1 | Overall backend flow | Full request-to-response pipeline importing Units 2-10 |
| 2 | Gateway & config | FastAPI boundary for models, uploads, and config-backed APIs |
| 3 | Thread runtime | Per-thread host paths, `/mnt/user-data` virtual paths, sandbox assignment |
| 4 | Lead agent factory | Resolve runtime flags into model, middleware, prompt, and tools |
| 5 | Tools & Docker sandbox | LangGraph tool-calling loop + OpenAI-compatible LLM + sandbox execution |
| 6 | Skills prompt system | Scan skills, apply enabled state, inject compact prompt index |
| 7 | Memory lifecycle | Filter conversation, update memory JSON, inject next prompt context |
| 8 | Subagent delegation | Background task execution with filtered tools and progress events |
| 9 | MCP deferred tools | Config mtime cache, deferred registry, `tool_search` discovery |
| 10 | Artifacts & archive safety | Thread-scoped artifact serving and safe `.skill` archive inspection |

Unit 1 ties all 10 together with real imports, simulating one backend request and five secondary flow summaries. After running the speedrun, the included [reading path](cases/speedrun-deer-flow/ORIGINAL-READING-PATH.md) maps every unit back to the original DeerFlow source files — with 90-minute and 180-minute routes depending on how deep you want to go.

## License

MIT
