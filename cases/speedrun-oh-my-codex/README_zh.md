# Speedrun: oh-my-codex

语言： [English](./README.md) | [简体中文](./README_zh.md)

> **源码来源**: [oh-my-codex](https://github.com/Yeachan-Heo/oh-my-codex) — 克隆日期 2026-04-07

## oh-my-codex 是什么
oh-my-codex，通常简称 OMX，是构建在 OpenAI Codex CLI 之上的一层工作流增强层。它保留 Codex 作为真正执行任务的引擎，再额外提供可复用的 prompts 和 skills、面向 `AGENTS.md` 的运行时 overlay、持久化的 `.omx/` 状态目录，以及在单会话不够用时可启用的 tmux/worktree 团队模式。原始仓库的主逻辑主要是 Node/TypeScript CLI，同时带有少量 Rust crate，用作运行时合同和 shell 辅助能力的窄边界 sidecar。

## 这个 Speedrun 覆盖什么
这个 speedrun 聚焦在项目最核心的主干：`omx` 入口怎样解析命令、安装自己的工作层、注入运行时上下文、启动持久化团队执行，并通过稳定合同与原生 helper 通信。为了让学习路径保持清晰，这里有意不展开 docs、missions、playground 示例、发布脚本，以及很多可选子命令。

## 快速开始
```bash
cd /root/key_projects/learn-codebase/speedrun-oh-my-codex
npm install
node unit-1-overall/index.js
```

这个 speedrun 没有额外第三方依赖，所以 `npm install` 主要是用来确认环境正常。

直接运行任意单元：

```bash
node unit-2-command-router/index.js
node unit-3-setup-config/index.js
node unit-4-overlay-routing/index.js
node unit-5-team-runtime/index.js
node unit-6-native-boundaries/index.js
```

## 学习路径

| Unit | 标题 | 口号 | 核心概念 |
|------|------|------|----------|
| 1 | OMX 端到端总览 | *一个 CLI，背后有很多层* | 端到端主流程 |
| 2 | 命令路由器 | *先解析，再分发* | 把 argv 转成 OMX 的命令意图 |
| 3 | Setup 与 Config | *先把工作层装进去* | 安装 prompts、skills、hooks 和受管配置 |
| 4 | Overlay 与关键词路由 | *在运行时教会 AGENTS* | 检测 skill 并注入会话级 overlay |
| 5 | Team Runtime | *持久化协作胜过临时并发* | 持久化 worker、task、phase 与 worktree 路径 |
| 6 | 原生边界 | *让原生接缝保持狭窄* | 通过合同与 runtime、sparkshell helper 通信 |

## 架构一眼看懂
- Unit 2 解释了为什么 `omx --madmax --high` 仍然只是一次普通的启动请求。
- Unit 3 说明 `omx setup` 本质上是在安装一套文件系统布局，而不只是写一个 TOML 文件。
- Unit 4 展示了 OMX 为什么把 `AGENTS.md` 当作运行时表面，而不是静态说明文档。
- Unit 5 解释了 `omx team` 为什么需要 `.omx/` 下的持久状态，而不是简单内存并发。
- Unit 6 展示了 Rust helper 如何被收束在窄小的 JSON/argv 合同之后。

## 调试
用 VS Code 打开 `/root/key_projects/learn-codebase/speedrun-oh-my-codex`，然后使用根目录下的 [.vscode/launch.json](./.vscode/launch.json)。每个 unit 都有独立的启动项，`Run Current File` 适合临时单步跟踪某一个抽取出来的文件。
