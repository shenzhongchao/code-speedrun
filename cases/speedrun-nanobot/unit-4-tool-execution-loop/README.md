# Unit 4: Agent Loop（工具调用主循环）

## In Plain Language
把它想成“班长调度循环”：先收任务，若需要查资料就派工具去做，拿到结果后再继续思考，直到给出最终答复。

## Background Knowledge
- **ReAct 风格循环**：模型与工具交替进行，直到得到最终答案。
- **Max Iterations**：防止无限循环的安全阈值。
- **Session History**：每轮结束后把用户与助手消息写回会话，供下一轮使用。

## Key Terminology
- **AgentLoopCore**：最小主循环实现。
- **Tool Result Injection**：将工具结果追加为 `role=tool` 消息。
- **Direct Processing**：不经过总线队列，直接处理一条指令（cron/heartbeat 常用）。

## What This Unit Does
本单元复刻 nanobot `agent/loop.py` 的核心闭环：
1) 从会话取历史并构建 messages（依赖 Unit 3）；
2) 调用 provider（依赖 Unit 6）；
3) 若返回 tool calls，则执行并回填结果；
4) 最终写回 session 并生成 outbound。

它是全项目最关键的“执行引擎”，Unit 1 会把它接到 bus、cron、heartbeat 上形成端到端流程。

## Key Code Walkthrough
- `runtime_loop.py:24`：构造函数注入 bus/session/context/provider/tools。
- `runtime_loop.py:70`：每轮调用 provider，判断是否需要工具。
- `runtime_loop.py:83`：执行工具并把结果作为 `role=tool` 追加。
- `runtime_loop.py:103`：本轮结束后持久化到 session。

## How to Run
```bash
python unit-4-tool-execution-loop/index.py
```

## Expected Output
```text
[Unit4] reply: 我已读取工具结果：...
[Unit4] sessions: [cli:direct]
```

## Exercises
1. 增加 `max_iterations` 命中后的兜底回复。
2. 在 `process_message` 中记录 `tools_used` 并打印。
3. **Explain It Back**：解释“为什么 tool result 要作为独立 `role=tool` 消息，而不是拼进 assistant 文本”。

## Debug Guide
### 1. Observation Points
File: `unit-4-tool-execution-loop/runtime_loop.py:70`
What to observe: 每一轮 provider 返回的是文本还是工具调用。
Breakpoint or log: 打印 `response.has_tool_calls`。

File: `unit-4-tool-execution-loop/runtime_loop.py:83`
What to observe: 工具结果如何回填到消息列表。
Breakpoint or log: 打印 `messages[-1]`。

### 2. Common Failures
Symptom: 循环永远不结束。
Cause: Provider 每次都返回 tool call。
Fix: 在 provider 中当收到 `role=tool` 后返回最终文本。
Verify: 程序能走到 final_content 分支。

Symptom: 回复为空。
Cause: Provider 返回 `content=None` 且没有兜底。
Fix: 增加 `(empty response)` 回退。
Verify: 出站消息有文本。

Symptom: 会话历史没更新。
Cause: 忘记 `session.append()`。
Fix: 在循环结束后追加 user/assistant 两条。
Verify: `sessions.list_keys()` 非空，history 长度增长。

### 3. State Inspection
- 打印 `len(messages)` 观察每轮消息增量。
- 检查 `session.history()`，确认写回顺序是否正确。

### 4. Isolation Testing
- 用 `MockProvider` + `ListDirTool` 就能独立跑通，不依赖真实模型。
- 修改用户输入关键词，测试“直接回答”与“工具调用”两条路径。
