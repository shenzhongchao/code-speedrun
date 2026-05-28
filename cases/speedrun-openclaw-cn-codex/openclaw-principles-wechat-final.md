# OpenClaw 架构解析：个人 AI 助理为什么需要运行时

很多 AI 助理的第一版，通常都是一个聊天框。

用户发来一句话，后端把历史消息和提示词拼起来，调用模型。如果模型要用工具，就在回调里执行工具，再把结果交给模型继续生成。

这个结构很适合 demo。

但一旦目标从“能聊天”变成“长期可用的个人助理”，问题会迅速变多：用户可能来自 Telegram、Slack、Discord、WebChat、CLI 或移动设备；同一个用户可能有多个会话；历史和记忆会不断增长；工具会从读文件扩展到执行命令、发消息、控制设备；渠道会超时、重试、重复投递；模型也可能被 prompt injection 诱导去请求危险操作。

这时，系统真正需要的不是更长的 prompt，而是一套 assistant runtime。

OpenClaw 值得拆解的地方就在这里。它不是把大模型直接接到聊天入口上，而是把个人助理拆成几层边界：

```text
真实世界输入
  -> Gateway / envelope
  -> session context
  -> agent loop
  -> model + tools
  -> reply delivery
```

这篇文章沿着“一条消息的旅程”解释这套结构。文中会区分两类内容：官方文档已经明确描述的机制，以及基于这些机制能得到的工程推论。

## 1. Gateway：先把真实世界挡在运行时外面

OpenClaw 官方文档把 Gateway 描述成一个长期运行的中心进程。它负责维护 WhatsApp、Telegram、Slack、Discord、Signal、iMessage、WebChat 等消息面，也给 macOS app、CLI、Web UI、自动化脚本和节点设备提供 WebSocket API。

这层的关键价值不是“多接几个渠道”，而是把渠道差异收敛成运行时协议。

Telegram 有 message id、chat id、sender。Slack 有 workspace、channel、thread。WebChat 来自浏览器。节点设备还会声明自己的 role、caps、commands 和 permissions。如果让 agent loop 直接面对这些原始事件，核心逻辑很快会被渠道细节污染。

所以入口层需要形成一个统一 envelope。概念上可以理解成：

```js
{
  runId: "tg-42",
  method: "agent",
  text: "明早提醒我看部署状态",
  sessionKey: "agent:main:telegram:@user",
  idempotencyKey: "telegram:personal:42",
  source: {
    channel: "telegram",
    account: "personal",
    from: "@user",
    chatType: "direct"
  }
}
```

这里有几个字段特别重要。

`runId` 是一次运行的观测单位。后续 lifecycle、assistant、tool 等事件都可以围绕它关联。

`sessionKey` 是上下文和并发控制单位。它决定这条消息属于哪个 session，也决定同一个 session 的 run 是否要排队。

`source` 是投递恢复单位。最后回复应该回到哪个渠道、哪个 thread、哪个用户，不能靠模型猜。

`idempotencyKey` 是副作用保护单位。官方 Gateway 文档明确要求 side-effecting 方法，比如 `send` 和 `agent`，使用幂等键以支持安全重试，服务端会保留短期 dedupe cache。没有这层保护，渠道重复投递一次消息，可能就会重复发通知、重复创建事项或重复执行动作。

Gateway 解决的不是推理问题，而是边界问题：外部世界可以混乱，但进入运行时之前必须变成可验证、可追踪、可去重的协议。

## 2. Context：模型回答前，先决定它看见什么

普通聊天机器人常把上下文理解成“最近几轮聊天历史”。个人助理不能这么窄。

当用户说“明早提醒我看部署状态”时，系统至少要回答几个问题：

- 当前是哪个 agent？
- 工作目录在哪里？
- 用户偏好和身份信息是什么？
- 当前会话历史有哪些？
- 哪些 workspace 文件应该注入？
- 哪些 skills 可见？
- 当前工具策略和 sandbox 状态是什么？
- 这次运行的 prompt 预算够不够？

OpenClaw 官方 Agent Runtime 文档明确说，它使用 `agents.defaults.workspace` 作为 agent 的工作目录；在首次或每次运行时，会把 workspace 中一组用户可编辑文件注入上下文。Agent Runtime 文档列出的基础文件包括：

```text
AGENTS.md
SOUL.md
TOOLS.md
BOOTSTRAP.md
IDENTITY.md
USER.md
```

Context 和 System Prompt 文档还会进一步提到运行时可能注入或报告的文件，例如：

```text
HEARTBEAT.md
MEMORY.md
```

这里需要纠正一个常见误解：context 不等于 memory。

官方 Context 文档的定义很清楚：context 是本次 run 真正发送给模型的全部内容，包括 system prompt、会话历史、工具调用和工具结果、附件、压缩摘要等；memory 可以存储在磁盘上，之后再被重新加载。也就是说，memory 是长期信息，context 是当前窗口。

