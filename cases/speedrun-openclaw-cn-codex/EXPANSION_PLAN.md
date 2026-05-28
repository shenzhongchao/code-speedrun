# OpenClaw Speedrun 教学扩展实施计划

目标：把 `cases/speedrun-openclaw-cn-codex` 从“6 个可运行概念示例”扩展成“6 个完整课时的教学项目”。每个课时应能支持 60-90 分钟教学，包含机制讲解、代码走读、调试实验、练习任务、源码映射和验收方式。

## 一、总体目标

当前 speedrun 已经建立了 6 个核心单元：

- Unit 1: Overall
- Unit 2: Gateway Entry
- Unit 3: Session Context
- Unit 4: Agent Loop
- Unit 5: Tools Safety
- Unit 6: Reply Delivery

下一阶段不是推翻现有结构，而是在每个单元上补齐教学闭环：

1. 真实问题场景
2. 架构图和数据流
3. 关键机制解释
4. 可运行代码实验
5. 调试任务
6. 渐进练习
7. 真实 OpenClaw 源码对照
8. 验收测试

完成后，学习者应能回答：

- 一条消息如何从渠道进入 OpenClaw？
- session、workspace、memory、system prompt 如何决定助理上下文？
- agent loop 如何排队、运行、流式输出、等待和持久化？
- skills、hooks、tool policy、sandbox 如何共同形成工具安全边界？
- agent payload 如何可靠投递回原始渠道？

## 二、建议新增文档

在 speedrun 根目录新增以下教学文档：

```text
LESSON_PLAN.md
GLOSSARY.md
SOURCE_MAP.md
EXERCISES.md
DEBUG_GUIDE.md
ARCHITECTURE.md
TEACHING_NOTES.md
```

### 1. `LESSON_PLAN.md`

用途：6 个课时的总纲。

内容：

- 每课目标
- 建议时长
- 课前准备
- 课堂流程
- 代码演示顺序
- 调试任务
- 课后练习
- 验收标准

### 2. `GLOSSARY.md`

用途：统一术语。

必须包含：

- agent run
- Gateway
- control plane
- channel
- envelope
- session key
- agent scope
- workspace
- bootstrap files
- memory recall
- system prompt
- skill
- hook
- tool policy
- sandbox
- lifecycle stream
- assistant stream
- tool stream
- payload
- reply delivery
- idempotency

### 3. `SOURCE_MAP.md`

用途：把 speedrun 文件映射到真实 OpenClaw 源码。

格式建议：

```markdown
## Unit 3: Session Context

Speedrun:
- `unit-3-session-context/session-context.js`

OpenClaw:
- `src/agents/agent-scope.ts`
- `src/agents/bootstrap-files.ts`
- `src/agents/memory-search.ts`
- `src/agents/pi-embedded-runner/system-prompt.ts`
- `src/agents/pi-embedded-runner/skills-runtime.ts`

What to compare:
- sessionKey 如何解析 agent
- bootstrap 文件如何注入
- memory 如何进入上下文
```

### 4. `EXERCISES.md`

用途：集中收纳所有练习和参考答案。

每个练习包含：

- 目标
- 修改文件
- 任务描述
- 提示
- 预期输出
- 参考实现思路

### 5. `DEBUG_GUIDE.md`

用途：给学习者明确断点清单。

每个 unit 包含：

- 推荐断点
- 观察变量
- 预期变化
- 常见错误

### 6. `ARCHITECTURE.md`

用途：统一放架构图、时序图、状态机。

建议包含：

- 全链路架构图
- assistant turn 时序图
- session context 数据流
- agent loop 状态机
- tool safety 分层图
- reply delivery 数据流

### 7. `TEACHING_NOTES.md`

用途：给讲师或自学者的讲解提示。

内容：

- 每章常见误解
- 讲解顺序建议
- 哪些地方适合现场调试
- 哪些地方可以和真实源码对照

## 三、建议新增目录

```text
fixtures/
tests/
labs/
```

### 1. `fixtures/`

放输入样例，供各 unit 和测试复用。

建议文件：

```text
fixtures/telegram-direct.json
fixtures/webchat-request.json
fixtures/slack-thread.json
fixtures/duplicate-message.json
fixtures/tool-denied.json
fixtures/tool-failure.json
fixtures/long-reply.json
fixtures/no-reply.json
```

### 2. `tests/`

放最小行为测试。

建议文件：

```text
tests/unit-2-gateway-entry.test.js
tests/unit-3-session-context.test.js
tests/unit-4-agent-loop.test.js
tests/unit-5-tools-safety.test.js
tests/unit-6-reply-delivery.test.js
```

