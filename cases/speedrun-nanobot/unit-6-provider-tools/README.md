# Unit 6: Provider 抽象与工具协议

## In Plain Language
把它当成“经理 + 工具箱”协作：经理（Provider）负责决定下一步，工具箱（ToolRegistry）负责真正执行动作。

## Background Knowledge
- **Provider 接口**：统一 LLM 适配层，隐藏具体厂商差异。
- **Tool Calling**：模型先声明“要调用哪个函数 + 参数”，系统执行后再把结果回填。
- **Schema Contract**：工具参数结构通过 JSON Schema 声明，便于模型按格式调用。

## Key Terminology
- **LLMResponse**：模型响应对象，包含文本或 tool calls。
- **ToolCall**：一次工具调用请求（id/name/arguments）。
- **ToolRegistry**：工具注册中心，负责发现与执行。
- **MockProvider**：可预测的假模型，便于本地学习和调试。

## What This Unit Does
本单元实现了 nanobot `providers/base.py` 与 `agent/tools/registry.py` 的核心契约：
- Provider 只返回“意图”（文本或工具调用）；
- ToolRegistry 只负责“执行”；
- 两者通过统一结构解耦。

这套契约会被 Unit 4 的 AgentLoop 使用，形成“模型决定 -> 工具执行 -> 结果回填”的循环。

## Key Code Walkthrough
- `provider_tools.py:11`：定义 `ToolCall` / `LLMResponse`。
- `provider_tools.py:31`：`MockProvider.chat()` 决定是直接回复还是先发 tool call。
- `provider_tools.py:89`：`ToolRegistry.execute()` 根据名字执行已注册工具。
- `index.py`：演示完整握手流程。

## How to Run
```bash
python unit-6-provider-tools/index.py
```

## Expected Output
```text
[Unit6] final: 我已读取工具结果：...
```

## Exercises
1. 新增 `read_text` 工具，并让 `MockProvider` 在关键词“读文件”时调用它。
2. 给 `ToolRegistry.execute()` 增加参数校验失败提示。
3. **Explain It Back**：解释“为什么 Provider 不应该直接操作文件系统，而是要走工具协议”。

## Debug Guide
### 1. Observation Points
File: `unit-6-provider-tools/provider_tools.py:45`
What to observe: 触发 tool call 的条件判断。
Breakpoint or log: 打印 `last_user`。

File: `unit-6-provider-tools/provider_tools.py:90`
What to observe: 工具名字解析是否命中。
Breakpoint or log: `print(name, arguments)`。

### 2. Common Failures
Symptom: 总是直接回复，不走工具。
Cause: 关键词条件没命中。
Fix: 检查 `MockProvider.chat` 的判断逻辑。
Verify: 输出出现 `has_tool_calls=True`。

Symptom: 提示 `tool not found`。
Cause: 工具未注册或 name 不一致。
Fix: 确认 `registry.register()` 与 tool_call.name 对齐。
Verify: 能拿到工具执行结果。

Symptom: 目录读取异常。
Cause: `path` 参数非法或权限不足。
Fix: 改成当前工作目录下相对路径 `.`。
Verify: 输出目录项字符串。

### 3. State Inspection
- 打印 `registry.definitions()` 检查模型可见的工具 schema。
- 打印 `messages` 观察 assistant/tool 消息是否按顺序追加。

### 4. Isolation Testing
- 该单元可独立运行，不依赖 bus/session/context。
- 可用不同关键词测试 direct reply 和 tool call 两条分支。
