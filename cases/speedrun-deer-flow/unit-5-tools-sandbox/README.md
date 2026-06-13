# Unit 5: LangGraph Tools and Docker Sandbox

> **Motto**: *The graph thinks, the sandbox touches files*

## In Plain Language

Agent 不是一个大函数。更准确地说，它是一圈循环：模型先决定要不要调用工具，工具从 runtime 里拿到 sandbox 和 thread data，再把真实世界的结果带回来，模型再根据结果继续回答。DeerFlow 用 LangGraph 管这圈循环，用 sandbox 管“碰文件、跑命令”这件危险的事。

这个单元把 DeerFlow 的真实形状压缩成一个教学版：LangGraph 里有 `model` 和 `tools` 两个节点，模型可以请求 `bash/read_file/write_file`，工具节点先经过 teaching runtime/provider，再交给 sandbox。Docker sandbox 会把 host 的 `user-data/` 挂到容器里的 `/mnt/user-data`；local sandbox 则在 tool 层把 `/mnt/user-data/...` 解析成当前 thread 的 host path。默认运行用可预测的 scripted model；`--live` 模式会接 OpenAI-compatible LLM，并用 Docker 跑命令。

## Background Knowledge

- **LangGraph 是状态机**：每个节点读写 `messages`，边决定下一步去模型还是工具。
- **Tool call 是一张工单**：模型不会直接执行命令，只返回工具名和参数。
- **Docker sandbox 是执行边界**：教学版把 `bash` 转成 `docker run --rm -v <host-user-data>:/mnt/user-data -w /mnt/user-data/workspace ... /bin/sh -lc <command>`。
- **virtual path 是模型的唯一文件语言**：`read_file/write_file` 只接受 `/mnt/user-data/...`，不接受 host 绝对路径。
- **Tool runtime 是中转站**：工具不是直接 new sandbox，而是从 runtime state 取 `sandbox_id`、`thread_data`，必要时由 provider acquire。
- **OpenAI-compatible 接口是配置形状**：同样用 `ChatOpenAI`，但通过 `base_url/api_key/model` 指向不同服务。

## Key Terminology

- **StateGraph**：LangGraph 的图构建器，这里定义 `model -> tools -> model` 的循环。
- **AIMessage.tool_calls**：模型请求工具调用的地方。
- **ToolMessage**：工具执行后的结果，会被放回消息列表给模型看。
- **DockerSandbox**：教学版 sandbox，把 host `user-data/` 挂到容器 `/mnt/user-data` 后执行工具命令。
- **OpenAICompatibleConfig**：最小模型配置，映射到 `ChatOpenAI(model, base_url, api_key, temperature)`。

## What This Unit Does

这个单元做三件事：

1. 继续展示 DeerFlow 式工具列表如何从 config、builtin、subagent、vision、MCP 拼出来
2. 用 LangGraph 实现一个最小 agent loop：模型节点、工具节点、条件边
3. 让工具调用走 runtime/provider/path validation，而不是直接调 sandbox
4. 提供 live 模式：OpenAI-compatible LLM 决定工具调用，Docker sandbox 通过 `/mnt/user-data` 执行任务

这里的 MCP 只说明“外部工具会被算进工具来源”。MCP server config、mtime cache、deferred registry 和 `tool_search` 的完整流程在 `Unit 9` 单独展开。

如果你想把真实环境里的上传、runtime、sandbox、tool call 和 artifact 返回完整串起来，先读 [REAL-SANDBOX-FLOW.md](/root/key_projects/learn-codebase/cases/speedrun-deer-flow/unit-5-tools-sandbox/REAL-SANDBOX-FLOW.md)。

对应真实源码：

- `src/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py`
- `src/deer-flow/backend/packages/harness/deerflow/models/factory.py`
- `src/deer-flow/backend/packages/harness/deerflow/tools/tools.py`
- `src/deer-flow/backend/packages/harness/deerflow/sandbox/`

## Key Code Walkthrough

- `tools_sandbox_demo.py:30`：`OpenAICompatibleConfig` 展示真实 DeerFlow model factory 的关键配置形状。
- `tools_sandbox_demo.py:147`：`DockerSandbox.execute_command()` 把普通 shell 命令包成挂载 `/mnt/user-data` 的 `docker run`。
- `tools_sandbox_demo.py:260`：`build_tool_runtime()` 构造 thread data、sandbox state 和 provider，模拟真实 `ToolRuntime`。
- `tools_sandbox_demo.py:228`：`ScriptedToolCallingModel` 是离线教学模型，固定先发工具调用再给最终回答。
- `tools_sandbox_demo.py:267`：`run_langgraph_sandbox_demo()` 构建 `model` 和 `tools` 两个 LangGraph 节点。
- `tools_sandbox_demo.py:283`：`call_tools()` 把模型的 tool call 派发到 runtime tool 层，再生成 `ToolMessage`。
- `tools_sandbox_demo.py:307`：条件边决定继续去工具节点，还是结束。
- `tools_sandbox_demo.py:430`：`read_file_runtime_tool()` 展示 local 模式如何校验并解析 `/mnt/user-data`。
- `tools_sandbox_demo.py:455`：`write_file_runtime_tool()` 展示写文件前的边界检查。

