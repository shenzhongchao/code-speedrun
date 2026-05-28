# Lab 01: Add Slack Channel

目标：理解 channel normalize。

任务：给 Slack 事件增加无 thread 的 direct channel 场景，并补测试证明 `source.threadId` 可以为空但 `sessionKey` 稳定。

验收：`npm test` 通过。
