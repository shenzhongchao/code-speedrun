# Unit 1: Overall Backend Flow

> **Motto**: *One request, ten moving parts*

## In Plain Language

把 DeerFlow backend 想成一条小流水线：gateway 先接住请求，thread runtime 给这次对话分配自己的文件夹和 `/mnt/user-data/...` 虚拟路径，lead agent 再决定该带哪些中间件和工具，最后 sandbox 真正去动文件和命令。这个单元还会压缩展示 skills、memory、subagent、MCP deferred tools 和 artifact safety 这五条 secondary flows。

## Background Knowledge

- **线程像一个独立背包**：一次对话不是“全局共享一堆文件”，而是每个 thread 都有自己的 `workspace / uploads / outputs`。技术上这就是把 `thread_id` 映射到固定目录。
- **virtual path 像统一路标**：gateway、agent、Docker sandbox 都说 `/mnt/user-data/...`，只有 runtime 知道它对应哪个 host 目录。
- **middleware 像安检闸机**：每个请求进站时都会按顺序过一组关卡。技术上就是在 agent 真正调用模型前，先补齐 thread data、sandbox、memory、title 这些状态。
- **tool 像可插拔的手**：模型自己不会读文件或跑命令，它只能挑一个工具去做。技术上是把配置工具、builtin 工具和 MCP 工具合并成一个列表。

## Key Terminology

- **Gateway API**：前端或外部调用最容易接触到的 HTTP 边界。它负责“列模型”“传文件”这种普通接口，不负责 agent 推理本身。
- **Thread Runtime**：一次对话在运行时拿到的最小上下文，至少包括三个路径和一个 `sandbox_id`。
- **Lead Agent**：DeerFlow 的主 agent 工厂。它把运行时参数翻译成模型、中间件、prompt 和工具列表。
- **Sandbox**：真正执行命令和文件读写的边界层。这个单元用 fake Docker runner 保持离线可跑，但路径契约和 Unit 5 的 Docker sandbox 一致。

## What This Unit Does

这个单元把 `Unit 2` 到 `Unit 10` 真实 import 进来，然后跑一条最短但完整的主链路：

1. 用 `GatewayAPI` 列模型并上传两个文件。
2. 用 `ThreadRuntimeManager` 为 `thread-007` 分配路径和 `sandbox_id`。
3. 用 `ToolRegistry` 解析出当前模型可见的工具。
4. 用 `LeadAgentFactory` 造一个 lead agent。
5. 让 agent 通过 sandbox 写出 `/mnt/user-data/workspace/brief.md`，再读回来并列目录。
6. 用 LangGraph 教学 agent 写 `/mnt/user-data/outputs/langgraph-result.txt`，并证明 host 侧输出文件存在。
7. 返回一个 `secondary_flows` 摘要，展示 skills prompt、memory context、subagent events、MCP deferred tools 和 artifact safety。

如果你先把这里吃透，再看原仓库，就不会被多进程部署、LangGraph server 和前端细节淹没。

## Key Code Walkthrough

- `main.py:22-45`：创建 demo config，并通过 `GatewayAPI` 上传两个文件。这对应原仓库里 `backend/app/gateway/routers/models.py` 和 `backend/app/gateway/routers/uploads.py` 的两个关键职责。
- `main.py:57-61`：把 `thread-007` 变成独立的 host `user-data` 目录和 `/mnt/user-data/...` 虚拟路径，再挂上 `sandbox_id`。
- `main.py:63-72`：按运行时条件解析工具列表。这里故意把 `subagent_enabled`、`model_supports_vision`、`tool_search_enabled` 都打开，让你看到工具为什么会变多。
- `main.py:85-102`：fake Docker runner 保留真实 Docker mount 形状，但不要求本机安装 Docker。
- `main.py:106-127`：先跑 lead agent 的文件工具流，再跑 LangGraph agent 的 virtual path 输出流。
- `main.py:148-154`：`virtual_path_flow` 把 host mount、virtual output path、host output path 放在一起，证明三者讲的是同一份文件。

相关单元：

- 不懂 gateway 为什么单独存在：先看 `../unit-2-gateway-config/README.md`
- 不懂线程路径怎么来的：先看 `../unit-3-thread-runtime/README.md`
- 不懂 agent 为什么不是“直接 new 一个模型”：先看 `../unit-4-lead-agent-factory/README.md`
- 不懂工具和 sandbox 为什么是边界层：先看 `../unit-5-tools-sandbox/README.md`

## How to Run

```bash
cd cases/speedrun-deer-flow
python unit-1-overall-backend-flow/main.py
```

## Expected Output

