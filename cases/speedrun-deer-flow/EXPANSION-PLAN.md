# DeerFlow Speedrun Expansion Plan

这份计划用于继续扩展 `cases/speedrun-deer-flow`，目标是把现有的“后端主干 1.0”升级成更完整的 DeerFlow 后端教学路径。扩展仍然遵守 code-speedrun 的核心标准：每个单元可运行、可调试、按真实源码边界拆解，代码本身要通过少量高价值 `LEARN:` 注释承担教学任务。
deerflow的源代码在`src/deer-flow`

## Current Baseline

现有 speedrun 已覆盖 DeerFlow 后端主链路：

| Unit | 当前主题 | 已覆盖的核心问题 |
|------|----------|------------------|
| 1 | Overall Backend Flow | 一次请求如何串起 gateway、thread runtime、lead agent、tool registry、sandbox |
| 2 | Gateway and Config | Gateway 如何暴露模型列表、上传文件、virtual path 和 artifact URL |
| 3 | Thread Runtime | `thread_id` 如何变成 workspace/uploads/outputs 和 sandbox 状态 |
| 4 | Lead Agent Factory | runtime flags 如何决定模型、中间件、prompt section 和工具 |
| 5 | LangGraph Tools and Docker Sandbox | `model -> tools -> model` 循环和 `/mnt/user-data` sandbox 边界 |

目前缺口不在主链路，而在 DeerFlow 作为 super agent harness 的二级主线：skills、memory、subagent、MCP deferred tools、artifact/skill archive 安全边界。这些能力决定了 DeerFlow 和普通 LangGraph demo 的差别。

## Expansion Goals

1. 补齐 DeerFlow 最有区分度的后端 secondary flows。
2. 保持每个新增单元只有一个教学概念，不把多个复杂机制塞进一个大 demo。
3. 让 `Unit 1` 最终真实 import 新增单元的 public API，而不是只在 README 里提到它们。
4. 所有新增单元默认离线可跑；需要真实 LLM、Docker、MCP server 的路径只能作为 optional live mode。
5. 每个新增单元至少有一个 pytest 覆盖关键状态转移。

## Target Unit List

新增 5 个单元，使最终 speedrun 变成 10 个单元。超过默认 4-8 个单元的原因：DeerFlow 是 Python backend + agent runtime + extension system 的组合，secondary flows 本身就是理解项目的核心，不适合全部织入现有单元。

```text
Unit 6: Skills Prompt System
  Motto:        Skills are recipes the agent can open when needed
  Concept:      Scan SKILL.md files, apply enabled state, and inject a compact skill list into the prompt
  Teaches:      为什么 skills 不是普通工具，而是按需加载的工作流说明书
  Source files: backend/packages/harness/deerflow/skills/*, app/gateway/routers/skills.py, agents/lead_agent/prompt.py
  Exports:      build_skills_prompt_section(), list_demo_skills(), install_demo_skill_archive()
  Runs as:      python unit-6-skills-prompt-system/main.py
  Prereqs:      Unit 2, Unit 4

Unit 7: Memory Lifecycle
  Motto:        Memory keeps lessons, not scratch paper
  Concept:      Filter conversation messages, queue memory updates, write memory JSON, then inject memory into the next prompt
  Teaches:      长期记忆如何避免保存 tool noise 和上传文件临时路径
  Source files: agents/middlewares/memory_middleware.py, agents/memory/queue.py, agents/memory/updater.py, agents/lead_agent/prompt.py
  Exports:      run_memory_lifecycle(), build_memory_context()
  Runs as:      python unit-7-memory-lifecycle/main.py
  Prereqs:      Unit 4, Unit 6 optional

Unit 8: Subagent Delegation
  Motto:        Delegate work, keep the parent context clean
  Concept:      task tool starts a subagent, passes thread/sandbox context, streams progress, then cleans up background state
  Teaches:      DeerFlow 的 subagent 为什么是后台执行链路，而不是普通函数调用
  Source files: tools/builtins/task_tool.py, subagents/executor.py, subagents/config.py, middlewares/subagent_limit_middleware.py
  Exports:      run_subagent_demo(), TaskEvent, SubagentExecutor
  Runs as:      python unit-8-subagent-delegation/main.py
  Prereqs:      Unit 3, Unit 4, Unit 5

Unit 9: MCP Deferred Tools
  Motto:        Do not show every tool until the agent asks
  Concept:      Gateway updates MCP config, cache detects config mtime changes, tool registry defers MCP tools behind tool_search
  Teaches:      外部工具太多时，DeerFlow 如何避免把全部 schema 一次性塞进模型上下文
  Source files: mcp/cache.py, mcp/tools.py, mcp/client.py, app/gateway/routers/mcp.py, tools/tools.py, tools/builtins/tool_search.py
  Exports:      run_mcp_deferred_tools_demo(), DeferredToolRegistry
  Runs as:      python unit-9-mcp-deferred-tools/main.py
  Prereqs:      Unit 2, Unit 5

Unit 10: Artifacts and Archive Safety
  Motto:        Outputs are useful only if serving them is safe
  Concept:      Resolve artifact virtual paths, serve text/binary files, inspect .skill archives, and reject unsafe archive entries
  Teaches:      artifact serving 和 skill installation 为什么必须有路径穿越、symlink、zip bomb 防护
  Source files: app/gateway/routers/artifacts.py, app/gateway/routers/skills.py, app/gateway/path_utils.py
  Exports:      resolve_demo_artifact(), inspect_skill_archive(), validate_archive_members()
  Runs as:      python unit-10-artifacts-archive-safety/main.py
  Prereqs:      Unit 2, Unit 3, Unit 6
```

