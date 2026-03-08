# Unit 6: 会话管理

## 用大白话说

这个单元就像一个"聊天记录本"。每个对话都有自己的记录本，记录了谁说了什么、什么时候说的。即使程序关掉再打开，记录本还在。而且记录本有个"书签"（last_consolidated），标记哪些内容已经被总结过了——Agent 只需要看书签后面的内容。

## 背景知识

**JSONL（JSON Lines）**：一种文件格式，每行是一个独立的 JSON 对象。相比普通 JSON 文件，JSONL 的优势是：追加写入不需要读取整个文件、单行损坏不影响其他行、可以用 `head`/`tail`/`grep` 直接查看。

**Append-Only（只追加）**：nanobot 的消息列表只追加不修改。即使记忆整合了旧消息，也不会从列表中删除它们，而是通过 `last_consolidated` 指针标记进度。这是为了 LLM 的 KV 缓存效率——如果修改了消息列表，缓存就失效了。

**Session Key**：格式为 `channel:chat_id`，唯一标识一个对话。同一个用户在不同平台上的对话是独立的会话。

## 关键术语

- **Session**：对话会话，包含消息列表、元数据和整合进度
- **SessionManager**：会话管理器，负责创建、加载、保存会话
- **last_consolidated**：整合指针，标记已被总结到 MEMORY.md 的消息数量
- **JSONL**：JSON Lines 格式，每行一条 JSON，用于会话持久化
- **对齐到 user 轮次**：确保历史消息以 user 消息开头，避免孤儿工具结果

## 这个单元做了什么

从 nanobot 的 `session/manager.py` 提取了会话管理的核心逻辑：

1. **session.py** — Session 数据类（消息存储 + 历史查询）和 SessionManager（JSONL 持久化）
2. **main.py** — 演示会话创建、消息追加、持久化、重新加载、历史对齐

在真实的 nanobot 中，还有：
- 旧版会话路径迁移（从 `~/.nanobot/sessions/` 到工作区）
- 会话列表查询（`list_sessions()`）
- 与 AgentLoop 的集成（→ Unit 1 中 `_save_turn` 方法）
- 工具结果截断（超过 500 字符的工具结果会被截断后存储）

## 关键代码走读

**session.py — get_history 的对齐逻辑**

```python
def get_history(self, max_messages=500):
    unconsolidated = self.messages[self.last_consolidated:]
    sliced = unconsolidated[-max_messages:]
    # 跳过开头的非 user 消息
    for i, m in enumerate(sliced):
        if m.get("role") == "user":
            sliced = sliced[i:]
            break
```

为什么要对齐？因为 LLM 的消息格式有严格要求：`tool` 消息必须跟在包含 `tool_calls` 的 `assistant` 消息后面。如果历史消息以孤立的 `tool` 结果开头，LLM 会报错。对齐到 user 轮次确保消息列表总是合法的。

**session.py — JSONL 持久化**

```python
def save(self, session):
    with open(path, "w") as f:
        f.write(json.dumps(metadata_line) + "\n")  # 第一行：元数据
        for msg in session.messages:
            f.write(json.dumps(msg) + "\n")         # 后续行：消息
```

第一行是元数据（会话键、创建时间、整合进度），后续每行是一条消息。加载时先读元数据，再逐行读消息。

## 运行方式

```bash
cd unit-6-session
python main.py
```

## 预期输出

```
==================================================
Unit 6: 会话管理演示
==================================================

--- 创建会话 ---
会话键: telegram:12345
消息数: 0
添加 6 条消息后: 6 条

--- 获取历史 ---
未整合消息: 6 条
  user      : 你好，我是小明
  assistant : 你好小明！有什么可以帮你的？
  user      : 帮我查一下天气
  assistant : 好的，让我查一下。 [+tool_calls]
  tool      : 北京今天晴，25°C [tool_result: web_search]
  assistant : 北京今天晴天，气温 25°C，适合出门。

--- 模拟记忆整合 ---
整合前: last_consolidated=0, 总消息=6
整合后: last_consolidated=4
可见历史: 2 条
  tool      : 北京今天晴，25°C
  assistant : 北京今天晴天，气温 25°C，适合出门。

--- 对齐到 user 轮次 ---
原始消息: 4 条
对齐后历史: 2 条（跳过了开头的 tool 和 assistant）
  user: 真正的开始
  assistant: 好的！
```

## 练习

1. **修改练习**：给 `SessionManager` 添加一个 `list_sessions()` 方法，扫描 sessions 目录，返回所有会话的键和最后更新时间。

2. **扩展练习**：实现一个 `Session.export_markdown()` 方法，把对话历史导出为可读的 Markdown 格式。

3. **用自己的话解释**：为什么 nanobot 选择"只追加"的消息存储策略，而不是在记忆整合后删除旧消息？这对 LLM 缓存有什么影响？

## 调试指南

**观察点**：
- 直接用文本编辑器打开 `.jsonl` 文件，查看存储格式
- 在 `get_history()` 处加断点，观察 `last_consolidated` 如何影响返回结果

**常见问题**：
- 会话加载失败 → 检查 JSONL 文件是否有格式错误（某行不是合法 JSON）
- 历史消息为空 → `last_consolidated` 可能等于 `len(messages)`，所有消息都被标记为已整合
- 重启后会话丢失 → 检查是否调用了 `manager.save()`

**状态检查**：
- `session.messages` 查看所有消息
- `session.last_consolidated` 查看整合进度
- `session.get_history()` 查看 Agent 实际看到的历史
