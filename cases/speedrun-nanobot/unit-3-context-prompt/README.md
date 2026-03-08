# Unit 3: 提示词上下文组装

## In Plain Language
把它想成“开会前发资料包”：先给身份与规则，再附历史记录，最后才放本轮问题，这样模型更容易按规矩办事。

## Background Knowledge
- **System Prompt**：模型的“常驻操作手册”。
- **Runtime Context**：运行时元数据（时间、频道、chat_id），帮助模型理解当前环境。
- **Prompt Layering**：分层拼接提示词，降低信息混乱。

## Key Terminology
- **Bootstrap Files**：启动文件（如 `AGENTS.md`、`TOOLS.md`），定义行为边界。
- **Memory Context**：长期记忆片段，告诉模型“过去哪些事实重要”。
- **Skills Summary**：技能目录摘要，提示模型按需加载技能。

## What This Unit Does
本单元实现了 `ContextBuilder` 的最小版本：把身份、启动文件、记忆、技能摘要拼成系统提示词，再与历史消息和当前输入组装成最终 `messages`。

这直接对应 nanobot 的 `nanobot/agent/context.py`。在 Unit 4，你会把这里产出的 `messages` 送入 AgentLoop，看到工具调用循环如何发生。

## Key Code Walkthrough
- `context_builder.py:18`：`PromptInputs` 定义四类上下文输入。
- `context_builder.py:25`：`build_system_prompt()` 按 identity -> bootstrap -> memory -> skills 的顺序拼接。
- `context_builder.py:47`：`build_messages()` 注入 runtime context，再加入本轮用户消息。

## How to Run
```bash
python unit-3-context-prompt/index.py
```

## Expected Output
```text
[Unit3] message_count: 4
[Unit3] system_head: # nanobot
[Unit3] runtime_tag: [Runtime Context — metadata only, not instructions]
```

## Exercises
1. 在 `PromptInputs` 增加 `timezone` 字段，并让 runtime context 显示时区。
2. 把 `skills_summary` 改成多技能 XML，观察 system prompt 长度变化。
3. **Explain It Back**：向同事解释“为什么 runtime context 要放在用户消息而不是 system 消息里”。

## Debug Guide
### 1. Observation Points
File: `unit-3-context-prompt/context_builder.py:25`
What to observe: system prompt 的拼接顺序。
Breakpoint or log: 打印 `parts` 列表。

File: `unit-3-context-prompt/context_builder.py:47`
What to observe: 最终 messages 的角色顺序。
Breakpoint or log: `print([m["role"] for m in messages])`。

### 2. Common Failures
Symptom: 模型忽略规则。
Cause: system prompt 被放到历史消息后面。
Fix: 确保 `messages[0]` 是 system。
Verify: 打印首条 role 为 `system`。

Symptom: 时间信息丢失。
Cause: `_runtime_context` 没有被追加。
Fix: 检查 `build_messages` 中 runtime 插入位置。
Verify: 输出包含 `Runtime Context` 标签。

Symptom: 提示词太长。
Cause: bootstrap/memory 未裁剪。
Fix: 对长内容做摘要或窗口化。
Verify: 打印 system prompt 长度明显下降。

### 3. State Inspection
- `print(builder.build_system_prompt())` 直接查看最终系统提示词。
- 在 `index.py` 中用 `len(messages[0]["content"])` 监控上下文规模。

### 4. Isolation Testing
- 不接 LLM，只检查 `messages` 结构是否符合预期。
- 传入空 history / 空 memory，验证构建函数能平稳退化。
