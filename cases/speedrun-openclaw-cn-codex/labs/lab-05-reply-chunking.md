# Lab 05: Reply Chunking

目标：理解 delivery 层可靠性。

任务：给不同 channel 设置不同 `maxLength`，并保留 Slack thread。

验收：长文本被拆分，所有 chunk 都带相同 `runId` 和 thread 信息。
