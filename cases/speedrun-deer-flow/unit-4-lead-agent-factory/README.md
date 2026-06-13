# Unit 4: Lead Agent Factory

> **Motto**: *Assemble, do not hardcode*

## In Plain Language

DeerFlow 的 lead agent 不是“选一个模型然后直接开跑”。它更像装配工位：先看运行时参数，再决定模型、中间件、prompt section 和工具列表。这个单元教的就是这套装配逻辑。

## Background Knowledge

- **factory 像配菜台**：同一道菜根据客人要求可以少辣、多辣、加配菜。技术上，factory 根据 runtime flags 决定 agent 的最终形状。
- **middleware 像出厂前检查清单**：不同请求需要不同检查项。技术上，plan mode、vision、subagent 开关会改变 middleware 列表。
- **prompt section 像说明书夹页**：系统 prompt 不是一整块石头，而是可以拼接的多个片段，比如基础规则、skills、memory。

## Key Terminology

- **RuntimeFlags**：一次 agent 创建时带入的运行时参数
- **LeadAgentFactory**：把 flags 翻译成 agent blueprint 的工厂
- **Blueprint**：还没真正执行前，agent 的配置快照
- **Thinking mode**：模型是否允许更强推理流程的开关

## What This Unit Does

这个单元保留了 `make_lead_agent()` 里最值得学的四件事：

1. 解析要用哪个模型
2. 根据能力和 flag 选择 middleware
3. 记录 prompt 会由哪些 section 组成
4. 把可用工具和运行时状态交给 agent 执行

你可以把它当成 DeerFlow agent 装配流程的教学版 X 光图。
扩展后，skills 和 memory section 不再是纯占位名称，而是读取 Unit 6/7 的 public API 生成摘要；subagent section 仍只展示启用状态，完整后台执行交给 Unit 8。

## Key Code Walkthrough

- `lead_agent_factory_demo.py:7-13`：`RuntimeFlags` 把最关键的运行时开关收拢到一个 dataclass 里，模拟原仓库 `configurable` 里的那几个核心参数。
- `lead_agent_factory_demo.py:20-60`：`DemoLeadAgent.run()` 不做空讲解，而是真实写出 `brief.md`、再读回内容、最后列目录。这让 agent 看起来像真的在“做事”。
- `lead_agent_factory_demo.py:73-88`：`create()` 是装配核心。它先 resolve model，再算 thinking 和 reasoning，再收集中间件、prompt section、工具列表。
- `lead_agent_factory_demo.py:132-153`：prompt section 摘要来自 Unit 6 的 skills prompt 和 Unit 7 的 memory context，避免 Unit 4 复制完整 secondary flow。
- `lead_agent_factory_demo.py:99-106`：模型解析逻辑故意保留“请求模型不存在时回退默认模型”的行为，这和原仓库的 `_resolve_model_name()` 一致。
- `lead_agent_factory_demo.py:108-130`：middleware 的增减完全由 flags 和模型能力驱动，这就是为什么 DeerFlow 没把中间件写死成一个常量列表。

## How to Run

```bash
cd cases/speedrun-deer-flow
python unit-4-lead-agent-factory/main.py
```

## Expected Output

你应该看到：

- `model_name` 是 `gpt-5-responses`
- `middlewares` 里包含 `TodoMiddleware`、`ViewImageMiddleware`、`SubagentLimitMiddleware`
- `tool_trace` 里出现 `write_file`、`read_file`、`bash`
- `prompt_sections` 里 `skills prompt` 有 enabled skill count，`subagent prompt` 反映当前 flag

## Exercises

### Explain It Back

为什么 `LeadAgentFactory` 要先算 middleware 和工具，再让 agent 执行？如果这些逻辑分散在运行途中，会带来什么问题？

### Modify It

- 把 `model_name` 改成不存在的值，看看 factory 会回退到哪个模型。
- 把 `is_plan_mode` 和 `subagent_enabled` 都改成 `False`，确认相关 middleware 消失。

## Debug Guide

### Observation Points

File: `lead_agent_factory_demo.py:28`
What to observe: agent 真正执行时拿到了哪些 runtime 路径
Breakpoint or log: 查看 `workspace_path`

File: `lead_agent_factory_demo.py:73`
What to observe: factory 装配 blueprint 时收集了哪些字段
Breakpoint or log: 查看 `blueprint`

File: `lead_agent_factory_demo.py:99`
What to observe: 请求模型不存在时如何回退
Breakpoint or log: 修改 `flags.model_name` 后单步进入 `_resolve_model()`

File: `lead_agent_factory_demo.py:108`
What to observe: middleware 列表如何随着 flags 变化
Breakpoint or log: 查看 `middlewares`

### Common Failures

Symptom: thinking 模式没生效
Cause: 选中的模型本身不支持 thinking
Fix: 检查 `lead_agent_factory_demo.py:75`
Verify: `thinking_enabled` 与模型能力一致

Symptom: `ViewImageMiddleware` 不出现
Cause: 当前模型 `supports_vision=False`
Fix: 改成 `gpt-5-responses` 或 `claude-sonnet-4.6`
Verify: 中间件列表里重新出现它

Symptom: `task` 工具没出现在输出里
Cause: `subagent_enabled=False`
Fix: 同时检查 `Unit 5` 的工具解析条件
Verify: `available_tools` 里重新出现 `task`

### State Inspection

- 用 `python -m pdb unit-4-lead-agent-factory/main.py`
- 在 `lead_agent_factory_demo.py:74` 后检查 `model`
- 在 `lead_agent_factory_demo.py:80` 后检查 `middlewares`
- 运行结束后查看 `unit-4-lead-agent-factory/_demo_data/workspace/brief.md`

### Isolation Testing

- 只测试解析逻辑：在交互式 Python 里调用 `LeadAgentFactory(...).explain_resolution(...)`
- 只测试执行逻辑：手工构造一个 `blueprint`，再直接 new `DemoLeadAgent`
- 想观察 prompt 拼装思想：改 `prompt_sections`，确认输出会反映它
