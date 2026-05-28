# Teaching Notes

- 先跑 Unit 1，再拆 Unit 2-6。学习者先看到完整链路，后续细节才有位置感。
- Unit 3 和 Unit 4 是主干。不要把太多时间花在真实渠道 SDK 细节上。
- 讲 Gateway 时强调：Gateway 规范化请求，不决定回复内容。
- 讲 Context 时强调：system prompt 不是一段静态文本，而是 workspace、memory、skills、history 的运行时产物。
- 讲 Agent Loop 时强调：`agent` 接受任务，`agent.wait` 等 lifecycle 完成；tool stream 的 end 不是 run end。
- 讲 Tools Safety 时强调：prompt 约束是软提示，policy/sandbox 是硬边界。
- 讲 Reply Delivery 时强调：delivery 不重新决策，只负责可靠、幂等、按渠道投递。
