# Unit 4: Overlay 与关键词路由

> **口号**: *在运行时教会 AGENTS*

## 用大白话先讲
这个单元解释了 OMX 如何在不把所有流程硬编码进 CLI flag 的前提下改变会话行为。它会读取用户输入，判断是否应该激活某个 skill，把结果写入状态文件，然后把临时 overlay 注入到 `AGENTS.md`。

## 背景知识
- **关键词路由像金属探测器**：它只寻找少数特定信号，而不会关心所有文字。技术上说，OMX 会在 prompt 里查找显式 skill 调用或加权关键词。
- **Overlay 像可拆卸插页**：你可以为某次会议临时往手册里塞一页，会议结束后再拿掉。技术上说，运行时上下文通过 marker 边界包裹，方便安全替换。

## 关键术语
- **Skill activation**：记录当前激活了哪个工作流 skill 的状态对象。
- **Marker-bounded overlay**：放在起止 marker 之间的文本，方便重新生成而不破坏底稿。
- **Project memory**：关于技术栈、约定和当前模式的简短持久化说明，会在运行时暴露给 Codex。

## 这个单元做了什么
这个单元只保留理解概念最必要的部分：检测 skill、写入 `skill-active-state.json`、构建 overlay，并把 overlay 合并到 demo `AGENTS.md`。这已经足以讲清楚运行时心智模型，而不用把整套 hook 系统都搬进来。

## 关键代码走读
`index.js:18-43` 是检测引擎。这里最关键的规则在 `index.js:20-29`：显式的 `$team` 或 `$ralph` 调用优先级高于模糊关键词匹配。这就是为什么 OMX 既能保持好用，又不至于变得不可预测。

`index.js:45-62` 会写入持久化 activation state，这和原始仓库把 mode/skill 状态存到 `.omx/` 下的习惯一致。`index.js:64-93` 则负责构建 overlay 文本，并用 marker-bounded 的方式重新写入。

`index.js:95-130` 的 demo 会创建一个极简 `AGENTS.md`，激活 `$team`，写出 `skill-active-state.json`，再把 overlay 合并进文件。

## 运行方式
```bash
cd /root/key_projects/learn-codebase/speedrun-oh-my-codex
node unit-4-overlay-routing/index.js
```

## 预期输出
你应该看到一个 JSON，其中 `activation.skill` 是 `team`。demo workspace 里应该同时存在 `AGENTS.md` 和 `.omx/state/skill-active-state.json`。

## 练习
### 用自己的话解释
为什么显式 `$skill` 语法应该比模糊关键词匹配优先级更高？

### 动手改
- 去掉示例输入里的 `$team` 前缀，看看最后会匹配到哪个关键词。
- 新增一个 `review` 关键词定义，并确认 detector 能激活它。

## 调试指南
### 观察点
文件：`index.js:18`
观察什么：显式 skill 调用如何压过模糊关键词匹配。
断点或日志：查看 `explicit` 和返回的 activation 对象。

文件：`index.js:45`
观察什么：后续 OMX 组件可读取的持久化状态 payload。
断点或日志：在写入前检查 `payload`。

文件：`index.js:84`
观察什么：已有 marker block 如何在新 overlay 写入前被移除。
断点或日志：检查 `withoutExisting` 和 `overlayText`。

### 常见故障
现象：detector 返回 `default`。
原因：示例文本不再包含支持的显式调用或关键词。
修复：把 `$team`、`$ralph` 或其他支持的触发词加回输入。
验证：重新运行，确认 `activation.skill` 不再是 `default`。

现象：overlay 每次运行都会重复追加。
原因：marker replacement 逻辑被删除了，或者 marker 文本被改坏了。
修复：恢复 `applyOverlay()` 里的 marker-bounded 替换逻辑。
验证：连续运行两次，确认 `AGENTS.md` 里只有一个 marker block。

现象：`skill-active-state.json` 没有写出来。
原因：状态目录写入步骤被跳过。
修复：恢复 demo 中对 `writeSkillActivationState()` 的调用。
验证：重新运行，确认 `.omx/state/` 下出现该 JSON 文件。

### 状态检查
- 查看 activation 文件：`cat unit-4-overlay-routing/demo-workspace/.omx/state/skill-active-state.json`
- 查看合并后的 `AGENTS.md`：`sed -n '1,80p' unit-4-overlay-routing/demo-workspace/AGENTS.md`

### 隔离测试
- 在 speedrun 根目录运行：`node --input-type=module -e "import { detectSkillActivation } from './unit-4-overlay-routing/index.js'; console.log(detectSkillActivation('plan this before coding'))"`
- 修改 `buildRuntimeOverlay()` 的输入数组，确认渲染结果跟着变化。
- 使用 VS Code 的 `Unit 4: Overlay & Keyword Routing` 启动项，单步 marker replacement 过程。