## Implementation Phases

### Phase 1: Skills and Memory

优先实现 `Unit 6` 和 `Unit 7`，因为它们直接补强 `Unit 4` 中目前只是占位的 `skills prompt` 和 `memory prompt`。

#### Unit 6 Deliverables

- 新目录：`unit-6-skills-prompt-system/`
- 文件：
  - `main.py`
  - `skills_prompt_demo.py`
  - `README.md`
  - `_demo_data/skills/public/research/SKILL.md`
  - `_demo_data/skills/custom/charting/SKILL.md`
  - `_demo_data/extensions_config.json`
- Demo 行为：
  - 扫描 public/custom skill 目录
  - 解析 `SKILL.md` front matter
  - 应用 enabled/disabled 状态
  - 生成 `<skill_system>` prompt section
  - 打包一个 `.skill` ZIP 并演示安装到 custom 目录
- 关键 `LEARN:` 注释位置：
  - front matter 解析处：解释 skill metadata 是 prompt 索引，不是完整加载
  - enabled state 合并处：解释 Gateway 和 LangGraph 分进程，所以状态要从文件重读
  - prompt section 生成处：解释 progressive loading pattern
  - archive install 处：解释安装先解压到 temp，再验证，再复制
- 测试：
  - `tests/test_unit6_skills_prompt.py`
  - 断言 disabled skill 不出现在 enabled prompt 中
  - 断言 prompt location 使用 `/mnt/skills/...`
  - 断言安装 `.skill` 后 custom skill 可被扫描

#### Unit 7 Deliverables

- 新目录：`unit-7-memory-lifecycle/`
- 文件：
  - `main.py`
  - `memory_lifecycle_demo.py`
  - `README.md`
  - `_demo_data/memory.json`
- Demo 行为：
  - 构造一段包含 human、AI tool call、ToolMessage、final AI response、uploaded files block 的消息流
  - 过滤出适合长期记忆的 user/final assistant 对话
  - 用 scripted LLM 生成真实风格的结构化 memory update payload
  - 原子写入 memory JSON
  - 生成下一次 prompt 的 `<memory>` section
  - 展示上传文件路径不会进入长期记忆
- 关键 `LEARN:` 注释位置：
  - message filter：解释 tool results 是过程噪音，不是用户长期偏好
  - upload block scrub：解释 `/mnt/user-data/uploads/...` 是 session-scoped
  - scripted LLM：解释真实版本由 LLM 返回 `user/history/newFacts/factsToRemove`，再由代码 merge 到 memory JSON
  - cache reload：解释 memory file 是跨请求状态
