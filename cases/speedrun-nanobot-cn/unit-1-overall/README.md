# Unit 1: 全局总览 — nanobot 端到端消息处理

## 用大白话说

这个单元是 nanobot 的"全景图"。想象一个客服中心：用户打电话进来（消息总线），前台把电话转给客服（Agent 循环），客服查资料（工具系统）、翻看之前的聊天记录（会话管理）、参考公司手册（上下文构建），然后回复用户。这个单元把所有环节串起来，让你看到一条消息从进入到回复的完整旅程。

## 背景知识

**Agent 循环（Agent Loop）**：AI Agent 的核心工作模式。不同于简单的"问答"，Agent 循环允许 LLM 多次调用工具、获取信息、再思考，直到得出最终答案。这就是 nanobot 能执行复杂任务的原因。

**ReAct 模式**：Reasoning + Acting 的缩写。LLM 先"思考"（生成文本），再"行动"（调用工具），然后根据工具结果继续思考。nanobot 的 Agent 循环就是 ReAct 模式的实现。

**消息驱动架构**：所有组件通过消息总线通信，而不是直接调用。这让系统更灵活——可以轻松添加新的聊天渠道，而不需要修改 Agent 核心。

## 关键术语

- **AgentLoop**：Agent 循环引擎，nanobot 的核心，协调所有子系统
- **ReAct 模式**：思考→行动→观察→思考的循环模式
- **max_iterations**：最大迭代次数（默认 40），防止 Agent 陷入无限循环
- **process_message**：处理一条消息的完整流程
- **_run_loop**：Agent 的内部迭代循环（LLM 调用 + 工具执行）

## 这个单元做了什么

从 nanobot 的 `agent/loop.py` 提取了核心处理引擎，并导入所有其他 Unit 的模块：

- **消息总线**（Unit 2）：接收用户消息、发送回复
- **工具系统**（Unit 3）：注册和执行工具
- **LLM 提供者**（Unit 4）：调用 LLM 获取回复
- **上下文构建**（Unit 5）：组装系统提示词和消息列表
- **会话管理**（Unit 6）：保存和加载对话历史
- **定时任务/心跳**（Unit 7）：自主执行和定期检查

演示了 5 个场景：简单对话、工具调用、多轮对话、定时任务触发、心跳服务。

## 关键代码走读

**main.py — Agent 循环的核心**

```python
async def _run_loop(self, messages):
    for iteration in range(self.max_iterations):
        response = await self.provider.chat(messages, tools=self.tools.get_definitions())

        if response.has_tool_calls:
            # 执行工具，把结果加入消息，继续循环
            result = await self.tools.execute(tc.name, tc.arguments)
            messages.append({"role": "tool", ...})
        else:
            # 得到文本回复，循环结束
            return response.content, tools_used
```

这就是 nanobot 的"心脏"。整个循环只有一个判断：LLM 是要调用工具还是直接回复？如果调用工具，执行后继续；如果直接回复，结束。简单但强大。

**main.py — 子系统编排**

```python
# 1. 获取会话 → Unit 6
session = self.sessions.get_or_create(msg.session_key)
# 2. 构建上下文 → Unit 5
messages = self.context.build_messages(history, msg.content, ...)
# 3. Agent 循环 → Unit 4 + Unit 3
final_content, tools_used = await self._run_loop(messages)
# 4. 保存会话 → Unit 6
session.add_message("user", msg.content)
self.sessions.save(session)
# 5. 发送回复 → Unit 2
return OutboundMessage(channel=msg.channel, ...)
```

每一步都调用了对应 Unit 的真实模块。这不是模拟——数据真的在各个子系统之间流动。

## 运行方式

```bash
cd unit-1-overall
python main.py
```

## 预期输出

```
============================================================
Unit 1: 全局总览 — nanobot 端到端消息处理
============================================================

工作区: /tmp/nanobot_overall_xxxxx

========================================
场景 1: 简单对话（纯文本回复）
========================================

  [AgentLoop] 收到: 你好，介绍一下自己
  [AgentLoop] 上下文: 4 条消息（含 0 条历史）
  [AgentLoop] 回复: 你好！我是 nanobot...

  最终回复: 你好！我是 nanobot...

========================================
场景 2: 工具调用（读取文件）
========================================

  [AgentLoop] 收到: 帮我读取文件 test.txt
  [AgentLoop] 工具调用: read_file({'path': 'README.md'})
  [AgentLoop] 工具结果: ...
  [AgentLoop] 回复: 根据工具返回的结果：...

========================================
场景 3: 多轮对话（会话持久化）
========================================
  会话消息数: 4
  ...

========================================
场景 4: 定时任务（→ Unit 7）
========================================
  添加定时任务: 状态检查
  执行了 1 个任务

========================================
场景 5: 心跳服务（→ Unit 7）
========================================
  心跳结果: ...

============================================================
总结
============================================================
  LLM 调用次数: N
  注册工具数: 2
```

## 练习

1. **修改练习**：给 `AgentLoop` 添加一个 `on_progress` 回调，在每次工具调用时通知外部（模拟 nanobot 的进度推送功能）。

2. **扩展练习**：实现 `/new` 命令——当用户发送 "/new" 时，清空当前会话并回复"新会话已开始"。

3. **用自己的话解释**：画一张流程图，展示一条消息从用户发出到收到回复经过了哪些组件。不看代码，凭记忆画，然后对照本单元的代码检查。

## 调试指南

**观察点**：
- 在 `process_message` 开头加断点，观察入站消息的完整结构
- 在 `_run_loop` 中观察每次迭代 LLM 返回了什么
- 在 `sessions.save()` 处观察会话如何持久化

**常见问题**：
- Agent 循环不停止 → 检查 MockProvider 是否总是返回 tool_calls，导致无限循环
- 工具执行失败 → 检查工具是否正确注册，参数是否匹配
- 会话历史为空 → 检查 session_key 是否一致（channel:chat_id）

**端到端调试**：
- 从 `InboundMessage` 开始，逐步跟踪数据流经每个子系统
- 检查每个子系统的输入和输出是否符合预期
