# Unit 5: 定时任务与心跳唤醒

## In Plain Language
把它想成“闹钟 + 值班巡检”：Cron 像定时闹钟按计划触发任务，Heartbeat 像巡检员周期检查待办并决定是否唤醒主流程。

## Background Knowledge
- **Cron 调度**：在未来某个时间点执行任务。
- **Two-Phase Heartbeat**：先判定（有没有任务），再执行（交给 AgentLoop）。
- **Callback 模式**：调度器不关心业务细节，只调用回调。

## Key Terminology
- **CronJob**：定时任务实体，包含 next_run_at。
- **run_pending**：扫描到期任务并执行。
- **HeartbeatDecision**：心跳判定结果（`skip` / `run`）。
- **on_execute**：真正执行业务的回调函数。

## What This Unit Does
本单元对应 nanobot 的 `cron/service.py` 与 `heartbeat/service.py` 的核心思想：
- CronService 管“什么时候触发”；
- HeartbeatService 管“是否唤醒主循环”；
- 真正执行交由外部回调（在 Unit 1 里接入 AgentLoop）。

## Key Code Walkthrough
- `scheduler.py:18`：`CronService.add_job()` 写入最小调度状态。
- `scheduler.py:33`：`run_pending()` 扫描到期任务并执行回调。
- `scheduler.py:63`：`HeartbeatDecisionProvider.decide()` 解析待办 Markdown。
- `scheduler.py:78`：`HeartbeatService.tick()` 实现“两阶段”心跳。

## How to Run
```bash
python unit-5-cron-heartbeat/index.py
```

## Expected Output
```text
[Unit5] cron_outputs: ['[cron:job-1] 总结今天完成事项']
[Unit5] heartbeat_result: [heartbeat] 执行任务: 每晚 22:00 复盘今天输出
```

## Exercises
1. 把 `interval_s` 改成不同值，观察 `next_run_at` 更新逻辑。
2. 增加 `enabled=False` 的 job，验证不会被执行。
3. **Explain It Back**：解释“为什么 heartbeat 要先判定再执行，而不是每次都调用 AgentLoop”。

## Debug Guide
### 1. Observation Points
File: `unit-5-cron-heartbeat/scheduler.py:33`
What to observe: 哪些任务被判定为到期。
Breakpoint or log: 打印 `now` 与 `job.next_run_at`。

File: `unit-5-cron-heartbeat/scheduler.py:78`
What to observe: heartbeat 决策分支。
Breakpoint or log: 打印 `decision.action`。

### 2. Common Failures
Symptom: cron 没有任务输出。
Cause: `interval_s` 太大或 `enabled=False`。
Fix: 先用 `interval_s=0` 验证链路。
Verify: `cron_outputs` 非空。

Symptom: heartbeat 总是 skip。
Cause: HEARTBEAT 文本里没有 `- [ ]`。
Fix: 增加未完成待办项。
Verify: `heartbeat_result` 出现执行文本。

Symptom: 任务执行后不再触发。
Cause: 没有刷新 `next_run_at`。
Fix: 在 run_pending 后更新 next_run。
Verify: 第二次调用到期后还能触发。

### 3. State Inspection
- 打印 `cron.jobs` 查看 job 状态变化。
- 检查 `decision.tasks` 是否正确提取未完成项。

### 4. Isolation Testing
- 该单元不依赖真实 LLM；`HeartbeatDecisionProvider` 可完全本地运行。
- 用不同 HEARTBEAT Markdown 直接测试 skip/run 两条路径。
