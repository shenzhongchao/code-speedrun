# Speedrun: nanobot（中文版）

> **源项目**: [nanobot](../nanobot) — 超轻量 AI Agent 框架（~4000 行代码）

## 项目简介

nanobot 是一个模块化的 AI Agent 框架，核心只有约 4000 行 Python 代码，却支持 10+ 聊天平台、20+ LLM 提供者、工具调用、记忆系统、定时任务等完整功能。

本 speedrun 将 nanobot 拆解为 7 个独立可运行的学习单元，每个单元聚焦一个核心概念。

## 架构总览

```
用户消息 (Telegram/Discord/CLI/...)
    ↓
┌─────────────────────────────────────┐
│  消息总线 (Unit 2)                    │
│  InboundMessage → asyncio.Queue      │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│  Agent 循环 (Unit 1)                  │
│                                      │
│  ┌─ 上下文构建 (Unit 5) ──────────┐  │
│  │  身份 + 引导文件 + 记忆 + 技能  │  │
│  └────────────────────────────────┘  │
│           ↓                          │
│  ┌─ LLM 调用 (Unit 4) ───────────┐  │
│  │  统一接口 → 100+ 提供者        │  │
│  └────────────┬───────────────────┘  │
│               ↓                      │
│       有工具调用？                    │
│      ╱          ╲                    │
│    是            否                   │
│    ↓              ↓                  │
│  ┌─ 工具执行 ─┐  保存会话 (Unit 6)  │
│  │ (Unit 3)   │       ↓             │
│  │ 文件/命令  │  发送回复            │
│  │ /搜索/...  │                      │
│  └─────┬──────┘                      │
│        ↓                             │
│    继续循环                           │
└──────────────┬──────────────────────┘
               ↓
┌─────────────────────────────────────┐
│  消息总线 (Unit 2)                    │
│  asyncio.Queue → OutboundMessage     │
└──────────────┬──────────────────────┘
               ↓
回复给用户

        ┌─ 定时任务 & 心跳 (Unit 7) ─┐
        │  自主唤醒 → Agent 循环       │
        └─────────────────────────────┘
```

## 学习路径

| 单元 | 主题 | 核心概念 | 运行命令 |
|------|------|----------|----------|
| **Unit 1** | [全局总览](unit-1-overall/) | 端到端消息处理，导入并编排所有模块 | `python unit-1-overall/main.py` |
| **Unit 2** | [消息总线](unit-2-message-bus/) | 异步队列解耦，InboundMessage/OutboundMessage | `python unit-2-message-bus/main.py` |
| **Unit 3** | [工具系统](unit-3-tool-system/) | 工具注册/校验/执行，安全防护 | `python unit-3-tool-system/main.py` |
| **Unit 4** | [LLM 提供者](unit-4-llm-provider/) | 统一接口，提供者注册表，模型匹配 | `python unit-4-llm-provider/main.py` |
| **Unit 5** | [上下文与记忆](unit-5-context-memory/) | 系统提示词构建，双层记忆系统 | `python unit-5-context-memory/main.py` |
| **Unit 6** | [会话管理](unit-6-session/) | JSONL 持久化，历史对齐，整合指针 | `python unit-6-session/main.py` |
| **Unit 7** | [定时任务与心跳](unit-7-cron-heartbeat/) | 自主唤醒，两阶段心跳，cron 调度 | `python unit-7-cron-heartbeat/main.py` |

**推荐顺序**：Unit 2 → Unit 3 → Unit 4 → Unit 5 → Unit 6 → Unit 7 → Unit 1

先理解各个子系统，最后看它们如何在 Unit 1 中协同工作。

## 快速开始

```bash
# 无需安装任何依赖，纯 Python 3.11+ 即可运行

# 运行所有单元
for i in 1 2 3 4 5 6 7; do
  echo "===== Unit $i ====="
  python unit-$i-*/main.py
  echo
done

# 或单独运行某个单元
python unit-2-message-bus/main.py
```

## 文件结构

```
speedrun-nanobot-cn/
├── README.md                    ← 你在这里
├── SIMPLIFICATIONS.md           ← 简化清单（扩展路线图）
├── pyproject.toml               ← 项目配置
├── .vscode/launch.json          ← VS Code 调试配置
├── unit-1-overall/              ← 全局总览
│   ├── main.py
│   └── README.md
├── unit-2-message-bus/          ← 消息总线
│   ├── events.py
│   ├── bus.py
│   ├── main.py
│   └── README.md
├── unit-3-tool-system/          ← 工具系统
│   ├── base.py
│   ├── registry.py
│   ├── tools.py
│   ├── main.py
│   └── README.md
├── unit-4-llm-provider/         ← LLM 提供者
│   ├── base.py
│   ├── registry.py
│   ├── provider.py
│   ├── main.py
│   └── README.md
├── unit-5-context-memory/       ← 上下文与记忆
│   ├── context.py
│   ├── memory.py
│   ├── main.py
│   └── README.md
├── unit-6-session/              ← 会话管理
│   ├── session.py
│   ├── main.py
│   └── README.md
└── unit-7-cron-heartbeat/       ← 定时任务与心跳
    ├── cron.py
    ├── heartbeat.py
    ├── main.py
    └── README.md
```