测试框架建议优先使用 Node 内置 `node:test`，避免引入额外依赖。

### 3. `labs/`

放挑战任务说明和可选起始代码。

建议文件：

```text
labs/lab-01-add-slack-channel.md
labs/lab-02-memory-ranking.md
labs/lab-03-session-history-store.md
labs/lab-04-approval-flow.md
labs/lab-05-reply-chunking.md
```

## 四、Unit 1 扩展计划：Overall

### 教学目标

让学习者建立全局心智模型：一条消息从入口到回复，依次穿过哪些边界，每一层产出什么数据。

### 当前不足

- 只展示 happy path。
- 缺少完整时序图。
- 没有解释关键字段如何贯穿全链路。
- 没有失败路径和变体输入。

### 需要新增的内容

#### 1. README 扩展

在 `unit-1-overall/README.md` 中新增：

- 全链路时序图
- 数据包跟踪表
- happy path 逐步讲解
- failure path 逐步讲解
- WebChat vs Telegram 输入对比

数据包跟踪表字段：

| 字段 | 产生位置 | 被谁使用 | 作用 |
|------|----------|----------|------|
| `runId` | Unit 2 | Unit 4/6 | 标识一次 run |
| `sessionKey` | Unit 2 | Unit 3/4 | 决定 agent 和 session |
| `idempotencyKey` | Unit 2 | Unit 6 | 防止重复投递 |
| `source` | Unit 2 | Unit 6 | 决定回复去哪里 |
| `payloads` | Unit 4 | Unit 6 | 最终回复内容 |

#### 2. 代码扩展

修改 `unit-1-overall/index.js`：

- 增加 `runScenario(name, request)`。
- 增加至少 3 个场景：
  - Telegram direct message
  - WebChat control-plane request
  - tool denied failure
- 打印每个阶段的简化 trace。

建议输出结构：

```text
[Gateway] normalized request
[Context] agent scope + memory hits
[Loop] lifecycle/tool/assistant events
[Delivery] transport result
```

#### 3. 调试实验

新增到 `DEBUG_GUIDE.md`：

- 断点 1：Gateway normalize 后
- 断点 2：`prepareRunContext()` 返回前
- 断点 3：`runtime.agent()` 内部 tool start
- 断点 4：`deliverRunResult()` 内部 dedupe 后

#### 4. 练习

新增到 `EXERCISES.md`：

- 实现一个普通问答 turn，不触发工具。
- 构造重复 `idempotencyKey`，证明第二次投递被拦截。
- 构造 unknown channel，观察错误发生在哪一层。

### 验收标准

- `node unit-1-overall/index.js` 至少跑 3 个场景。
- 输出能清楚区分 Gateway、Context、Loop、Delivery 四个阶段。
- README 能让学习者不读其他 unit 也理解全链路。

## 五、Unit 2 扩展计划：Gateway Entry

### 教学目标

讲清楚入口统一、控制平面、渠道规范化和幂等请求。

### 当前不足

- 只有 Telegram 示例。
- connection lifecycle 很简化。
- 没有体现 node/operator/channel 的差异。
- 没有重复消息和多入口对比。

### 需要新增的内容

#### 1. README 扩展

新增：

- Gateway 角色说明：operator、channel、node、web client。
- connect lifecycle：
  - connect
  - auth/pairing
  - accepted/rejected
  - event publish
- normalize 对比表：
  - Telegram raw event
  - Slack thread event
  - WebChat request
  - CLI command

#### 2. 代码扩展

修改 `unit-2-gateway-entry/entry.js`：

- 新增 `createWebChatClient()`
- 新增 `createSlackChannel()`
- 新增 `createNodeClient()`
- 增加 basic pairing/auth 模拟：
  - local client auto accepted
  - remote client requires token
  - node requires deviceId
- 增加 duplicate message 示例。

建议新增 API：

```js
createSlackChannel({ agentId })
createWebChatEnvelope({ sessionKey, text, clientId })
createNodeInvokeEnvelope({ nodeId, command, params })
validateConnection({ client, config })
```

#### 3. fixtures

新增：

- `fixtures/telegram-direct.json`
- `fixtures/webchat-request.json`
- `fixtures/slack-thread.json`

#### 4. 测试

新增 `tests/unit-2-gateway-entry.test.js`：

- Telegram event normalize 生成稳定 `sessionKey`。
- Slack thread event 保留 `threadId`。
- WebChat request 生成 `source.kind = "control-plane"`。
- remote client 无 token 被拒绝。

#### 5. 练习

