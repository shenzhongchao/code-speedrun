# Debug Guide

## Unit 1

- 断点：`runScenario()` 的 `[Gateway]` 输出前。
- 观察：`runId`、`sessionKey`、`idempotencyKey`、`source`。
- 常见错误：把 tool denied 当成 Gateway 错误；实际应在 Loop/Tools 边界出现。

## Unit 2

- 断点：`validateConnection()` 返回前。
- 观察：local、remote token、node `deviceId`。
- 断点：每个 channel 的 `normalize()` 返回前。
- 观察：Slack `threadId` 是否保留。

## Unit 3

- 断点：`prepareRunContext()` 返回前。
- 观察：`agentScope`、`bootstrapFiles`、`memoryHits`、`skills`、`promptBudget`。
- 常见错误：把 session history 和 memory recall 混成同一类上下文。

## Unit 4

- 断点：`submit()` 中 `accepted/queued` 事件。
- 断点：`runEmbeddedAgent()` tool start 前。
- 观察：同一 `sessionKey` 的 run 是否串行。
- 常见错误：`wait()` 只能等 lifecycle end/error，不能被 tool end 唤醒。

## Unit 5

- 断点：`createGuardedTool().call()` policy 决策后。
- 观察：hook 改写后的 args、deny 是否先于 tool 执行。
- 常见错误：认为 prompt injection 可以覆盖 deny policy。

## Unit 6

- 断点：`deliverRunResult()` dedupe 后。
- 观察：重复 `idempotencyKey`、NO_REPLY、chunk、Slack thread。
- 常见错误：在 delivery 层重新决定是否应该回复；这里只处理可靠投递。