- 测试：
  - `tests/test_unit7_memory_lifecycle.py`
  - 断言 tool call AIMessage 不进入 memory input
  - 断言 upload-only turn 被丢弃
  - 断言 `/mnt/user-data/uploads/` 不出现在保存后的 memory JSON

### Phase 2: Subagent and MCP

实现 `Unit 8` 和 `Unit 9`，补齐“多代理委派”和“外部工具延迟暴露”两条 super-agent 能力。

#### Unit 8 Deliverables

- 新目录：`unit-8-subagent-delegation/`
- 文件：
  - `main.py`
  - `subagent_delegation_demo.py`
  - `README.md`
  - `_demo_data/thread-subagent/user-data/workspace/`
- Demo 行为：
  - parent runtime 带入 `thread_id`、sandbox state、thread data、parent model、trace id
  - `task` 工具创建 background task
  - subagent 使用过滤后的 tool list，明确不包含 `task`，防止递归委派
  - background executor 产生 `task_started`、`task_running`、`task_completed` 事件
  - 完成后清理 background state
- 关键 `LEARN:` 注释位置：
  - parent context extraction：解释子代理共享 thread/sandbox，但不共享全部对话上下文
  - tool filtering：解释不允许 subagent 再调 subagent
  - background task store：解释执行和轮询分离
  - cleanup：解释后台结果不清理会造成长期进程内存泄露
- 测试：
  - `tests/test_unit8_subagent_delegation.py`
  - 断言 subagent tools 不包含 `task`
  - 断言事件顺序是 started -> running -> completed
  - 断言 terminal task 被 cleanup

#### Unit 9 Deliverables

- 新目录：`unit-9-mcp-deferred-tools/`
- 文件：
  - `main.py`
  - `mcp_deferred_tools_demo.py`
  - `README.md`
  - `_demo_data/extensions_config.json`
- Demo 行为：
  - Gateway-style update 写入 MCP server config
  - cache 记录 config mtime
  - config 文件变化后 cache 判定 stale
  - fake MCP loader 返回一批工具
  - tool registry 在 `tool_search_enabled=True` 时只暴露 `tool_search`，把 MCP 工具放入 deferred registry
  - agent 搜索 `"github"` 后才拿到 `github.search_issues`
- 关键 `LEARN:` 注释位置：
  - config write：解释 Gateway 进程和 LangGraph 进程通过文件状态同步
  - mtime check：解释不依赖内存单例跨进程通信
  - deferred registry：解释工具 schema 延迟加载减少上下文压力
  - tool search：解释模型先发现工具，再决定是否加载细节
- 测试：
  - `tests/test_unit9_mcp_deferred_tools.py`
  - 断言 config mtime 变化会让 cache stale
  - 断言 deferred mode 下 visible tools 包含 `tool_search` 但不直接包含所有 MCP tools
  - 断言 search 后返回匹配工具

### Phase 3: Artifact Safety and Integration

实现 `Unit 10`，然后回头更新总览、阅读路径、调试配置和结构验证。

#### Unit 10 Deliverables

- 新目录：`unit-10-artifacts-archive-safety/`
- 文件：
  - `main.py`
  - `artifacts_archive_safety_demo.py`
  - `README.md`
  - `_demo_data/threads/thread-artifact/user-data/outputs/report.html`
  - `_demo_data/threads/thread-artifact/user-data/outputs/notes.txt`
  - demo 内动态生成 safe/unsafe `.skill` archives
- Demo 行为：
  - virtual artifact path 映射到 thread-scoped host path
  - text/html 返回 HTML-style response，text/plain 返回 plain text，binary 返回 bytes metadata
  - `.skill/SKILL.md` 路径从 ZIP 内读取文件
  - 拒绝 `../evil.txt`、绝对路径、symlink entry
  - 拒绝超过 max total uncompressed size 的 archive
- 关键 `LEARN:` 注释位置：
  - virtual path resolver：解释 artifact endpoint 不接受任意 host path
  - MIME decision：解释 response 类型由文件内容和 mimetype 决定
  - ZIP member validation：解释 ZIP 内路径也可能攻击 host filesystem
  - size accounting：解释 zip bomb 防护用 uncompressed size