这一区分非常关键。

如果把所有长期记忆、所有历史、所有工具说明都一次性塞进 prompt，系统会变慢、变贵，也更容易让旧信息干扰当前任务。OpenClaw 的实际做法是给上下文建立预算意识：workspace 文件会被截断，缺失文件会注入 marker，`/context list` 和 `/context detail` 可以查看每类内容占用了多少上下文。

Skills 也不是把完整说明全塞进去。官方 System Prompt 文档说明，OpenClaw 会把可用 skill 的 name、description、location 以紧凑列表放入 prompt，模型需要时再用 `read` 加载对应的 `SKILL.md`。

这背后的原则是：模型应该知道“有哪些能力可请求”，但不应该在每次运行时背上所有能力的完整说明。

## 3. System Prompt：它是运行时产物，不是固定文案

很多系统把 system prompt 当作一段手写模板。OpenClaw 不是这样。

官方文档明确写到，OpenClaw 为每次 agent run 构造自有 system prompt，不使用底层 pi-coding-agent 的默认 prompt。这个 prompt 会包含工具指导、执行偏好、安全提示、skills 列表、workspace、文档路径、sandbox 状态、当前时间、reply tags、runtime metadata 等。

这里有一个重要边界：system prompt 是软约束，不是权限系统。

它可以影响模型行为，但不能保证模型永远不犯错。用户可以发起 prompt injection，模型也可能误判上下文。所以真正的安全不能靠“请不要做危险事”这类提示词，而要靠工具策略、审批、sandbox、渠道 allowlist 和 Gateway 的连接认证来执行。

工程上可以这样理解：

```text
system prompt 负责告诉模型应该怎么行动
tool policy 和 sandbox 负责决定它能不能行动
```

这也是个人助理和普通聊天机器人的分水岭。聊天机器人只要生成文本；个人助理会行动，所以必须把“行动权限”从模型手里拿出来。

## 4. Agent Loop：一次运行不是一次模型调用

上下文准备好之后，才进入 agent loop。

官方 Agent Loop 文档把它定义为一次真实的 agent run：intake、context assembly、model inference、tool execution、streaming replies、persistence。也就是说，它不是 `model.generate()` 的薄封装，而是把消息变成行动和最终回复的权威路径。

OpenClaw 的入口也不是简单阻塞到最终文本。官方文档描述的流程是：

```text
agent(request) -> { runId, acceptedAt }
agent.wait(runId) -> ok / error / timeout
event stream -> lifecycle / assistant / tool
```

`agent` RPC 会校验参数、解析 session、持久化 session metadata，然后立即返回 `runId` 和 `acceptedAt`。真正的执行在后面继续跑。调用方可以用 `agent.wait` 等待 lifecycle end/error，也可以订阅事件流。

这个设计解决了一个实际问题：一次个人助理运行可能持续很久。它可能先流式输出一段文字，再调用工具，再等待工具结果，再继续调用模型，最后写入会话历史。如果入口请求一直阻塞，系统会很脆弱；如果只暴露最终字符串，又无法观察中间状态。

所以 OpenClaw 把运行过程事件化：

```text
lifecycle: start / end / error
assistant: text deltas
tool: tool start / update / end
```

这样前端能显示实时进度，日志能追踪失败，调试器能看到工具参数，调用方也不会把某个 tool end 误判成整个 run 完成。

## 5. Queue：同一个 session 必须有顺序

个人助理的另一个难点是并发。

用户连续发两句话：

```text
帮我改部署脚本
顺便把刚才的改动提交
```

这两句话有明显顺序关系。如果它们并发执行，就可能同时读写同一份 session transcript、同一个 workspace 文件、同一段 memory 或同一个工具状态。

OpenClaw 的 Command Queue 文档明确说，`runEmbeddedPiAgent` 会按 session key 入队，保证一个 session 同时只有一个 active run；同时每个 session run 还会进入全局 lane，以限制整体并发。这样既避免同一会话内部竞态，也允许不同 session 在全局上有限并行。

更细一点，OpenClaw 的消息队列还支持 `steer`、`followup`、`collect` 等模式。官方 Command Queue 文档当前写明默认模式是 `collect`：短时间内到来的多条消息会被合并成后续一个 agent turn。`steer` 则用于在可行时把新消息注入当前 run，`followup` 用于等当前 run 结束后再开启下一轮。

这说明 OpenClaw 处理的不是抽象的“请求并发”，而是更贴近聊天语义的“会话顺序”。对于个人助理，这比普通 HTTP 并发控制更重要。

## 6. Model：模型是推理组件，不是权限中心

