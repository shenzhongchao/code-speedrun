# Speedrun NanoClaw

> **源码**: [nanoclaw](https://github.com/qwibitai/nanoclaw) — 克隆于 2026-02-26

## 这是什么

NanoClaw 是一个轻量级的个人 AI 助手，它通过 WhatsApp 接收消息，在隔离的 Linux 容器中运行 Claude 智能体来处理请求，然后把结果发回给你。整个系统只有一个 Node.js 进程和几个源文件。

## 架构一句话概括

```
WhatsApp (baileys) --> SQLite --> 轮询循环 --> Docker 容器 (Claude Agent SDK) --> 回复
```

## 学习路径

| 单元 | 主题 | 核心概念 |
|------|------|----------|
| [Unit 1](unit-1-overall/) | 全局总览 | 端到端主流程：消息进 → 处理 → 回复出 |
| [Unit 2](unit-2-whatsapp-channel/) | WhatsApp 通道 | 消息收发、连接管理、触发词过滤 |
| [Unit 3](unit-3-sqlite-persistence/) | SQLite 持久化 | 数据库 schema、消息存储、状态管理 |
| [Unit 4](unit-4-container-runner/) | 容器运行器 | 容器挂载、进程生成、流式输出解析 |
| [Unit 5](unit-5-group-queue/) | 分组队列 | 并发控制、每组排队、空闲管理 |
| [Unit 6](unit-6-ipc-scheduler/) | IPC 与调度器 | 文件系统 IPC、定时任务、cron 调度 |
| [Unit 7](unit-7-agent-runner/) | Agent Runner | 容器内运行时、Claude SDK 调用、MCP 工具、查询循环 |
| [Unit 8](unit-8-skills-engine/) | Skills Engine | 技能安装/卸载、三方合并、manifest、状态管理 |

## 快速开始

```bash
cd speedrun-nanoclaw
npm install
npm run all        # 依次运行所有单元
npm run unit1      # 只运行第 1 单元
```

## 前置要求

- Node.js 20+
- 不需要 Docker（所有容器操作已被 stub）
- 不需要 WhatsApp 账号（所有网络操作已被 stub）