- 实现 `createDiscordChannel()`。
- 给 `idempotencyKey` 加入 account/channel，避免不同账号 messageId 冲突。

### 验收标准

- Unit 2 至少展示 3 种入口。
- 测试覆盖 normalize、connect validate、idempotency。
- README 能解释 Gateway 为什么需要统一 envelope。

## 六、Unit 3 扩展计划：Session Context

### 教学目标

讲清楚 agent scope、workspace、bootstrap、memory、skills、system prompt 如何决定一次 run 的上下文。

这是最重要的扩展单元之一。

### 当前不足

- workspace 只是内存对象。
- memory search 太简单。
- 没有 session history 和长期记忆的区分。
- 没有 prompt budget、截断、缺失文件处理。
- skills 只是数组，没有 discovery/gating 概念。

### 需要新增的内容

#### 1. README 扩展

新增专题：

- session key 格式：
  - `agent:main:main`
  - `agent:main:telegram:@user`
  - group session
  - subagent/session 变体
- workspace 模拟目录：
  - `AGENTS.md`
  - `SOUL.md`
  - `USER.md`
  - `MEMORY.md`
  - `skills/`
  - `sessions/`
- memory 三层：
  - bootstrap memory
  - searchable memory
  - transcript history
- prompt budget：
  - 为什么不能把所有记忆塞进 prompt
  - 截断策略
  - 缺失文件 marker

#### 2. 代码扩展

修改 `unit-3-session-context/session-context.js`：

- 增加 workspace file store。
- 增加 bootstrap truncation。
- 增加 memory ranking：
  - title match 权重高
  - body match 权重低
  - recent memory 加分
- 增加 session history loader。
- 增加 skills discovery/gating。
- 增加 prompt budget report。

建议新增 API：

```js
createWorkspaceStore(files)
resolveSessionHistory({ sessionKey, store })
rankMemory({ query, entries })
applyPromptBudget({ sections, maxChars })
discoverSkills({ workspace, enabledSkills, binaries })
buildContextReport(context)
```

#### 3. fixtures

新增：

- `fixtures/workspace-main.json`
- `fixtures/memory-entries.json`
- `fixtures/session-history.json`
- `fixtures/skills-registry.json`

#### 4. 测试

新增 `tests/unit-3-session-context.test.js`：

- session key 解析到正确 agent。
- 缺失 bootstrap 文件生成 marker。
- 过长 bootstrap 被截断。
- title memory match 排在 body match 前。
- disabled skill 不进入 prompt。

#### 5. 练习

- 给 memory ranking 增加时间衰减。
- 增加 `TOOLS.md` 注入。
- 实现 group session 的 context 标记。
- 实现 `/context list` 风格的 budget report。

### 验收标准

- Unit 3 能展示 workspace、memory、history、skills、prompt budget 五类上下文。
- README 能解释长期记忆和 session history 的区别。
- 测试覆盖 context 组装的主要边界。

## 七、Unit 4 扩展计划：Agent Loop

### 教学目标

讲清楚 agent loop 作为运行时系统的机制：排队、生命周期、流式事件、工具调用、等待、错误、持久化。

这是最重要的扩展单元之一。

### 当前不足

- 只有一个同步 happy path。
- 没有 queued/timeout/error 状态。
- 没有 assistant delta 分段。
- 没有 session history persistence。
- 没有 compaction 模拟。

### 需要新增的内容

#### 1. README 扩展

新增：

- Agent Loop 状态机：

```text
accepted -> queued -> started -> tool_running -> streaming -> ended
                                      |
                                      v
                                    error
```

- `agent` vs `agent.wait`：
  - `agent` 返回 accepted
  - `agent.wait` 等 end/error
  - wait timeout 不取消 run
- per-session queue：
  - 同一 session 串行
  - 不同 session 可并行
- stream 类型：
  - lifecycle
  - assistant
  - tool
  - compaction

#### 2. 代码扩展

修改 `unit-4-agent-loop/agent-loop.js`：

- `agent()` 立即返回 accepted job handle。
- 后台运行 job。
- `wait(runId, { timeoutMs })` 支持超时。
- assistant delta 分段输出。
- tool error path。
- run timeout path。
- session history store。
- compaction mock。

建议新增 API：

```js
createAgentRuntime({ tools, sessionStore, clock })
runtime.submit(context)
runtime.wait(runId, { timeoutMs })
runtime.subscribe(listener)
createSessionStore()
compactHistory(history)
```

#### 3. 测试

新增 `tests/unit-4-agent-loop.test.js`：

