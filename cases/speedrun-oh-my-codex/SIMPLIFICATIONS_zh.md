# 简化说明

这里列出相对于原始仓库被简化、替换或省略的部分。
如果你后面想逐步恢复真实实现，这个文件就是导航图。

## Unit 1: OMX 端到端总览

- 启动路径只走到 overlay 与结果汇总，没有真正启动 Codex；真实启动流程在 `src/cli/index.ts`。
- 团队进度通过直接函数调用推进，没有真实 tmux 事件与 worker heartbeat；真实行为在 `src/team/runtime.ts`。

## Unit 2: 命令路由器

- 这里只建模了 `launch`、`resume`、`setup`、`team`、`sparkshell` 和 `help`；完整命令矩阵在 `src/cli/index.ts`。
- 未知命令只走默认 help 路径；真实 CLI 还处理本地 help ownership 与 launch fallback，逻辑在 `src/cli/index.ts`。

## Unit 3: Setup 与 Config

- 这里只安装了两个 prompt 和两个 skill；真实资产在 `prompts/` 与 `skills/`。
- TOML 合并逻辑被压缩成了一个小型受管块；真实的 selective upsert 与 cleanup 在 `src/config/generator.ts`。

## Unit 4: Overlay 与关键词路由

- 关键词检测只覆盖了很小一部分 registry；真实触发集合在 `src/hooks/keyword-registry.ts`。
- 省略了 overlay 锁、截断策略与多 section 优先级规则；真实实现位于 `src/hooks/agents-overlay.ts`。

## Unit 5: Team Runtime

- Worktree 这里只表现为规划后的路径，没有真正调用 git worktree；真实实现位于 `src/team/worktree.ts`。
- 没有启动 tmux pane 或 worker 子进程；真实持久化协作逻辑在 `src/team/runtime.ts` 与 `src/team/tmux-session.ts`。

## Unit 6: 原生边界

- 由于当前环境没有安装 Cargo，这里用 JavaScript 模拟 Rust runtime 与 sparkshell 的行为；真实二进制位于 `crates/omx-runtime/` 和 `crates/omx-sparkshell/`。
- Explore 路由与输出摘要只保留了 happy path；真实 fallback 与 hydration 逻辑在 `src/cli/explore.ts` 与 `src/cli/sparkshell.ts`。

