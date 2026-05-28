# Unit 1: OMX 端到端总览

> **口号**: *一个 CLI，背后有很多层*

## 用大白话先讲
这个单元是理解整个仓库最快的入口。一个脚本完成了精简版 `omx setup`、把用户输入转成 overlay 状态、启动持久化 team runtime，并通过原生合同边界发送一次 dispatch。

## 背景知识
- **命令路由器像前台接待**：前台不负责解决问题，只负责把你送到对的窗口。技术上说，OMX 会先解析 argv，再把请求交给窄而清晰的 handler。
- **Overlay 像贴在手册上的便签**：底稿不变，但每次会话都能临时加一张说明。技术上说，OMX 会把运行时上下文插入 `AGENTS.md`。
- **持久状态像共用白板**：所有参与者都必须看同一块板。技术上说，leader 和 workers 通过 `.omx/` 下的文件协调。

## 关键术语
- **Invocation**：CLI 参数解析后的含义，比如 `launch` 或 `team`。
- **Overlay**：插入到 `AGENTS.md` 里的会话级文本，让 Codex 看到当前模式、skill 和代码上下文。
- **原生边界**：JavaScript 编排层和 helper 二进制之间的狭窄接口，通常表现为 JSON 命令或 argv 数组。

## 这个单元做了什么
这个脚本把 Unit 2 到 Unit 6 串了起来，并用比较真实的数据形状把它们接在一起。它不试图复刻所有 OMX 细节，而是证明这些核心子系统之间确实可以交换状态，而不是只停留在口头描述。

## 关键代码走读
`index.js:4-23` 的 imports 本身就是一个缩略版架构图：总流程依赖路由层、setup 层、overlay 层、team runtime 和原生边界层。`index.js:27-58` 是启动时 overlay 的关键步骤。它会检测激活 skill、写入 `.omx/state/skill-active-state.json`、构造 runtime overlay，并把 overlay 合并进 `AGENTS.md`。

真正的 happy path 从 `index.js:60-99` 开始。`parseInvocation()` 和 `routeInvocation()` 像真实 CLI 一样处理 `setup`、`launch` 和 `team`，但这里的 handler 是本地且极简的。原生接缝则在 `index.js:101-134`，这个阶段会排队一个 dispatch、把它标记为 notified，再运行 sparkshell 风格的长输出摘要器。

最终 JSON 报告在 `index.js:136-163` 组装完成。它是回答“OMX 到底由哪几层构成、每层持有什么状态”的最快方式。

## 运行方式
```bash
cd /root/key_projects/learn-codebase/speedrun-oh-my-codex
node unit-1-overall/index.js
```

## 预期输出
你应该看到一个包含四个顶层字段的 JSON：`setup`、`launch`、`team` 和 `nativeBoundary`。其中 `team.phase` 应该是 `team-exec`，`launch.skill` 应该是 `team`。

## 练习
### 用自己的话解释
为什么这个单元要 import 兄弟单元，而不是把逻辑全部内联复制进一个文件？这件事反映了原始仓库的什么设计思想？

### 动手改
- 修改 `index.js` 里的 `userPrompt`，让激活 skill 从 `team` 变成 `ralph`。
- 再加一条 runtime command，把 dispatch 标记成 delivered，然后观察 snapshot backlog 怎么变。

## 调试指南
### 观察点
文件：`index.js:27`
观察什么：用户输入是如何变成 overlay 和 skill 状态文件的。
断点或日志：在 `buildRuntimeOverlay()` 前暂停，检查 `activation`。

文件：`index.js:65`
观察什么：同一个 workspace 如何依次穿过 setup、launch 和 team 流程。
断点或日志：步入 `routeInvocation()`，比较每次解析得到的 invocation。

文件：`index.js:101`
观察什么：原生边界里的 dispatch 如何从 queued 变成 notified。
断点或日志：每次调用 `execRuntimeCommand()` 后查看 `runtimeBridge`。

### 常见故障
现象：输出里一直没有 `team-exec`。
原因：推进 phase 的那几行被删除或注释掉了。
修复：恢复 `index.js:94-95` 的 `advancePhase()` 调用。
验证：重新运行，确认 `team.phase` 变成 `team-exec`。

现象：`launch.skill` 变成 `default`。
原因：示例 prompt 不再包含可路由的关键词。
修复：把 `$team`、`$ralph` 或其他支持的触发词加回 `userPrompt`。
验证：重新运行，确认 `launch.skill` 改变。

现象：`AGENTS.md` 里看不到 overlay。
原因：单元没有完成 overlay 写回步骤。
修复：检查 `applyLaunchOverlay()` 是否仍然会读取并重写 `AGENTS.md`。
验证：打开 `unit-1-overall/demo-workspace/AGENTS.md`，确认 marker block 存在。

### 状态检查
- 查看安装后的 workspace：`find unit-1-overall/demo-workspace -maxdepth 4 -type f | sort`
- 查看注入后的 `AGENTS.md`：`sed -n '1,80p' unit-1-overall/demo-workspace/AGENTS.md`
- 查看团队状态：`cat unit-1-overall/demo-workspace/.omx/team/*/phase.json`

### 隔离测试
- 把 `index.js:80-99` 的 team 代码块临时注释掉，确认其余流程仍然能跑。
- 把 `chooseSparkShellRoute("run git status --short")` 改成短命令，比如 `echo ok`，确认摘要器会返回 `mode: "raw"`。
- 在根目录 `.vscode/launch.json` 里使用 `Unit 1: OMX End-to-End` 启动项，逐步单步整个流程。
