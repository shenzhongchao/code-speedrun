# Speedrun: DeerFlow Backend

> **Source**: [deer-flow](https://github.com/bytedance/deer-flow) — cloned on 2026-03-23

## What DeerFlow Is

DeerFlow 是一个开源的 **super agent harness**。简单说，它不是单纯的“聊天机器人 UI”，也不是只会单轮问答的 agent demo；它是一套把 **LLM、工具调用、子代理、记忆、sandbox、skills** 这些能力编排在一起的后端框架。它的目标是让 agent 不只是“回答问题”，而是真的能在受控环境里读写文件、执行命令、委派子任务、调用外部工具，并把这些动作组织成一条可持续运行的工作流。

从系统拆分上看，DeerFlow 主要有两层：

- `frontend/`：Next.js 界面层，负责聊天交互和可视化
- `backend/`：Python/LangGraph 主干，负责 gateway、agent runtime、tool orchestration、sandbox、memory、subagents

这份 speedrun 只拆后者，因为后端才是 DeerFlow 最核心的“能做事”的部分。

## What This Speedrun Covers

这个 speedrun 明确只覆盖 DeerFlow 的 **Python backend 主干**，不覆盖 Next.js 前端。原因很直接：原仓库是 Python + Node.js 的 monorepo，而 `Unit 1` 必须真实 import 其它单元。跨运行时去拼“总装脚本”会变成人造讲解，不利于把主链路跑通。这里保留的主链路是：**Gateway API 收到请求 -> Thread Runtime 分配线程目录和 sandbox -> Lead Agent Factory 解析运行时参数 -> Tool Registry 选出可用工具 -> Local Sandbox 执行命令和文件读写**。

覆盖情况：

- 直接覆盖：`backend/app/gateway/`、`backend/packages/harness/deerflow/agents/`、`backend/packages/harness/deerflow/tools/`、`backend/packages/harness/deerflow/sandbox/`
- 织入讲解：memory、skills prompt、subagents、uploads conversion、tool search
- 明确排除：`frontend/`、`docker/`、`skills/`、IM channels、测试与 CI

## Quick Start

```bash
cd cases/speedrun-deer-flow
python -m pip install -r requirements.txt
python unit-1-overall-backend-flow/main.py
```

运行任意单元：

```bash
python unit-2-gateway-config/main.py
python unit-3-thread-runtime/main.py
python unit-4-lead-agent-factory/main.py
python unit-5-tools-sandbox/main.py
```

## Learning Path

| Unit | Title | Motto | Concept |
|------|-------|-------|---------|
| 1 | Overall Backend Flow | *One request, five moving parts* | End-to-end backend main flow that imports and orchestrates Units 2-5 |
| 2 | Gateway and Config | *HTTP is the front desk* | FastAPI-style boundary for config-backed APIs and uploads |
| 3 | Thread Runtime | *Each thread gets its own backpack* | Per-thread paths and sandbox assignment through middleware |
| 4 | Lead Agent Factory | *Assemble, do not hardcode* | Resolve runtime flags into model, middleware, prompt, and tools |
| 5 | Tools and Sandbox | *Tools need safe hands* | Tool registry plus local sandbox command and file execution |

## Architecture At A Glance

- `Unit 2` 解释为什么 DeerFlow 把“模型列表、文件上传”做成 Gateway API，而不是塞进 LangGraph。
- `Unit 3` 解释 thread id 如何变成 `workspace / uploads / outputs` 三个路径，再挂上 `sandbox_id`。
- `Unit 4` 解释 `make_lead_agent()` 的真正价值：不是“多写几个 if”，而是把运行时参数翻译成模型、中间件和工具选择。
- `Unit 5` 解释工具来源和本地 sandbox 的最小执行面。
- `Unit 1` 用真实 import 把前四个单元串起来，模拟一次后端请求。

## Debugging

打开 `cases/speedrun-deer-flow/` 到 VS Code，直接使用根目录的 `.vscode/launch.json`：

- `Unit 1: Overall Backend Flow`
- `Unit 2: Gateway and Config`
- `Unit 3: Thread Runtime`
- `Unit 4: Lead Agent Factory`
- `Unit 5: Tools and Sandbox`
- `Run Current File`

调试顺序建议先跑 `Unit 1`，再遇到不懂的地方跳到对应子单元。这样你会先看到完整链路，再拆开每一块。

## Back To Source

当你跑完这 5 个单元，下一步不要盲读整个仓库。先看 [ORIGINAL-READING-PATH.md](/root/key_projects/learn-codebase/cases/speedrun-deer-flow/ORIGINAL-READING-PATH.md)，按单元对照回到真实 DeerFlow 源码。那份文档会告诉你每个 speedrun 单元对应原仓哪些文件、建议先读哪几个入口、以及用什么 `rg` / `sed` 命令快速定位。
