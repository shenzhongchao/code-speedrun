# Unit 8: Subagent Delegation

> **Motto**: *Delegate work, keep the parent context clean*

## In Plain Language

Subagent 的核心不是“再调用一个函数”，而是“父 agent 把一块会污染上下文的工作交给另一个 agent 做”。父 agent 仍然负责理解用户问题和写最终答案；子 agent 只拿到一张清楚的派工单、同一个 thread 的文件现场、同一个 sandbox 入口，然后把结果交回来。

这个单元把流程拆成一条可观察的数据线：父 agent 决定要不要委派，生成 `task(...)` 调用；`task` 工具从 runtime 里取 thread、sandbox、model、trace；executor 创建子 agent 的初始 state；后台任务产生进度事件；最后父 agent 用子 agent 的结果综合回答。

## Background Knowledge

- **父 agent 是总负责人**：它决定是否拆任务、拆给谁、最后怎样回答用户。
- **`task` 工具是派工单**：真实参数是 `description`、`prompt`、`subagent_type`，还有系统注入的 `tool_call_id`。
- **子 agent 有同一个现场**：它能访问同一个 `/mnt/user-data/workspace`、uploads、outputs 和 sandbox。
- **子 agent 没有整本聊天记录**：它的初始消息只有 delegated prompt，这样 verbose 探索不会挤占父 agent 上下文。
- **后台任务负责等待和汇报**：真实 DeerFlow 会后台执行、轮询状态、流式发 `task_started/task_running/task_completed`。
- **工具过滤防止失控**：子 agent 默认拿不到 `task`，避免 subagent 再开 subagent。

## Key Terminology

- **Parent decision**：父 agent 看到用户请求后决定是否调用 `task`
- **TaskCall**：一次 `task(description, prompt, subagent_type)` 调用的教学数据结构
- **Runtime snapshot**：从父 runtime 抽出来传给 executor 的 thread/sandbox/model/trace 信息
- **Subagent initial state**：子 agent 启动时看到的 state，包含单条 human prompt 和 thread/sandbox handle
- **TaskEvent**：后台执行期间发给前端的进度事件
- **Tool result**：`task` 工具最终返回给父 agent 的字符串

## What This Unit Does

这个单元保留了真实 subagent 链路里的七个关键动作：

1. 构造一个带 workspace 文件的 thread 现场
2. 父 agent 判断 workspace inspection 会产生噪音，于是生成 `task` 调用
3. `SubagentExecutor` 从父上下文构造 runtime snapshot
4. executor 给子 agent 过滤工具，移除 `task`
5. executor 构造子 agent 初始 state：只有 delegated prompt，没有父对话全文
6. 后台任务产生 started、running、completed 事件
7. 父 agent 拿到 tool result 后生成最终回答，并清理 completed task

学完这个单元，你应该能理解：subagent 的价值是隔离探索上下文，同时共享必要运行现场。

## Key Code Walkthrough

- `subagent_delegation_demo.py:11`：`ParentContext` 表示父 agent 已经拥有的 thread、sandbox、workspace、model、trace。
- `subagent_delegation_demo.py:34`：`TaskCall` 表示父 agent 实际发出的 `task(...)` 派工单。
- `subagent_delegation_demo.py:56`：`subagent_tools` 先应用 allowlist，再移除 disallowed tools，比如 `task`。
- `subagent_delegation_demo.py:67`：`build_runtime_snapshot()` 模拟真实 `task_tool` 从 `runtime.state` 和 `runtime.context` 抽信息。
- `subagent_delegation_demo.py:78`：`build_initial_state()` 展示子 agent 只收到一条 delegated prompt。
- `subagent_delegation_demo.py:103`：`poll_until_done()` 压缩表达后台执行、轮询和事件流。
- `subagent_delegation_demo.py:223`：`plan_parent_delegation()` 展示父 agent 为什么会选择调用 subagent。
- `subagent_delegation_demo.py:247`：`synthesize_parent_answer()` 强调最终答案仍由父 agent 负责。

