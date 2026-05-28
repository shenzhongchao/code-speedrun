# Unit 6: 原生边界

> **口号**: *让原生接缝保持狭窄*

## 用大白话先讲
这个单元解释了 OMX 如何使用原生 helper，而不用把整个项目都改造成原生应用。JavaScript 只需要把一个小命令对象送过边界，再拿回一个小事件对象，就可以把 helper 当成专业工具来使用。

## 背景知识
- **合同像过关申报单**：只要双方都认可字段格式，边界穿越就很顺畅。技术上说，runtime bridge 依赖稳定的 command/event 形状。
- **Sidecar 像专职技师**：你不会因为有个很擅长发动机的技师，就把整个办公室搬进修车厂。技术上说，OMX 把 Rust helper 限制在一个狭窄边界之后。
- **摘要器像门卫**：短输出直接放行，长而嘈杂的输出先压缩再通过。技术上说，sparkshell 会根据输出大小切换行为。

## 关键术语
- **Runtime command**：像 `AcquireAuthority` 或 `QueueDispatch` 这样的 JSON 形状请求。
- **Snapshot**：包含 authority、backlog、replay 和 readiness 的紧凑状态视图。
- **Spark route**：决定输出是否应该被摘要的命令分类结果。

## 这个单元做了什么
这个单元模拟了 OMX 最重要的两条原生接缝。第一条是 runtime bridge，它接受少量 command 变体并返回 event 对象。第二条是 sparkshell 风格的路由与长输出摘要。

## 关键代码走读
`index.js:12-30` 负责构建 snapshot 形状。它对应了原始仓库的一个重要理念：JavaScript 应该读取一个小而稳定的兼容视图，而不是直接依赖原生内部细节。

`index.js:32-86` 是 bridge 的核心。`index.js:33-34` 的注释就是这个单元的核心观点：只有当合同保持小且稳定时，这条原生边界才会健康。这里用 `AcquireAuthority`、`QueueDispatch` 和 `MarkNotified` 就足以把模式讲清楚。

`index.js:100-131` 处理 sparkshell 的路由和摘要。路由分类器负责判断某个命令是否可能产生长输出，而摘要器则把长输出压缩成 head/tail 元数据。

## 运行方式
```bash
cd /root/key_projects/learn-codebase/speedrun-oh-my-codex
node unit-6-native-boundaries/index.js
```

## 预期输出
你应该看到一个带有 `events`、`sparkRoute` 和 `sparkResult` 的 JSON。snapshot event 应该报告 `ready: true`，而长 `git status --short` 示例应该得到 `mode: "summary"` 的 spark 结果。

## 练习
### 用自己的话解释
为什么让 bridge 合同保持小而稳定，会比把所有原生细节都暴露给 JavaScript 更安全？

### 动手改
- 给 demo 事件序列增加一个 `MarkDelivered` 命令，并确认 backlog 发生变化。
- 把摘要阈值从 `6` 降到 `3`，观察有更多输出被摘要。

## 调试指南
### 观察点
文件：`index.js:12`
观察什么：snapshot 是如何从可变 bridge 状态导出的。
断点或日志：在调用 `captureSnapshot()` 前后查看 `state.dispatches`。

文件：`index.js:32`
观察什么：bridge 内部 command 到 event 的精确映射关系。
断点或日志：逐个单步 `execRuntimeCommand()` 的每个 `case`。

文件：`index.js:100`
观察什么：命令分类逻辑如何决定输出是不是“长输出”。
断点或日志：检查 `argv`、`command` 和 `subcommand`。

### 常见故障
现象：抛出 `Unsupported runtime command`。
原因：demo 发送了这个简化 bridge 还没建模的命令。
修复：给 `execRuntimeCommand()` 增加一个新 `case`，或者改回已支持的 demo 输入。
验证：重新运行，确认 event 列表完整输出。

现象：git 示例返回的是 `mode: "raw"`。
原因：输出行数已经不超过当前阈值。
修复：给示例输出再多加几行，或者降低阈值。
验证：重新运行，确认重新出现 `mode: "summary"`。

现象：snapshot 报告 `ready: false`。
原因：在抓取 snapshot 之前没有先获取 authority。
修复：保持 `AcquireAuthority` 命令出现在 `CaptureSnapshot` 之前。
验证：重新运行，确认 readiness 的 reasons 数组为空。

### 状态检查
- 在 speedrun 根目录运行：`node --input-type=module -e "import { createRuntimeBridgeState, execRuntimeCommand, captureSnapshot } from './unit-6-native-boundaries/index.js'; const state=createRuntimeBridgeState(); execRuntimeCommand(state,{command:'AcquireAuthority',owner:'leader',lease_id:'x',leased_until:'2099-01-01'}); console.log(captureSnapshot(state));"`

### 隔离测试
- 把示例 `git status --short` prompt 改成 `echo ok`，确认 `chooseSparkShellRoute()` 返回 `shell-native`。
- 再增加一条 dispatch 记录，确认 snapshot 里的 `pending` 和 `notified` 计数变化。
- 使用 VS Code 的 `Unit 6: Native Boundaries` 启动项，一条命令一条命令地观察 event 数组增长。
