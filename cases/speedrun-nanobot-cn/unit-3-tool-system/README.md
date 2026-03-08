# Unit 3: 工具系统

## 用大白话说

这个单元就像一个"瑞士军刀工具箱"。Agent（AI 助手）本身只会"思考"和"说话"，但通过工具系统，它可以读文件、执行命令、搜索网页——就像给大脑接上了手和脚。每个工具都有一份"使用说明"，Agent 看了说明后决定用哪个。

## 背景知识

**Function Calling（函数调用）**：OpenAI 在 2023 年引入的机制，让 LLM 不仅能生成文本，还能"调用函数"。LLM 收到工具定义（JSON Schema 格式）后，会在回复中返回 `tool_calls`，指定要调用的函数名和参数。应用层负责实际执行并把结果返回给 LLM。

**JSON Schema**：一种描述 JSON 数据结构的标准。用来定义工具参数的类型、是否必填、枚举值等。LLM 根据 Schema 生成合法的参数。

**抽象基类（ABC）**：Python 的 `abc.ABC` 让你定义"接口"——只声明方法签名，不实现。子类必须实现所有抽象方法，否则无法实例化。这保证了所有工具都有统一的接口。

## 关键术语

- **Tool**：工具抽象基类，定义了 name/description/parameters/execute 四个必须实现的接口
- **ToolRegistry**：工具注册表，管理所有已注册工具的容器
- **JSON Schema**：描述工具参数结构的标准格式，LLM 据此生成合法参数
- **Function Calling**：LLM 通过返回 tool_calls 来"调用"工具的机制
- **deny_patterns**：ExecTool 的危险命令黑名单，用正则表达式匹配

## 这个单元做了什么

从 nanobot 的 `agent/tools/` 目录提取了工具系统的核心架构：

1. **base.py** — 工具抽象基类，定义统一接口 + 参数校验逻辑
2. **registry.py** — 工具注册表，负责注册、查找、执行工具
3. **tools.py** — 两个示例工具：ReadFileTool（读文件）和 ExecTool（执行命令）
4. **main.py** — 完整演示：注册、校验、执行、安全防护

在真实的 nanobot 中，工具系统还包括：
- WriteFileTool / EditFileTool / ListDirTool（→ 文件操作）
- WebSearchTool / WebFetchTool（→ 网页搜索和抓取）
- SpawnTool（→ 子代理生成）
- CronTool（→ Unit 7 定时任务）
- MessageTool（→ 跨渠道消息发送）
- MCP 工具包装器（→ 外部 MCP 服务器的工具）

## 关键代码走读

**base.py — 工具到 LLM 的桥梁**

```python
def to_schema(self) -> dict[str, Any]:
    return {
        "type": "function",
        "function": {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
        },
    }
```

这个方法把工具转换成 OpenAI 的 Function Calling 格式。LLM 收到这些定义后，就知道有哪些工具可用、每个工具需要什么参数。

**registry.py — 执行流程**

```python
async def execute(self, name: str, params: dict[str, Any]) -> str:
    tool = self._tools.get(name)          # 1. 找到工具
    errors = tool.validate_params(params)  # 2. 校验参数
    result = await tool.execute(**params)   # 3. 执行
```

为什么错误信息后面要加 `_HINT`？因为 LLM 会看到这个提示，引导它分析错误并换个方式重试，而不是盲目重复同样的调用。

**tools.py — 安全防护**

```python
DENY_PATTERNS = [
    r"\brm\s+-[rf]{1,2}\b",     # rm -rf
    r"\b(mkfs|diskpart)\b",      # 格式化磁盘
    r":\(\)\s*\{.*\};\s*:",      # fork 炸弹
]
```

这是"最佳努力"的安全防护——不能保证拦截所有危险命令，但能挡住最常见的破坏性操作。真实的 nanobot 还支持白名单模式和工作目录限制。

## 运行方式

```bash
cd unit-3-tool-system
python main.py
```

## 预期输出

```
==================================================
Unit 3: 工具系统演示
==================================================

已注册 3 个工具: ['greet', 'read_file', 'exec']

--- 工具定义（OpenAI 格式）---
  greet: 用指定语言向用户问好。
    参数: {"name": {"type": "string", "description": "用户名"}, "language": ...}
  read_file: 读取指定路径的文件内容。
    参数: {"path": {"type": "string", "description": "文件路径"}}
  exec: 执行 shell 命令并返回输出。请谨慎使用。
    参数: {"command": {"type": "string", "description": "要执行的 shell 命令"}}

--- 参数校验 ---
  合法参数: errors=[]
  缺少 name: errors=['missing required name']
  非法语言: errors=['language must be one of ['zh', 'en', 'ja']']

--- 工具执行 ---
  greet: 你好，nanobot！
  greet(en): Hello, nanobot!

--- 读取文件 ---
  文件内容: 这是一个测试文件的内容。
nanobot 工具系统演示。

--- 执行命令 ---
  echo: Hello from nanobot!
  python: 4

--- 安全防护 ---
  rm -rf /: Error: 命令被安全防护拦截（检测到危险模式）
  shutdown: Error: 命令被安全防护拦截（检测到危险模式）

--- 错误处理 ---
  不存在的工具: Error: Tool 'nonexistent' not found. Available: greet, read_file, exec
```

## 练习

1. **修改练习**：实现一个 `WriteFileTool`，接受 `path` 和 `content` 参数，将内容写入文件。注意处理目录不存在的情况（提示：`Path.parent.mkdir(parents=True, exist_ok=True)`）。

2. **扩展练习**：给 `ExecTool` 添加一个"白名单模式"——只允许执行匹配白名单正则的命令，其他一律拒绝。

3. **用自己的话解释**：为什么 nanobot 的工具系统要用 JSON Schema 来定义参数，而不是直接用 Python 的函数签名？这样做对 LLM 有什么好处？

## 调试指南

**观察点**：
- 在 `registry.execute()` 处加断点，观察 LLM 传来的参数长什么样
- 在 `tool.validate_params()` 处观察校验过程

**常见问题**：
- `Tool 'xxx' not found` → 工具没注册，检查 `registry.register()` 是否被调用
- 参数校验失败 → 检查 LLM 返回的参数是否符合 JSON Schema（类型、必填字段）
- ExecTool 超时 → 命令执行时间超过 timeout，考虑增大超时或优化命令

**隔离测试**：
- 每个工具都可以单独实例化和测试：`await ReadFileTool().execute(path="test.txt")`
- 不需要启动整个 Agent 就能验证工具逻辑
