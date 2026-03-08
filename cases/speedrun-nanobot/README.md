> **Source**: [nanobot](https://github.com/HKUDS/nanobot) — cloned on 2026-02-27

# speedrun-nanobot（中文拆解版）

这个目录把 `HKUDS/nanobot` 拆成 6 个可独立运行的学习单元。目标是：先跑通主流程，再逐层放大细节，最后能自己重写一个最小可用版本。

## Quick Start
```bash
# Python 3.11+
python run_all.py
```

也可以逐个运行：
```bash
python unit-2-message-bus/index.py
python unit-3-context-prompt/index.py
python unit-4-tool-execution-loop/index.py
python unit-5-cron-heartbeat/index.py
python unit-6-provider-tools/index.py
python unit-1-overall/index.py
```

## Learning Units

Unit 1: Overall — nanobot 主流程总览
  Concept:      端到端编排，导入并串联 Unit 2~6 的真实模块
  Teaches:      理解 gateway 形态下“聊天 + cron + heartbeat 共用 AgentLoop”
  Source files: nanobot/cli/commands.py, nanobot/agent/loop.py, nanobot/channels/manager.py, nanobot/cron/service.py, nanobot/heartbeat/service.py
  Imports from: Unit 2 (bus/session), Unit 3 (context), Unit 4 (loop), Unit 5 (cron/heartbeat), Unit 6 (provider/tools)
  Runs as:      python unit-1-overall/index.py
  Prereqs:      None

Unit 2: 消息总线与会话归档
  Concept:      用异步队列解耦渠道输入与主循环处理，并按 session_key 归档历史
  Teaches:      为什么 nanobot 先做路由/会话，再做模型推理
  Source files: nanobot/bus/events.py, nanobot/bus/queue.py, nanobot/session/manager.py
  Exports:      InboundMessage, OutboundMessage, MessageBus, SessionStore
  Runs as:      python unit-2-message-bus/index.py
  Prereqs:      None

Unit 3: 提示词上下文组装
  Concept:      把 identity/bootstrap/memory/skills/history/runtime 拼成一次 LLM 输入
  Teaches:      上下文分层和 runtime metadata 注入策略
  Source files: nanobot/agent/context.py, nanobot/agent/skills.py, nanobot/agent/memory.py
  Exports:      PromptInputs, ContextBuilder
  Runs as:      python unit-3-context-prompt/index.py
  Prereqs:      None

Unit 4: Agent Loop 工具执行循环
  Concept:      模型响应与工具调用交替迭代，直到收敛出最终回复
  Teaches:      ReAct 式循环在工程里的最小实现
  Source files: nanobot/agent/loop.py, nanobot/agent/tools/registry.py
  Exports:      AgentLoopCore
  Runs as:      python unit-4-tool-execution-loop/index.py
  Prereqs:      Unit 2, Unit 3, Unit 6

Unit 5: 定时任务与心跳唤醒
  Concept:      Cron 到点触发 + Heartbeat 两阶段判定（decide -> execute）
  Teaches:      后台任务如何与主循环松耦合联动
  Source files: nanobot/cron/service.py, nanobot/heartbeat/service.py
  Exports:      CronService, CronJob, HeartbeatDecisionProvider, HeartbeatService
  Runs as:      python unit-5-cron-heartbeat/index.py
  Prereqs:      None

Unit 6: Provider 抽象与工具协议
  Concept:      Provider 决策与 ToolRegistry 执行分离
  Teaches:      统一模型层与工具层契约，便于替换实现
  Source files: nanobot/providers/base.py, nanobot/providers/litellm_provider.py, nanobot/agent/tools/base.py, nanobot/agent/tools/filesystem.py
  Exports:      BaseProvider, MockProvider, ToolRegistry, ListDirTool, LLMResponse, ToolCall
  Runs as:      python unit-6-provider-tools/index.py
  Prereqs:      None

## Coverage Review
Coverage:
  ✅ Covered:  nanobot/cli/, nanobot/agent/, nanobot/bus/, nanobot/session/, nanobot/cron/, nanobot/heartbeat/, nanobot/providers/, nanobot/config/（在 Unit 1/3 中织入）
  ⏭️ Skipped:  bridge/src/（独立 TypeScript WhatsApp bridge，属外部接入层）, case/（演示资源）, tests/（测试工程）
  ⏭️ Skipped:  nanobot/channels/* 具体平台实现（Telegram/Slack/Matrix 等），在 Unit 1 用统一入口抽象代替
  ⚠️ Gap check: 无关键高频依赖遗漏；高频模块 bus/agent/config/channels/providers/cron 均被主线覆盖

## Architecture (Speedrun)
```text
Inbound Message
   |
   v
[Unit2 MessageBus + SessionStore]
   |
   v
[Unit3 ContextBuilder] --> messages
   |
   v
[Unit4 AgentLoopCore] <--> [Unit6 Provider + ToolRegistry]
   |
   +--> Outbound Message
   |
   +<-- [Unit5 CronService]
   |
   +<-- [Unit5 HeartbeatService]
```

## 建议学习顺序
1. 先跑 `python unit-1-overall/index.py` 看全链路。
2. 再按 `2 -> 3 -> 6 -> 4 -> 5` 深挖每个子系统。
3. 最后对照 `../nanobot/` 原仓库，把简化实现逐项还原（见 `SIMPLIFICATIONS.md`）。
