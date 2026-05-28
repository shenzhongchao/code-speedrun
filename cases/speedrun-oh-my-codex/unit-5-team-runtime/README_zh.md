# Unit 5: Team Runtime

> **口号**: *持久化协作胜过临时并发*

## 用大白话先讲
这个单元解释了为什么 OMX 需要独立的 `team` runtime，而不是简单拉起几个 agent 然后听天由命。真正的团队执行需要 phase、task ownership、worker identity、worktree path，以及一个跨回合存活的共享状态根目录。

## 背景知识
- **Runtime 像项目经理手册夹**：里面记录 workers、tasks 和 phase 变化，避免事情在多轮协作里丢失。技术上说，OMX 会把团队元数据持久化到 `.omx/team/...`。
- **Phase machine 像红绿灯**：你只能沿着允许的方向前进。技术上说，`team-plan -> team-prd -> team-exec -> team-verify` 是受约束的状态机。
- **Worktree 像独立工位**：每个 worker 都需要自己的桌面，以免编辑互相冲突。技术上说，team mode 会给每个 worker 规划独立 worktree 路径。

## 关键术语
- **Team phase**：持久化执行生命周期中的当前步骤，比如 `team-plan` 或 `team-exec`。
- **Manifest**：描述 team 名称、请求任务、worker 数量和状态根目录的元数据。
- **Worktree path**：某个 worker 将要工作的文件系统位置。

## 这个单元做了什么
这个单元创建了一个小但足够真实的 team runtime。它会清洗 team 名、构建 tasks、把 tasks 分配给 workers、把状态文件写入 `.omx/team/...`，然后把 phase 推进到执行阶段，以展示运行中的协作状态。

## 关键代码走读
`index.js:17-65` 是 phase machine。这里最重要的是 `advancePhase()` 会拒绝非法跳转，这对应了原始仓库希望防止团队流程进入无意义状态的设计。

`index.js:67-111` 构建后续会持久化的数据：task 列表、worker 列表、inbox 路径和 JSON 状态文件。`index.js:134-170` 的 `startTeamRuntime()` 把它们接起来，其中 `index.js:167-169` 的注释是这个单元最重要的结论：持久化协作需要共享状态根目录。

`index.js:173-191` 的 demo 会启动 runtime、推进两个 phase、把一个 task 标记为完成、另一个标记为进行中，最后输出一个紧凑 snapshot。

## 运行方式
```bash
cd /root/key_projects/learn-codebase/speedrun-oh-my-codex
node unit-5-team-runtime/index.js
```

## 预期输出
你应该看到一个 JSON snapshot，其中 `phase: "team-exec"`，`workerCount: 3`，task 统计里有一个 completed、一个 in_progress、一个 pending。

## 练习
### 用自己的话解释
为什么把共享状态根目录放在 `.omx/team/` 下，会比把全部 team 状态只留在内存里更可靠？

### 动手改
- 把 `workerCount` 增加到 `4`，观察 task assignment 如何分布到更多 worker。
- 在验证后调用 `advancePhase(runtime.state, "team-fix", "...")`，强行走一次 `team-fix` loop，并观察 `current_fix_attempt`。

## 调试指南
### 观察点
文件：`index.js:17`
观察什么：允许的 phase transition 表，以及 fix attempt 计数器。
断点或日志：分别用合法和非法 target 单步 `advancePhase()`。

文件：`index.js:90`
观察什么：worker 记录如何获得自己的 worktree 和 inbox 路径。
断点或日志：检查 `buildWorkers()` 返回的 worker 对象。

文件：`index.js:134`
观察什么：runtime 在持久化前的完整对象。
断点或日志：查看 `runtime.manifest`、`runtime.tasks` 和 `runtime.workers`。

### 常见故障
现象：phase 推进时报 `Invalid transition`。
原因：请求的下一阶段不允许从当前阶段直接跳过去。
修复：遵守 `advancePhase()` 中定义的合法顺序。
验证：重新按 `team-plan -> team-prd -> team-exec` 跑一遍。

现象：snapshot 里所有 task 都还是 pending。
原因：demo 在启动 runtime 后没有更新 task 状态。
修复：恢复 `index.js:186-187` 的状态更新。
验证：重新运行，确认统计发生变化。

现象：worktree 路径看起来不对，或者是空的。
原因：worker 记录没有使用预期的 state root。
修复：检查传给 `buildWorkers()` 的 `stateRoot`。
验证：重新运行，查看 JSON snapshot 中的 `worktrees` 数组。

### 状态检查
- 查看 manifest：`cat unit-5-team-runtime/demo-workspace/.omx/team/*/manifest.json`
- 查看 task 状态：`cat unit-5-team-runtime/demo-workspace/.omx/team/*/tasks.json`
- 查看 worker 状态：`cat unit-5-team-runtime/demo-workspace/.omx/team/*/workers.json`

### 隔离测试
- 在 speedrun 根目录运行：`node --input-type=module -e "import { createTeamState, advancePhase } from './unit-5-team-runtime/index.js'; const state=createTeamState('demo'); console.log(advancePhase(state,'team-prd','ok'))"`
- 修改 `buildTasks()`，让第二个 task 属于 `designer`，确认 manifest 仍然正常。
- 用 VS Code 的 `Unit 5: Team Runtime` 启动项观察 runtime 在持久化前后如何变化。