- 同一 session run 串行。
- 不同 session run 可并行。
- `wait` 超时不取消 run。
- tool error 产生 lifecycle error。
- run end 后写入 session history。
- 历史过长触发 compaction。

#### 4. 练习

- 实现 abort signal。
- 实现 tool update event。
- 实现 assistant delta coalescing。
- 实现 retry after compaction。

### 验收标准

- Unit 4 可以演示至少 4 条路径：success、tool error、wait timeout、compaction。
- 测试覆盖 queue、wait、error、persistence。
- README 能让学习者理解 agent loop 是运行系统，不是单次函数调用。

## 八、Unit 5 扩展计划：Tools Safety

### 教学目标

讲清楚 tools、skills、hooks、policy、sandbox 五层如何共同构成可扩展且可约束的能力系统。

这是最重要的扩展单元之一。

### 当前不足

- policy 太简单。
- 没有 approval flow。
- 没有 workspace-only 文件工具。
- 没有真实 `SKILL.md` 示例。
- 没有 prompt injection 案例。

### 需要新增的内容

#### 1. README 扩展

新增：

- 五层关系图：

```text
Skill discovery
  -> Prompt exposure
  -> Hook pipeline
  -> Tool policy
  -> Sandbox / workspace boundary
```

- system prompt safety vs hard enforcement 区别。
- allow/ask/deny 策略矩阵。
- sandbox host 类型：
  - sandbox
  - gateway
  - node

#### 2. 代码扩展

修改 `unit-5-tools-safety/tools-safety.js`：

- 增加 `loadSkillFromMarkdown()`。
- 增加 approval request flow。
- 增加 workspace-only file read/write tool。
- 增加 policy matrix。
- 增加 prompt injection 示例输入。
- 增加 hook 阻止调用的能力。

建议新增 API：

```js
loadSkillFromMarkdown(markdown)
createApprovalQueue()
resolvePolicyMatrix({ toolName, channel, chatType, model, sandboxMode })
createWorkspaceFileTool({ workspaceRoot })
assertWithinWorkspace(path, workspaceRoot)
runToolWithApproval({ tool, args, policy, approvals })
```

#### 3. fixtures

新增：

```text
fixtures/skills/calendar/SKILL.md
fixtures/skills/deploy/SKILL.md
fixtures/prompt-injection-message.txt
fixtures/policy-matrix.json
```

#### 4. 测试

新增 `tests/unit-5-tools-safety.test.js`：

- disabled skill 不加载。
- binary missing skill 不加载。
- `before_tool_call` 可以改写参数。
- hook 可以阻止危险参数。
- `ask` 生成 approval request。
- approve 后执行，reject 后拒绝。
- workspace-only 工具阻止 `../secret`。
- prompt injection 不能绕过 deny policy。

#### 5. 练习

- 增加 `browser.open` 工具策略。
- 实现 `after_tool_call` 结果清洗。
- 给不同 channel 配不同 policy。
- 实现 node host 工具路由。

### 验收标准

- Unit 5 能演示 allow、ask、deny、approval、workspace boundary。
- 测试覆盖安全边界。
- README 能解释为什么 prompt 约束不能替代 policy/sandbox。

## 九、Unit 6 扩展计划：Reply Delivery

### 教学目标

讲清楚 agent payload 如何可靠、幂等、按渠道格式投递给用户。

### 当前不足

- 只支持 text payload。
- 没有 chunking。
- 没有 transport failure/retry。
- 没有 typing/final event。
- 没有 group reply tag。

### 需要新增的内容

#### 1. README 扩展

新增：

- payload 类型：
  - text
  - reasoning
  - tool summary
  - error
  - silent
- reply shaping 原则：
  - 合并
  - 过滤
  - 抑制
  - 不重新决策
- channel 差异：
  - Telegram markdown
  - Slack thread
  - WebChat delta/final
  - group reply tag

#### 2. 代码扩展

修改 `unit-6-reply-delivery/reply-delivery.js`：

- 支持多 payload 类型。
- 支持 chunking。
- 支持 channel formatter。
- 支持 retry。
- 支持 dead-letter log。
- 支持 typing/final event 模拟。

建议新增 API：

```js
shapePayloads(payloads, options)
chunkMessage(text, maxLength)
formatForChannel(reply, channel)
createRetryingTransport(transport, { retries })
createDeadLetterLog()
emitTypingEvent({ channel, to })
```

#### 3. fixtures

新增：

```text
fixtures/long-reply.json
fixtures/no-reply.json
fixtures/tool-error-payload.json
fixtures/slack-thread-source.json
```

#### 4. 测试

