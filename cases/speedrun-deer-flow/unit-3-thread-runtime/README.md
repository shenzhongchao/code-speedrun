# Unit 3: Thread Runtime

> **Motto**: *Each thread gets its own backpack*

## In Plain Language

如果 DeerFlow 不给每个 thread 单独发一个“背包”，上传的文件、生成的产物、临时工作区就会全混在一起。这个单元教的就是：一个 `thread_id` 怎样稳定地长成一组运行时路径和一个 `sandbox_id`。

## Background Knowledge

- **线程像工单号**：工厂里每个工单都要有自己的料箱。技术上，`thread_id` 决定目录根路径。
- **lazy init 像先贴标签再开箱**：有时先知道路径就够了，不必立刻创建目录。技术上就是 `before_agent()` 可以只计算 path，不创建文件夹。
- **错误边界像保险丝**：工具失败不等于整次对话崩掉。技术上就是把异常翻译成一条可继续处理的错误消息。

## Key Terminology

- **ThreadRuntime**：线程的最小运行时状态对象
- **lazy_init**：只计算路径，不立刻创建目录
- **sandbox_id**：某个线程当前挂到哪个 sandbox 实例
- **tool error boundary**：把工具异常转换成可恢复消息的边界层

## What This Unit Does

这个单元保留了 DeerFlow runtime 里三个最核心的动作：

1. 由 `thread_id` 推导出 `workspace / uploads / outputs`
2. 根据 `lazy_init` 决定目录是否马上创建
3. 把工具异常转成可恢复的错误消息

这正是原仓库里 `ThreadDataMiddleware`、`SandboxMiddleware` 和 `ToolErrorHandlingMiddleware` 真正想保护的东西。

## Key Code Walkthrough

- `thread_runtime_demo.py:24-28`：`before_agent()` 是线程运行时入口。它决定这次只算路径，还是顺手把目录建出来。
- `thread_runtime_demo.py:30-37`：`plan()` 把一个 thread id 映射成三条路径。这是 DeerFlow “每个对话一个文件系统切片”的核心。
- `thread_runtime_demo.py:39-45`：`ensure_thread_dirs()` 和 `attach_sandbox()` 把路径从“纸面计划”变成“真实可用的运行时状态”。
- `thread_runtime_demo.py:56-68`：`tool_error_boundary()` 模仿原仓库的工具异常兜底逻辑。重点不是异常类型本身，而是“错误也要变成 agent 能继续处理的消息”。
- `thread_runtime_demo.py:71-85`：`run_demo()` 同时展示 lazy 和 eager 两种模式，让你直观看到目录是否真的落盘。

## How to Run

```bash
cd src/speedrun-deer-flow
python unit-3-thread-runtime/main.py
```

## Expected Output

你应该看到：

- `lazy_runtime.workspace_exists` 是 `false`
- `eager_runtime.workspace_exists` 是 `true`
- `eager_runtime.sandbox_id` 是 `local`
- `error_boundary.status` 是 `error`

## Exercises

### Explain It Back

为什么 DeerFlow 要允许 `lazy_init=True`？什么情况下“先知道路径，再真正创建目录”会更合理？

### Modify It

- 把 `lazy_manager` 改成 `lazy_init=False`，看看输出怎么变。
- 把 `attach_sandbox(..., sandbox_id="remote")`，观察输出里的 `sandbox_id`。

## Debug Guide

### Observation Points

File: `thread_runtime_demo.py:24`
What to observe: 线程运行时入口如何决定 lazy 还是 eager
Breakpoint or log: 查看 `self.lazy_init`

File: `thread_runtime_demo.py:30`
What to observe: 三个路径是怎样由 thread id 推出来的
Breakpoint or log: 查看 `thread_root`

File: `thread_runtime_demo.py:39`
What to observe: 目录何时真正落盘
Breakpoint or log: 单步进入 `ensure_thread_dirs()`

File: `thread_runtime_demo.py:56`
What to observe: 工具报错后如何被转换成可恢复消息
Breakpoint or log: 观察 `exc.__class__.__name__`

### Common Failures

Symptom: lazy 模式下目录不存在
Cause: 这是预期行为，不是 bug
Fix: 如果你需要立刻生成目录，就用 `lazy_init=False`
Verify: `workspace_exists` 变成 `true`

Symptom: 所有线程写到同一个地方
Cause: 你把 `thread_id` 写死了
Fix: 检查 `plan()` 里是否还在用传入参数
Verify: 改不同 thread id 会得到不同路径

Symptom: 工具失败直接抛异常
Cause: 你绕过了 `tool_error_boundary()`
Fix: 把 failing call 包进 `tool_error_boundary(...)`
Verify: 输出里出现 `status: error`

### State Inspection

- 用 `python -m pdb unit-3-thread-runtime/main.py`
- 在 `thread_runtime_demo.py:77` 后检查 `lazy_runtime`
- 在 `thread_runtime_demo.py:78` 后检查 `eager_runtime`
- 运行结束后看 `unit-3-thread-runtime/_demo_data/threads/thread-eager/user-data/`

### Isolation Testing

- 单独调用 `ThreadRuntimeManager(...).plan("thread-x")`，不创建目录
- 单独调用 `ThreadRuntimeManager(...).ensure_thread_dirs(runtime)`，只看文件系统副作用
- 单独调用 `tool_error_boundary("bash", lambda: int("oops"))`，只看错误消息格式
