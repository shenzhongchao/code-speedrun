# Lab 04: Approval Flow

目标：实现真实 approval 状态流。

任务：让 `ask` policy 先返回 pending，再由外部调用 approve/reject。

验收：approve 后执行 tool，reject 后不执行 tool。