OpenClaw 可以接入不同模型，但模型在架构中的位置应该保持稳定：它负责生成回复、选择下一步、提出工具调用意图。

注意是“意图”，不是“权限”。

一个模型可以生成：

```text
我想调用 exec 运行某个命令
我想调用 message 发送一条消息
我想读取 workspace 中的某个文件
```

但系统不能因为模型这样说就直接执行。

官方插件 hooks 文档说明，`before_tool_call` 可以重写参数、阻止执行或要求审批；`after_tool_call` 可以观察结果、错误和耗时；`message_sending` 可以改写或取消发送。Exec Approvals 文档也强调，sandboxed agent 要在真实 host 上执行命令时，需要 policy、allowlist 和可选用户审批共同通过。

这才是安全边界。

Prompt 可以提醒模型不要越权，但真正阻止越权的是这些机制：

- tool policy 决定工具是否可用；
- plugin hook 可以拦截、改写或要求审批；
- exec approvals 把 shell 命令放进 allowlist/ask/deny 流程；
- sandbox 限制文件系统和 host 访问；
- channel allowlist 限制谁可以触发敏感能力。

这层设计的核心原则是：

```text
Skills 让模型知道可以请求什么
Policy / approval / sandbox 决定到底能不能做
```

## 7. Delivery：payload 还不是最终消息

Agent Loop 结束后，系统拿到的是 payload，不是最终渠道消息。

最终要发到 Telegram、Slack、Discord 或 WebChat 之前，还要处理一批和模型无关的事情：长文本如何分块，Markdown 是否需要转义，Slack thread 是否要保留，Telegram preview 是否要编辑，媒体是否重复发送，失败是否重试，`NO_REPLY` 是否要抑制。

OpenClaw 的 Streaming and Chunking 文档把这里拆得很细：它区分 channel block streaming 和 preview streaming；长文本 chunk 会优先按段落、换行、句子、空白切分，代码块不会随意切坏；如果 streaming 阶段已经发过某个媒体，final payload 中重复的媒体会被去重。

Retry Policy 文档也强调，重试是按单个 HTTP request 做，而不是重跑整个多步骤流程；目标是保持顺序，并避免重复非幂等操作。

这说明 reply delivery 是独立边界。它不应该重新调用模型，也不应该重新解释 agent 结果。它的职责是把已经生成的 payload 可靠、合规、去重地送回正确渠道。

## 8. OpenClaw 真正解决的是什么

把这些层连起来看，OpenClaw 解决的不是“如何调用大模型”，而是“如何让大模型长期、安全、可观察地进入用户生活和工作环境”。

```text
Gateway 解决消息怎么进来、怎么认证、怎么去重
Context 解决模型本次到底看见什么
System Prompt 解决运行时规则如何注入
Agent Loop 解决一次运行如何执行和观察
Queue 解决同一 session 的顺序一致性
Tools Safety 解决模型意图如何变成受控行动
Reply Delivery 解决结果如何可靠回到用户
```

这些边界会增加工程复杂度，但它们换来几个长期收益。

第一，模型可以替换，而入口、上下文、工具和投递边界不必重写。

第二，渠道可以新增，而 agent loop 不必被 Slack thread、Telegram preview、Discord retry 之类细节污染。

第三，工具可以变强，但真实权限不会直接交给模型。

第四，运行可以被观察、等待、取消、排队、恢复，而不是只剩一段最终文本。

第五，长期记忆、workspace 文件和会话历史可以被预算管理，而不是无限塞进 prompt。

如果说普通聊天机器人关心的是“用户说了什么，模型回什么”，那么个人 AI 助理必须关心更多：

这句话来自哪里，属于哪个 session，模型看见了什么上下文，能安全使用哪些工具，运行过程中发生了什么，最后结果如何可靠回到用户。

大模型提供推理能力。

但让个人 AI 助理真正可用、可控、可长期演进的，是模型之外的运行时系统。

OpenClaw 的核心，正是这套系统。

## 参考资料

- OpenClaw Gateway architecture: https://docs.openclaw.ai/concepts/architecture
- OpenClaw Agent runtime: https://docs.openclaw.ai/concepts/agent
- OpenClaw Agent Loop: https://docs.openclaw.ai/concepts/agent-loop
- OpenClaw Context: https://docs.openclaw.ai/concepts/context
- OpenClaw System Prompt: https://docs.openclaw.ai/concepts/system-prompt
- OpenClaw Command Queue: https://docs.openclaw.ai/concepts/queue
- OpenClaw Streaming and Chunking: https://docs.openclaw.ai/concepts/streaming
- OpenClaw Retry Policy: https://docs.openclaw.ai/concepts/retry
- OpenClaw Plugin Hooks: https://docs.openclaw.ai/plugins/hooks
- OpenClaw Exec Approvals: https://docs.openclaw.ai/tools/exec-approvals