## How to Run

离线教学模式：

```bash
cd cases/speedrun-deer-flow
python unit-5-tools-sandbox/main.py
```

真实 LLM + Docker sandbox 模式：

```bash
cd cases/speedrun-deer-flow
export OPENAI_API_KEY="..."
export OPENAI_BASE_URL="https://api.openai.com/v1"
export OPENAI_MODEL="gpt-4o-mini"
python unit-5-tools-sandbox/main.py --live
```

如果你用的是其它 OpenAI-compatible 服务，只改 `OPENAI_BASE_URL` 和 `OPENAI_MODEL`。

## Expected Output

离线模式里你应该看到：

- `mode` 是 `offline-scripted-langgraph`
- `tools` 里包含 `bash`、`read_file`、`write_file`、`tool_search`
- `agent.tool_trace[0].tool` 是 `bash`
- `agent.final_message` 是 `LANGGRAPH_SANDBOX_OK`

live 模式里你应该看到：

- `mode` 是 `live-openai-compatible-docker`
- `tool_trace` 至少有一次 `bash`
- Docker 命令会把 `_demo_data/docker-thread/user-data` 挂到 `/mnt/user-data`
- 工具输出或最终回答里出现 `LANGGRAPH_SANDBOX_OK`

## Exercises

### Explain It Back

为什么模型节点不能直接调用 `subprocess.run()`，而要先产出 tool call，再让工具节点进入 sandbox 执行？

为什么工具参数里应该使用 `/mnt/user-data/outputs/result.txt`，而不是 host 上的绝对路径？

### Modify It

- 把 scripted model 的 `tool_name` 改成 `write_file`，让工具节点写 `/mnt/user-data/outputs/result.txt`。
- 把 Docker image 改成 `alpine:3.20`，观察命令兼容性变化。
- 在 `next_step()` 里打印最后一条消息，观察图什么时候继续、什么时候结束。

## Debug Guide

### Observation Points

File: `tools_sandbox_demo.py:147`
What to observe: shell 命令如何被包成 Docker CLI 参数，以及 host user-data 如何挂到 `/mnt/user-data`
Breakpoint or log: 查看 `docker_command`

File: `tools_sandbox_demo.py:176`
What to observe: virtual path 如何映射到 host path
Breakpoint or log: 调用 `sandbox.virtual_to_host("/mnt/user-data/outputs/a.txt")`

File: `tools_sandbox_demo.py:267`
What to observe: LangGraph 节点如何共享 `messages`
Breakpoint or log: 查看 `state["messages"]`

File: `tools_sandbox_demo.py:283`
What to observe: `AIMessage.tool_calls` 如何变成 sandbox 执行
Breakpoint or log: 查看 `tool_call`

File: `tools_sandbox_demo.py:307`
What to observe: 条件边如何决定是否进入工具节点
Breakpoint or log: 查看 `last_message.tool_calls`

### Common Failures

Symptom: `ModuleNotFoundError: langgraph`
Cause: 没安装 speedrun 依赖
Fix: 在 `cases/speedrun-deer-flow` 运行 `python -m pip install -r requirements.txt`
Verify: `python -c "import langgraph"`

Symptom: live 模式提示缺少环境变量
Cause: 没设置 `OPENAI_API_KEY`、`OPENAI_BASE_URL` 或 `OPENAI_MODEL`
Fix: 设置三个变量后重跑
Verify: 错误消失，并开始调用模型

Symptom: live 模式提示找不到 `docker`
Cause: 当前机器没有 Docker CLI 或 Docker Desktop WSL integration
Fix: 安装并启用 Docker 后重跑
Verify: `docker --version` 有输出

Symptom: Docker 拉镜像失败
Cause: 网络或镜像源问题
Fix: 先手动 `docker pull python:3.12-slim`
Verify: `docker run --rm python:3.12-slim python --version`

Symptom: `read_file` 报 `Sandbox path must start with /mnt/user-data`
Cause: 工具参数传了 `/workspace/...` 或 host 绝对路径
Fix: 改成 `/mnt/user-data/workspace/...`、`/mnt/user-data/uploads/...` 或 `/mnt/user-data/outputs/...`
Verify: `sandbox.virtual_to_host(...)` 能返回 host `user-data` 下的路径

### State Inspection

- 用 `python -m pdb unit-5-tools-sandbox/main.py`
- 在 `tools_sandbox_demo.py:280` 后检查模型返回的 `AIMessage`
- 在 `tools_sandbox_demo.py:296` 后检查 `ToolMessage`
- 在 `tools_sandbox_demo.py:430` 后检查 `requested_path` 和解析后的 host path
- live 模式结束后看 `unit-5-tools-sandbox/_demo_data/docker-thread/user-data/`

### Isolation Testing

- 只测 Docker 命令拼装：给 `DockerSandbox` 注入 fake `runner`
- 只测路径映射：调用 `DockerSandbox(...).write_file("/mnt/user-data/outputs/a.txt", "...")`
- 只测 LangGraph 循环：使用 `ScriptedToolCallingModel`
- 只测 OpenAI-compatible 配置：调用 `OpenAICompatibleConfig.to_chat_openai_kwargs()`