- 测试：
  - `tests/test_unit10_artifacts_archive_safety.py`
  - 断言 path traversal 被拒绝
  - 断言 `.skill/SKILL.md` 能被读取
  - 断言 unsafe ZIP member 被拒绝

## Required Integration Changes

### Unit 1 Update

`unit-1-overall-backend-flow/main.py` 应在原有主链路之外增加一个紧凑的 `secondary_flows` 输出：

```python
"secondary_flows": {
    "skills_prompt": build_skills_prompt_section(...),
    "memory_context": build_memory_context(...),
    "subagent_events": run_subagent_demo(...),
    "mcp_deferred_tools": run_mcp_deferred_tools_demo(...),
    "artifact_safety": resolve_demo_artifact(...),
}
```

要求：

- Unit 1 必须真实 import 新单元的 public API。
- Unit 1 只展示每条 secondary flow 的摘要，不复制各单元完整 demo。
- Unit 1 仍然默认离线可跑。
- 如果输出太长，只保留 count、names、event types、selected paths。

### Unit 4 Update

`unit-4-lead-agent-factory/lead_agent_factory_demo.py` 目前的 `prompt_sections` 是静态名称。扩展后应改成：

- skills section 来自 Unit 6 的 `build_skills_prompt_section()` 的摘要
- memory section 来自 Unit 7 的 `build_memory_context()` 的摘要
- subagent section 保留在 Unit 4 中只展示是否启用，完整行为交给 Unit 8

### Unit 5 Update

`ToolRegistry` 可以保留当前教学版，但 README 应明确：

- Unit 5 只解释 MCP tools 被“算入工具来源”
- Unit 9 才解释 MCP config、cache、deferred registry、tool_search 的完整流程

### Root README Update

更新 `cases/speedrun-deer-flow/README.md`：

- `What This Speedrun Covers` 增加 skills、memory、subagents、MCP、artifacts safety
- `Learning Path` 表从 5 行扩展到 10 行
- `Quick Start` 增加运行新增单元命令
- `Architecture At A Glance` 增加二级主线说明

### SIMPLIFICATIONS Update

更新 `SIMPLIFICATIONS.md`：

- 为 Unit 6-10 各加一节
- 明确哪些地方用 fake/scripted 实现替代真实依赖：
  - Unit 7 不调用真实 LLM 更新 memory
  - Unit 8 不创建真实 LangChain agent，只模拟 executor 状态机
  - Unit 9 不连接真实 MCP server，使用 fake MCP loader
  - Unit 10 不启动 FastAPI，只模拟 resolver 和 response decision

### ORIGINAL-READING-PATH Update

更新 `ORIGINAL-READING-PATH.md`：

- `90-Minute Route` 可以保留主链路
- 新增 `180-Minute Route`，包含 Unit 6-10 对应源码
- 每个新增单元补 `Unit Crosswalk`
- 加一节 `When To Read Frontend`，说明 artifacts、skills、memory 的 UI 入口在 frontend 中，但本 speedrun 不拆前端

### VS Code Debug Config

更新 `.vscode/launch.json`，新增：

- `Unit 6: Skills Prompt System`
- `Unit 7: Memory Lifecycle`
- `Unit 8: Subagent Delegation`
- `Unit 9: MCP Deferred Tools`
- `Unit 10: Artifacts and Archive Safety`

## Coverage Map

