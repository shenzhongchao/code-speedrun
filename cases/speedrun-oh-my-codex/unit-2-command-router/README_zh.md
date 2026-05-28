# Unit 2: 命令路由器

> **口号**: *先解析，再分发*

## 用大白话先讲
这个单元解释了 OMX 怎样判断你到底想启动哪种会话。它把原始 argv 变成一个小而清晰的结构化含义，这样后面的代码就不需要反复猜用户意图。

## 背景知识
- **解析器像翻译员**：翻译员把杂乱表达变成清晰信息。技术上说，`parseInvocation()` 会把参数数组转成带类型的命令形状。
- **handler 表像总机**：总机不解决问题，只负责接通正确线路。技术上说，`routeInvocation()` 负责把命令映射到对应 handler。

## 关键术语
- **Launch invocation**：表示“启动 Codex”的请求，即使用户只输入了一串 flag。
- **Subcommand**：像 `setup`、`team`、`sparkshell` 这种命名分支。
- **Team args**：从 `omx team` 中推导出的 worker 数量、agent 类型和任务文本。

## 这个单元做了什么
这个单元用一个文件复现了 OMX CLI 最核心的参数解析规则。它展示了三个最重要的想法：裸 flag 会落到 `launch`，`team` 需要单独的参数归一化逻辑，路由应该和业务逻辑分离。

## 关键代码走读
`index.js:13-34` 会把 `team` 参数规范化成 `workerCount`、`agentType` 和 `task`。这对应了真实 CLI 的需求：像 `3:executor` 这种压缩写法，最终还是要变成显式 runtime 参数。

`index.js:36-80` 是核心解析器。`index.js:40-47` 这条规则最关键：如果第一个 token 缺失或者以 `--` 开头，OMX 会认为你仍然是在尝试启动 Codex。`index.js:82-93` 则只负责把解析结果交给 handler，而不关心 handler 具体做什么。

`index.js:118-157` 的 demo 会把五组示例输入跑过解析和路由。想最快理解命令表面时，先读这一段最省时间。

## 运行方式
```bash
cd /root/key_projects/learn-codebase/speedrun-oh-my-codex
node unit-2-command-router/index.js
```

## 预期输出
你应该看到一个包含若干路由结果的数组。第一个示例会把 `["--madmax","--high"]` 映射到 `launchWithHud`，第三个示例会把 `team` 输入映射到 `teamCommand`。

## 练习
### 用自己的话解释
为什么 OMX 会把 `omx --high` 当成一次 launch 请求，而不是未知命令？

### 动手改
- 新增一个叫 `doctor` 的子命令支持。
- 把默认 team worker 数量从 `3` 改成 `2`，然后观察输出怎么变化。

## 调试指南
### 观察点
文件：`index.js:13`
观察什么：`3:executor` 是怎么变成结构化 team 参数的。
断点或日志：检查 `match` 和 `normalizeTeamArgs()` 返回的对象。

文件：`index.js:36`
观察什么：第一个 token 如何决定解析分支。
断点或日志：打印 `first`，然后对不同示例输入逐个单步。

文件：`index.js:82`
观察什么：解析后的命令是如何交给 handler 表的。
断点或日志：在执行前检查 `handler`。

### 常见故障
现象：`team` 输入解析后得到空任务。
原因：`3:executor` 后面没有附带任务文本。
修复：在 staffing token 之后至少补一个任务单词。
验证：重新运行，确认 `task` 不为空。

现象：`--high` 被解析成 `unknown`。
原因：launch fallback 分支被改坏或删掉了。
修复：恢复 `index.js:42` 的 `first.startsWith("--")` 检查。
验证：重新运行，确认第一个示例仍然路由到 `launchWithHud`。

现象：路由阶段抛出 `No handler registered`。
原因：解析出的命令在 demo handler 表里没有对应项。
修复：补上对应 handler，或者提供 `default` handler。
验证：重新运行，确认每个示例都能返回路由结果。

### 状态检查
- 直接看 demo 输入：`index.js:108-116`
- 在 speedrun 根目录运行：`node --input-type=module -e "import { parseInvocation } from './unit-2-command-router/index.js'; console.log(parseInvocation(['team','2:planner','draft','scope']))"`

### 隔离测试
- 在 Node REPL 里调用 `parseInvocation([])`，确认它返回 `command: "launch"`。
- 调用 `normalizeTeamArgs(['4:verifier','audit','the','handoff'])`，确认 staffing 结果正确。
- 使用 VS Code 的 `Unit 2: Command Router` 启动项，一次只跟一条示例输入。