## How to Run

```bash
cd cases/speedrun-deer-flow
python unit-8-subagent-delegation/main.py
```

## Expected Output

你应该看到：

- `parent_decision.task_calls[0]` 是一次 `task` 派工单
- `runtime_snapshot` 包含 `thread_id`、`sandbox_id`、`parent_model`、`trace_id`
- `subagent_tools` 包含 `bash/read_file/write_file`，不包含 `task`
- `subagent_initial_state.messages` 只有一条 human prompt
- `subagent_initial_state.thread_data.workspace_path` 是 `/mnt/user-data/workspace`
- `events` 顺序是 `task_started -> task_running -> task_completed`
- `tool_result_for_parent` 以 `Task Succeeded. Result:` 开头
- `parent_final_answer` 使用了子 agent 结果
- `background_tasks_after_cleanup` 是空列表

## Exercises

### Explain It Back

为什么父 agent 不直接把完整对话历史交给子 agent？

为什么子 agent 共享 workspace/sandbox，但最终答案仍由父 agent 写？

为什么子 agent 的工具列表里必须移除 `task`？

### Modify It

- 修改 `plan_parent_delegation()` 里的 prompt，观察 `subagent_initial_state.messages` 怎样变化。
- 在 workspace 里增加一个文件，确认 `tool_result_for_parent` 会列出新的相对路径。
- 把 `disallowed_tools` 里的 `task` 临时删掉，观察测试为什么会失败。

## Debug Guide

### Observation Points

File: `subagent_delegation_demo.py:223`
What to observe: 父 agent 为什么决定调用 `task`
Breakpoint or log: 查看 `parent_decision`

File: `subagent_delegation_demo.py:67`
What to observe: runtime snapshot 从父上下文继承了哪些字段
Breakpoint or log: 查看 `runtime_snapshot`

File: `subagent_delegation_demo.py:78`
What to observe: 子 agent 初始 state 没有父对话全文
Breakpoint or log: 查看 `initial_state["messages"]`

File: `subagent_delegation_demo.py:103`
What to observe: 后台任务怎样从 running 走到 completed
Breakpoint or log: 查看 `task["status"]`

File: `subagent_delegation_demo.py:170`
What to observe: completed task 怎样被 cleanup
Breakpoint or log: 查看 `terminal`

### Common Failures

Symptom: `task` 出现在 `subagent_tools`
Cause: 子 agent 工具过滤被绕过
Fix: 检查 `SubagentExecutor.subagent_tools`
Verify: 输出里不再包含 `task`

Symptom: 子 agent initial state 里出现父对话全文
Cause: 把 parent conversation 当成 child messages 传入了
Fix: 只把 delegated prompt 放进 `messages`
Verify: `subagent_initial_state.messages` 只有一条 human message

Symptom: cleanup 后还有 background task
Cause: terminal status 不在 cleanup 集合里，或者没有调用 cleanup
Fix: 检查 `cleanup_terminal_tasks()`
Verify: `background_tasks_after_cleanup` 是空列表

### State Inspection

- 用 `python -m pdb unit-8-subagent-delegation/main.py`
- 在 `subagent_delegation_demo.py:256` 后检查 `parent_decision`
- 在 `subagent_delegation_demo.py:263` 后检查 `delegation`
- 在 `subagent_delegation_demo.py:268` 后检查 cleanup 前后的 `executor.background_tasks`

### Isolation Testing

- 只测工具过滤：new `SubagentExecutor(...)` 后访问 `subagent_tools`
- 只测父 agent 决策：调用 `plan_parent_delegation(...)`
- 只测子 agent state：构造 `TaskCall` 后调用 `build_initial_state(...)`
- 只测事件顺序：调用 `delegate(...)` 后查看 `events_for(task_id)`
- 只测 cleanup：手工设置 completed task 后调用 `cleanup_terminal_tasks()`