| Source area | 当前状态 | 扩展后状态 | 处理方式 |
|-------------|----------|------------|----------|
| `app/gateway/routers/models.py` | Covered | Covered | Unit 2 |
| `app/gateway/routers/uploads.py` | Covered | Covered | Unit 2 |
| `app/gateway/routers/skills.py` | Woven | Covered | Unit 6, Unit 10 |
| `app/gateway/routers/mcp.py` | Excluded | Covered | Unit 9 |
| `app/gateway/routers/artifacts.py` | Woven | Covered | Unit 10 |
| `agents/lead_agent/agent.py` | Covered | Covered | Unit 4, Unit 8 |
| `agents/lead_agent/prompt.py` | Woven | Covered | Unit 6, Unit 7 |
| `agents/middlewares/memory_middleware.py` | Woven | Covered | Unit 7 |
| `agents/memory/*` | Excluded | Covered | Unit 7 |
| `agents/middlewares/subagent_limit_middleware.py` | Woven | Covered | Unit 8 |
| `tools/builtins/task_tool.py` | Woven | Covered | Unit 8 |
| `subagents/*` | Excluded | Covered | Unit 8 |
| `mcp/*` | Woven | Covered | Unit 9 |
| `tools/builtins/tool_search.py` | Woven | Covered | Unit 9 |
| `skills/*` | Woven | Covered | Unit 6 |
| `sandbox/*` | Covered | Covered | Unit 3, Unit 5 |
| `community/aio_sandbox/*` | Woven | Woven | Keep out of unit scope; mention in SIMPLIFICATIONS |
| `app/channels/*` | Excluded | Excluded | Keep excluded unless future plan covers IM channels |
| `frontend/*` | Excluded | Excluded | Keep excluded; only reference UI entry points |

## Test Plan

Run from `cases/speedrun-deer-flow`:

```bash
python unit-1-overall-backend-flow/main.py
python unit-2-gateway-config/main.py
python unit-3-thread-runtime/main.py
python unit-4-lead-agent-factory/main.py
python unit-5-tools-sandbox/main.py
python unit-6-skills-prompt-system/main.py
python unit-7-memory-lifecycle/main.py
python unit-8-subagent-delegation/main.py
python unit-9-mcp-deferred-tools/main.py
python unit-10-artifacts-archive-safety/main.py
pytest
```

After all units are implemented, run the structural checker from repo root:

```bash
python .codex/skills/code-speedrun/scripts/verify_speedrun.py cases/speedrun-deer-flow
```

Manual acceptance checklist:

- Every documented command runs from `cases/speedrun-deer-flow`.
- Unit 1 imports and calls public APIs from Units 2-10.
- Each new unit has a clear `README.md`, exercises, debug guide, and expected output.
- Each new unit source file contains high-value `LEARN:` comments at non-obvious boundaries.
- `.vscode/launch.json` points at real entry points for Units 1-10.
- `SIMPLIFICATIONS.md` lists every fake/scripted dependency.
- Root README explains DeerFlow first, then the expanded speedrun scope.
- Tests cover at least one meaningful state transition per new unit.

## Suggested Work Order

1. Implement Unit 6.
2. Add `tests/test_unit6_skills_prompt.py`.
3. Implement Unit 7.
4. Add `tests/test_unit7_memory_lifecycle.py`.
5. Update Unit 4 to consume Unit 6/7 summaries.
6. Implement Unit 8.
7. Add `tests/test_unit8_subagent_delegation.py`.
8. Implement Unit 9.
9. Add `tests/test_unit9_mcp_deferred_tools.py`.
10. Implement Unit 10.
11. Add `tests/test_unit10_artifacts_archive_safety.py`.
12. Update Unit 1 to include `secondary_flows`.
13. Update root README, SIMPLIFICATIONS, ORIGINAL-READING-PATH, launch.json.
14. Run all unit commands and pytest.
15. Run speedrun verifier and fix structural issues.

## Risk Notes

- Do not let Unit 8 become a full LangChain reimplementation. The teaching target is subagent lifecycle, not model reasoning.
- Do not require live MCP servers in Unit 9. A deterministic fake loader is enough to teach config/cache/deferred behavior.
- Do not put all prompt text into Unit 6/7 output. Show summaries and short excerpts so the demo remains readable.
- Do not add frontend units in this expansion. Frontend can be a separate speedrun later.
- Keep generated `_demo_data/` deterministic by resetting it at the start of each demo.

## Definition of Done

This expansion is done when a learner can run `Unit 1`, see the complete backend shape, then drill into Units 2-10 and understand:

- how HTTP config/upload boundaries feed the runtime;
- how a thread owns its file-system slice;
- how the lead agent is assembled;
- how LangGraph tool calls cross into a sandbox;
- how skills enter prompts without loading all skill content up front;
- how memory keeps durable user context while dropping temporary upload paths;
- how subagents run with inherited runtime state but isolated execution;
- how MCP tools are cached and deferred behind tool search;
- how artifact and skill archive serving avoids unsafe file access.
