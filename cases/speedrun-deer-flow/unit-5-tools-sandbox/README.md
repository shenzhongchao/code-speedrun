# Unit 5: Tools and Sandbox

> **Motto**: *Tools need safe hands*

## In Plain Language

模型会“想”，但不会自己碰文件和命令。真正伸手的是工具，而工具真正落地时又要经过 sandbox。这个单元就是把“工具来自哪里”和“sandbox 实际做什么”拆开讲清楚。

## Background Knowledge

- **工具列表像工具箱**：工人每次上工不一定带同一套工具。技术上，配置、builtin、subagent、vision、MCP 都会影响最终工具箱。
- **sandbox 像手套**：不是直接让 agent 碰宿主机，而是通过一个受控接口执行命令和读写文件。技术上是 `execute_command`、`read_file`、`write_file` 这样的最小方法集。
- **MCP 像外接工具柜**：不是本地自带，但可以按需挂进来。教学版只保留“会并进工具列表”这个关键事实。

## Key Terminology

- **ToolRegistry**：决定当前 agent 看得到哪些工具的地方
- **Builtin tools**：DeerFlow 自带工具，比如 `present_file`、`ask_clarification`
- **MCP tools**：来自外部 MCP server 的工具
- **LocalSandbox**：本地文件系统版本的 sandbox

## What This Unit Does

这个单元做两件事：

1. 把配置工具、builtin、subagent、vision、MCP 工具合并成最终列表
2. 用本地 sandbox 真实执行一次写文件、读文件、跑命令

它对应原仓库 `tools/tools.py` 和 `sandbox/local/local_sandbox.py` 的核心教学形状。

## Key Code Walkthrough

- `tools_sandbox_demo.py:17-57`：`LocalSandbox` 保留了 DeerFlow 本地 sandbox 最核心的三个动作：选 shell、执行命令、读写文件。
- `tools_sandbox_demo.py:67-85`：`resolve_tools()` 展示工具为什么会变多。不是简单“把所有工具都加进去”，而是根据 vision、subagent、MCP 条件动态拼接。
- `tools_sandbox_demo.py:92-93`：`build_tool_registry()` 让别的单元可以把配置工具列表直接喂进来。
- `tools_sandbox_demo.py:96-115`：`run_demo()` 先写入 `hello.txt`，再读回来，最后用 `ls` 证明 sandbox 真的对文件系统产生了作用。

## How to Run

```bash
cd src/speedrun-deer-flow
python unit-5-tools-sandbox/main.py
```

## Expected Output

你应该看到：

- `tools` 里既有 `config`，也有 `builtin` 和 `mcp`
- `sandbox_read` 读回刚写进去的文本
- `sandbox_command` 输出 `hello.txt`

## Exercises

### Explain It Back

为什么 DeerFlow 不把 `bash`、`read_file`、`write_file` 直接做成模型内建能力，而是通过工具和 sandbox 暴露出来？

### Modify It

- 把 `model_supports_vision` 改成 `False`，确认 `view_image` 会消失。
- 把 `include_mcp` 改成 `False`，确认 MCP 工具和 `tool_search` 一起消失。

## Debug Guide

### Observation Points

File: `tools_sandbox_demo.py:23`
What to observe: sandbox 如何挑选一个可用 shell
Breakpoint or log: 查看 `_get_shell()` 返回值

File: `tools_sandbox_demo.py:33`
What to observe: 命令执行后的 stdout、stderr、exit code 如何被整理
Breakpoint or log: 查看 `result.returncode`

File: `tools_sandbox_demo.py:67`
What to observe: 不同 flag 如何改变工具列表
Breakpoint or log: 查看 `resolved`

File: `tools_sandbox_demo.py:96`
What to observe: 文件副作用与命令副作用是否都发生了
Breakpoint or log: 看 `note_path` 和 `sandbox_command`

### Common Failures

Symptom: `view_image` 没出现
Cause: `model_supports_vision=False`
Fix: 改成 `True`
Verify: `tools` 列表里出现 `view_image`

Symptom: `tool_search` 没出现
Cause: 你关闭了 `include_mcp` 或 `tool_search_enabled`
Fix: 同时打开这两个参数
Verify: 输出里出现 `tool_search`

Symptom: `sandbox_command` 报错
Cause: shell 不可用或命令路径写错
Fix: 先检查 `_get_shell()`，再检查 `ls` 命令里的路径
Verify: 输出变成 `hello.txt`

### State Inspection

- 用 `python -m pdb unit-5-tools-sandbox/main.py`
- 在 `tools_sandbox_demo.py:75` 后检查 `resolved`
- 在 `tools_sandbox_demo.py:100` 后查看 `note_path.exists()`
- 运行结束后直接看 `unit-5-tools-sandbox/_demo_data/workspace/hello.txt`

### Isolation Testing

- 只测工具列表：单独调用 `registry.resolve_tools(...)`
- 只测文件读写：只保留 `LocalSandbox.write_file()` 和 `read_file()`
- 只测命令执行：改成 `sandbox.execute_command("pwd")`
