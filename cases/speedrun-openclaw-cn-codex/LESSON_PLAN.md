# OpenClaw Speedrun 6 课教学计划

每课建议 60-90 分钟：先运行示例，再画数据流，再读核心函数，最后做一个失败路径实验。

| 课时 | 目标 | 课堂流程 | 验收 |
|------|------|----------|------|
| Unit 1 Overall | 建立一条消息从入口到回复的全局模型 | 运行 `unit-1-overall/index.js`，对比 Telegram、WebChat、tool denied 三个场景，追踪 `runId/sessionKey/idempotencyKey/source/payloads` | 能讲清 Gateway、Context、Loop、Delivery 四段边界 |
| Unit 2 Gateway Entry | 理解控制平面、渠道规范化和连接校验 | 运行 Unit 2，比较 Telegram、Slack、WebChat envelope，调试 `validateConnection()` | 能解释 Gateway 为什么只产出统一 envelope |
| Unit 3 Session Context | 理解 agent scope、workspace、bootstrap、memory、skills、prompt budget | 运行 Unit 3，调试 `prepareRunContext()`，观察缺失文件、记忆排序和 skill gating | 能区分长期记忆、bootstrap 和 session history |
| Unit 4 Agent Loop | 理解队列、生命周期、stream、wait、错误和持久化 | 运行 Unit 4，观察 same-session queue、assistant delta、tool event、history store | 能解释 `agent` 与 `agent.wait` 的不同语义 |
| Unit 5 Tools Safety | 理解 skills、hooks、policy、approval、sandbox 五层边界 | 运行 Unit 5，触发 allow/ask/deny、hook block、workspace traversal | 能说明 prompt safety 不能替代硬 policy |
| Unit 6 Reply Delivery | 理解 payload shaping、NO_REPLY、chunk、retry、dead-letter、channel formatter | 运行 Unit 6，构造重复 key、长回复、Slack thread、失败 transport | 能解释 delivery 是可靠性边界，不重新决策 |

课前准备：
- Node.js 22.12+。
- 在本目录运行 `npm run all` 和 `npm test`。
- 打开 `SOURCE_MAP.md` 对照真实 OpenClaw 文件名。

课后练习：
- 完成 `EXERCISES.md` 中每个 unit 的第一个任务。
- 从 `labs/` 任选一个 lab，把测试补上再实现。
