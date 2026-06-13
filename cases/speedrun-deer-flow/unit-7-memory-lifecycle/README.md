# Unit 7: Memory Lifecycle

> **Motto**: *Memory keeps lessons, not scratch paper*

## In Plain Language

DeerFlow 的 memory 不是把整段聊天记录无脑存起来。工具调用、shell 输出、上传文件路径这些东西只对当前请求有用，放进长期记忆反而会污染后续对话。这个单元教的是：一段 noisy message stream 怎样被过滤、更新成 memory JSON，再注入下一次 prompt。

## Background Knowledge

- **长期记忆像用户画像**：它应该保存偏好、工作背景、长期事实，而不是每次工具执行的过程。
- **ToolMessage 像施工噪音**：它对本轮推理有用，但不是用户长期偏好。
- **上传路径像临时取件码**：`/mnt/user-data/uploads/...` 只在当前 thread/session 有意义，未来请求里可能已经失效。
- **scripted LLM 像固定答案的 LLM**：真实版本调用模型生成结构化更新；教学版用固定规则生成同形状的 `user/history/newFacts/factsToRemove` payload。

## Key Terminology

- **MemoryMiddleware**：agent 执行后把可记忆对话送入 memory queue 的 middleware
- **Memory updater**：读取旧 memory 和新对话，生成更新后的 memory JSON
- **Upload block**：UploadsMiddleware 注入 human message 的 `<uploaded_files>` 片段
- **Atomic write**：先写临时文件，再替换正式 memory 文件
- **`<memory>`**：注入下一次 system prompt 的长期记忆片段

## What This Unit Does

这个单元保留了 memory 生命周期里五个关键动作：

1. 构造包含 human、AI tool call、ToolMessage、final AI response 和 upload block 的消息流
2. 只保留 human 和 final assistant response
3. 删除 upload-only turn，并 scrub `/mnt/user-data/uploads/...`
4. 把过滤后的对话格式化成 LLM updater 输入
5. 用 scripted LLM 生成结构化更新 payload，再 merge 到 memory JSON
6. 原子写入 memory JSON，并构造下一次 prompt 的 `<memory>` section

学完这个单元，你应该能理解：为什么 DeerFlow 的 memory 需要过滤，而不是简单保存所有 messages。

## Key Code Walkthrough

- `memory_lifecycle_demo.py:24`：`filter_messages_for_memory()` 是过滤入口。
- `memory_lifecycle_demo.py:37`：upload block 会被删除，upload-only turn 会被整轮丢弃。
- `memory_lifecycle_demo.py:47`：带 `tool_calls` 的 AIMessage 和 ToolMessage 不进入 memory input。
- `memory_lifecycle_demo.py:80`：`format_conversation_for_update()` 把 filtered messages 转成 updater prompt 会读取的对话文本。
- `memory_lifecycle_demo.py:90`：`scripted_llm_structured_update()` 模拟真实 LLM 返回 `user/history/newFacts/factsToRemove`。
- `memory_lifecycle_demo.py:149`：`apply_structured_update()` 像真实 updater 一样检查 `shouldUpdate`、补时间戳、创建 facts。
- `memory_lifecycle_demo.py:216`：`save_memory_atomic()` 先写 `.tmp` 再替换正式文件。
- `memory_lifecycle_demo.py:223`：`build_memory_context()` 每次从文件重新加载 memory。

## How to Run

```bash
cd cases/speedrun-deer-flow
python unit-7-memory-lifecycle/main.py
```

## Expected Output

你应该看到：

- `filtered_messages` 里没有 tool-call AIMessage
- `filtered_messages` 里没有 ToolMessage
- upload-only turn 被丢弃
- `conversation_for_llm` 只包含用户输入和最终 assistant response
- `structured_update` 包含 `user`、`history`、`newFacts`、`factsToRemove`
- 保存后的 `facts` 带有 `content`、`category`、`confidence`、`createdAt`、`source`
- `memory_context` 是 `<memory>...</memory>`
- 输出里没有 `/mnt/user-data/uploads/...`

## Exercises

### Explain It Back

为什么 ToolMessage 和带 tool call 的 AIMessage 不应该进入长期记忆？

为什么上传文件路径在本轮有用，但不应该被保存到未来对话？

### Modify It

- 在 `build_demo_messages()` 里加一个新的用户偏好，确认它进入 memory context。
- 加一条看起来很有信息量的 ToolMessage，确认它仍然不会被保存。

## Debug Guide

### Observation Points

File: `memory_lifecycle_demo.py:24`
What to observe: message filter 如何决定保留或丢弃一条消息
Breakpoint or log: 查看 `message.type`

File: `memory_lifecycle_demo.py:37`
What to observe: upload-only turn 怎样触发 `skip_next_ai`
Breakpoint or log: 查看 `cleaned`

File: `memory_lifecycle_demo.py:90`
What to observe: scripted LLM 返回的结构化 payload
Breakpoint or log: 查看 `structured_update`

File: `memory_lifecycle_demo.py:149`
What to observe: payload 怎样 merge 成 memory JSON
Breakpoint or log: 查看 `section_update` 和 `fact`

File: `memory_lifecycle_demo.py:216`
What to observe: memory JSON 怎样原子写入
Breakpoint or log: 查看 `temp_path`

### Common Failures

Symptom: memory 里出现 `/mnt/user-data/uploads/`
Cause: upload block scrub 或 final scrub 被绕过
Fix: 检查 `filter_messages_for_memory()` 和 `scrub_upload_mentions()`
Verify: `json.dumps(saved)` 不包含 uploads 路径

Symptom: memory context 是空的
Cause: 没有 user/final assistant pair 通过过滤
Fix: 加一条真实 human turn 和最终 AI response
Verify: `build_memory_context()` 返回 `<memory>`

### State Inspection

- 用 `python -m pdb unit-7-memory-lifecycle/main.py`
- 在 `memory_lifecycle_demo.py:258` 后检查 `filtered`
- 在 `memory_lifecycle_demo.py:260` 后检查 `structured_update`
- 运行结束后看 `unit-7-memory-lifecycle/_demo_data/_runtime/memory.json`

### Isolation Testing

- 只测过滤：构造 `DemoMessage` 列表后调用 `filter_messages_for_memory(...)`
- 只测更新：调用 `scripted_llm_structured_update(memory, messages)`，再调用 `apply_structured_update(...)`
- 只测 prompt：写一个 memory JSON 后调用 `build_memory_context(...)`
