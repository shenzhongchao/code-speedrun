# Unit 7: 定时任务与心跳

## 用大白话说

这个单元让 AI 助手不只是"你问我答"，还能"主动行动"。定时任务就像手机闹钟——到了时间就执行指定的事情。心跳服务则像一个值班员——每隔一段时间醒来看看有没有需要处理的事。两者结合，让 nanobot 变成一个 24/7 运行的智能助手。

## 背景知识

**Cron 表达式**：Unix 系统中定义周期性任务的标准格式，如 `0 9 * * 1` 表示"每周一早上 9 点"。nanobot 通过 `croniter` 库解析 cron 表达式。

**asyncio.sleep**：Python 异步编程中的"等待"函数。与 `time.sleep` 不同，它不会阻塞整个程序——其他协程可以继续运行。定时任务服务用它来等待下一个任务的执行时间。

**虚拟工具调用（Virtual Tool Call）**：心跳服务的决策阶段不是让 LLM 自由回答，而是定义一个虚拟工具（`heartbeat`），让 LLM 通过工具调用返回结构化的决策（skip/run）。这比解析自由文本更可靠。

## 关键术语

- **CronService**：定时任务服务，管理和执行计划任务
- **CronSchedule**：定时计划，支持 at（定时）、every（间隔）、cron（表达式）三种模式
- **CronJob**：一个定时任务，包含计划、消息和执行状态
- **HeartbeatService**：心跳服务，定期唤醒 Agent 检查 HEARTBEAT.md
- **HEARTBEAT.md**：心跳配置文件，定义 Agent 需要主动关注的事项
- **两阶段执行**：Phase 1 决策（是否有任务）→ Phase 2 执行（完成任务）

## 这个单元做了什么

从 nanobot 的 `cron/` 和 `heartbeat/` 目录提取了自主执行的核心逻辑：

1. **cron.py** — 定时任务服务（任务增删、到期检查、执行回调）
2. **heartbeat.py** — 心跳服务（定期检查 HEARTBEAT.md、两阶段决策执行）
3. **main.py** — 演示定时任务的完整生命周期和心跳的三种场景

在真实的 nanobot 中，还有：
- cron 表达式支持（通过 croniter 库）和时区处理
- 任务的启用/禁用切换
- 心跳决策通过 LLM 虚拟工具调用完成（→ Unit 4 LLM 提供者）
- 心跳结果通过消息总线发送到最近活跃的渠道（→ Unit 2 消息总线）
- CronTool 让 Agent 自己管理定时任务（→ Unit 3 工具系统）

## 关键代码走读

**cron.py — 定时器循环**

```python
async def tick(self) -> int:
    now = _now_ms()
    due = [j for j in self.jobs
           if j.enabled and j.next_run_at_ms and now >= j.next_run_at_ms]
    for job in due:
        await self._execute_job(job)
    return len(due)
```

`tick()` 是定时器的核心：遍历所有任务，找出到期的，逐个执行。真实的 nanobot 中，`tick` 由 `asyncio.sleep` 驱动的循环自动调用。

**cron.py — 一次性任务的处理**

```python
if job.schedule.kind == "at":
    job.enabled = False          # 执行后禁用
    job.next_run_at_ms = None
else:
    job.next_run_at_ms = _compute_next_run(...)  # 计算下次执行时间
```

"at" 类型的任务执行一次后自动禁用（或删除），而 "every" 类型的任务会计算下一次执行时间。

**heartbeat.py — 两阶段设计的智慧**

为什么不直接让 Agent 执行 HEARTBEAT.md 中的所有内容？因为 HEARTBEAT.md 可能包含"每天早上发天气预报"这样的描述，但现在可能是下午——不需要执行。Phase 1 让 LLM 判断"现在是否需要行动"，避免不必要的执行。

## 运行方式

```bash
cd unit-7-cron-heartbeat
python main.py
```

## 预期输出

```
==================================================
Unit 7: 定时任务与心跳演示
==================================================

--- 定时任务服务 ---
添加任务: 天气播报 (id=xxx, 每 60 秒)
添加任务: 一次性提醒 (id=xxx, 一次性)
添加任务: 未来提醒 (id=xxx, 1 小时后)

当前任务: 3 个
  [xxx] 天气播报: every, 待执行
  [xxx] 一次性提醒: at, 待执行
  [xxx] 未来提醒: at, 待执行

--- 检查到期任务 ---
  [Cron] 执行任务 '一次性提醒': 提醒用户开会
  [Cron] 结果: 已完成: 提醒用户开会
执行了 1 个到期任务
  [xxx] 一次性提醒: ok (已禁用)

--- 心跳服务 ---

场景 1: 没有 HEARTBEAT.md
  结果: None（None = 无事可做）

场景 2: HEARTBEAT.md 无任务
  [Heartbeat] 检查 HEARTBEAT.md...
  [Heartbeat] 决策: skip（没有待办任务）
  结果: None

场景 3: HEARTBEAT.md 有任务
  [Heartbeat] 检查 HEARTBEAT.md...
  [Heartbeat] 决策: run（发现任务: ...）
  [通知] 心跳执行完成: ...
  结果: 心跳执行完成: ...
```

## 练习

1. **修改练习**：给 `CronService` 添加一个 `enable_job(job_id, enabled)` 方法，可以启用或禁用任务。

2. **扩展练习**：实现一个简单的心跳循环——用 `asyncio.sleep` 每 5 秒调用一次 `heartbeat.tick()`，运行 3 次后停止。

3. **用自己的话解释**：心跳服务为什么要用"两阶段"设计（先决策再执行），而不是直接执行 HEARTBEAT.md 中的所有内容？

## 调试指南

**观察点**：
- 在 `cron.tick()` 处加断点，观察哪些任务到期了
- 在 `heartbeat.tick()` 处观察 HEARTBEAT.md 的内容和决策结果

**常见问题**：
- 任务不执行 → 检查 `next_run_at_ms` 是否大于当前时间，任务是否 `enabled`
- 一次性任务重复执行 → 检查执行后 `enabled` 是否被设为 False
- 心跳总是 skip → 检查 HEARTBEAT.md 内容是否包含决策函数能识别的关键词

**状态检查**：
- `cron.list_jobs()` 查看所有活跃任务
- `job.last_status` 查看上次执行结果
- `heartbeat.tick_count` 查看心跳检查次数