你应该看到一个 JSON，里面至少有这几块：

- `health`
- `models_seen_by_gateway`
- `thread_runtime`
- `uploaded_files`
- `lead_agent.middlewares`
- `lead_agent.tool_trace`
- `virtual_path_flow`
- `secondary_flows`

最关键的成功信号是 `lead_agent.tool_trace` 里出现 `write_file`、`read_file`、`bash` 三步，而且 `bash` 的输出里能看到 `brief.md`。
另一个成功信号是 `virtual_path_flow.output_virtual_path` 是 `/mnt/user-data/outputs/langgraph-result.txt`，并且 `host_output_exists` 是 `true`。
`secondary_flows` 应该包含 `skills_prompt`、`memory_context`、`subagent_events`、`mcp_deferred_tools` 和 `artifact_safety`。

## Exercises

### Explain It Back

用你自己的话解释：为什么 DeerFlow 需要先做 `thread runtime`，再做 `lead agent`，而不是让 agent 自己临时拼路径和工具？

再解释一次：为什么上传文件给 agent 的是 `/mnt/user-data/uploads/...`，而不是 host 上的绝对路径？

### Modify It

- 把 `model_name="gpt-5-responses"` 改成 `gemini-2.5-flash`，再观察 `lead_agent.available_tools` 和 `lead_agent.middlewares` 的变化。
- 把 `subagent_enabled=True` 改成 `False`，确认 `task` 和 `SubagentLimitMiddleware` 都会消失。

## Debug Guide

### Observation Points

File: `main.py:29`
What to observe: gateway 返回的模型列表长什么样，哪些字段会暴露给前端
Breakpoint or log: 在这一行后面加 `breakpoint()`，查看 `models`

File: `main.py:47`
What to observe: thread id 是怎样变成 host 路径和 virtual 路径的
Breakpoint or log: 查看 `thread_runtime.user_data_path` 和 `thread_runtime.virtual_outputs_path`

File: `main.py:63`
What to observe: 运行时 flag 如何改变工具列表
Breakpoint or log: 查看 `available_tools`

File: `main.py:106`
What to observe: lead agent 真正执行时写了什么文件、返回了什么 tool trace
Breakpoint or log: 逐步单步进入 `agent.run(...)`

File: `main.py:113`
What to observe: LangGraph agent 如何用 `/mnt/user-data/outputs/...` 写出 host 文件
Breakpoint or log: 查看 `graph_outcome` 和 `output_host_path`

### Common Failures

Symptom: `ModuleNotFoundError`
Cause: 你不是从 `cases/speedrun-deer-flow` 根目录启动脚本
Fix: 先 `cd cases/speedrun-deer-flow` 再运行
Verify: `python unit-1-overall-backend-flow/main.py` 能打印 JSON

Symptom: `brief.md` 没有出现在输出里
Cause: `agent.run(...)` 没有真正执行到 sandbox 写文件
Fix: 在 `main.py:106` 断点，确认 `sandbox` 是 `DockerSandbox`
Verify: `lead_agent.tool_trace[0].tool` 是 `write_file`

Symptom: `host_output_exists` 是 `false`
Cause: LangGraph agent 没有通过 `/mnt/user-data/outputs/langgraph-result.txt` 写入输出文件
Fix: 检查 `main.py:113-130` 的 scripted tool call 和 `output_virtual_path`
Verify: `virtual_path_flow.host_output_exists` 是 `true`

Symptom: 上传列表是空的
Cause: 你改坏了 `GatewayAPI.upload_files(...)` 的 safe filename 逻辑
Fix: 回看 `Unit 2` 里的 `gateway_config_demo.py:112-144`
Verify: `uploaded_files` 至少有两条记录

### State Inspection

- 用 `python -m pdb unit-1-overall-backend-flow/main.py` 逐步执行
- 在 `main.py:60` 后检查 `thread_runtime.__dict__`
- 在 `main.py:106` 后检查 `outcome["tool_trace"]`
- 在 `main.py:129` 后检查 `output_host_path`
- 运行结束后直接看 `unit-1-overall-backend-flow/_demo_data/threads/thread-007/user-data/workspace/brief.md`
  和 `unit-1-overall-backend-flow/_demo_data/threads/thread-007/user-data/outputs/langgraph-result.txt`

### Isolation Testing

- 只想验证 gateway：把 `run_demo()` 暂时截断到 `uploads = ...` 然后 `return uploads`
- 只想验证 agent：保留 `thread_runtime`、`available_tools` 和 `agent.run(...)`，跳过 `models`
- 想强行观察目录副作用：删除 `_demo_data/` 后重跑一遍，看目录如何重新生成