新增 `tests/unit-6-reply-delivery.test.js`：

- `NO_REPLY` 被抑制。
- 长文本被 chunk。
- 同 idempotency key 不重复发送。
- transport 失败后重试。
- retry 失败进入 dead-letter。
- Slack source 保留 thread。

#### 5. 练习

- 增加 Discord formatter。
- 增加 markdown escape。
- 增加 group reply tag。
- 实现 delivery metrics。

### 验收标准

- Unit 6 能演示 success、NO_REPLY、duplicate、chunking、retry failure。
- 测试覆盖 shaping、dedupe、transport retry。
- README 能解释 delivery 是可靠性边界，不是 agent 决策层。

## 十、项目级测试计划

### 1. package.json scripts

新增：

```json
{
  "scripts": {
    "test": "node --test tests/*.test.js",
    "verify": "npm run all && npm test"
  }
}
```

### 2. 测试原则

- 测试行为，不测试内部实现细节。
- 每个 unit 至少 5 个测试。
- 失败路径必须有测试。
- 教学代码保持简单，但边界行为要真实。

### 3. 最小验收命令

```bash
npm run all
npm test
python3 ../../.codex/skills/code-speedrun/scripts/verify_speedrun.py .
```

## 十一、推荐实施顺序

### Phase 1：教学框架

先补全项目级文档和目录。

任务：

- 新增 `LESSON_PLAN.md`
- 新增 `GLOSSARY.md`
- 新增 `SOURCE_MAP.md`
- 新增 `DEBUG_GUIDE.md`
- 新增 `ARCHITECTURE.md`
- 新增 `fixtures/`
- 新增 `tests/`
- 更新 `package.json` scripts

验收：

- 文档能解释 6 课结构。
- `npm run all` 仍通过。

### Phase 2：扩展 Unit 3

优先扩展上下文系统，因为它最能体现 OpenClaw 的个人助理机制。

任务：

- workspace store
- bootstrap truncation
- memory ranking
- session history
- skills discovery
- prompt budget report
- Unit 3 tests

验收：

- Unit 3 至少展示 4 类上下文来源。
- 测试覆盖缺失、截断、排序、skill gating。

### Phase 3：扩展 Unit 4

扩展 agent loop 运行时。

任务：

- async submit/wait
- session queue
- stream subscribe
- wait timeout
- tool error
- session persistence
- compaction mock
- Unit 4 tests

验收：

- Unit 4 能演示 success、error、timeout、compaction。

### Phase 4：扩展 Unit 5

扩展工具安全。

任务：

- `SKILL.md` loader
- policy matrix
- approval queue
- workspace-only file tool
- hook block
- prompt injection case
- Unit 5 tests

验收：

- Unit 5 能演示 allow/ask/deny/approval/workspace boundary。

### Phase 5：扩展 Unit 2 和 Unit 6

补齐入口和出口。

任务：

- Unit 2 多入口 normalize
- Unit 2 connection validation
- Unit 6 payload shaping
- Unit 6 chunk/retry/dead-letter
- tests

验收：

- 至少 3 种入口、3 种 delivery 路径。

### Phase 6：扩展 Unit 1

最后回到 overall，把各单元增强能力串起来。

任务：

- 多场景 runner
- trace 输出
- failure path
- README 更新

验收：

- Unit 1 可以跑 Telegram、WebChat、tool denied、duplicate delivery 等场景。

## 十二、最终验收标准

项目完成后应满足：

- `npm run all` 通过。
- `npm test` 通过。
- speedrun 结构校验通过。
- 每个 unit README 都能独立支撑 60-90 分钟教学。
- 每个 unit 至少包含：
  - 机制图
  - 代码走读
  - 调试任务
  - 练习
  - 源码映射
  - 失败路径
- `LESSON_PLAN.md` 能串起完整课程。
- `SOURCE_MAP.md` 能帮助学习者从 speedrun 跳到真实 OpenClaw 源码。
- `DEBUG_GUIDE.md` 能指导学习者用断点观察数据流。

## 十三、优先级总结

最高优先级：

1. Unit 3: Session Context
2. Unit 4: Agent Loop
3. Unit 5: Tools Safety

中优先级：

4. Unit 2: Gateway Entry
5. Unit 6: Reply Delivery

最后整合：

6. Unit 1: Overall

原因：Unit 3、4、5 分别对应 OpenClaw 的上下文、运行时、工具安全，是理解 OpenClaw 原理机制的主干。Unit 2 和 Unit 6 是入口和出口。Unit 1 应在其他单元扩展后再更新，作为最终总览。
