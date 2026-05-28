# OpenClaw 架构解析：为什么个人 AI 助理不只是一个聊天框

如果你要做一个 AI 应用，最自然的起点通常是聊天框。

用户输入一句话，模型返回一段文本。这个模式简单、直接，也足够展示大模型的能力。

但当目标从“聊天机器人”变成“个人 AI 助理”，聊天框很快就不够了。

一个真正的个人助理不是只会回答问题。它要长期存在，要记住用户偏好，要能出现在 Telegram、Slack、WebChat、桌面端和移动端里，要能读写本地工作区，要能调用工具，要能处理失败和重试，还要能在关键操作前受到安全约束。

这时，核心问题就不再是“怎么调用模型”，而是：

如何把大模型放进一套可控、可观察、可扩展的个人助理运行时里。

OpenClaw 的架构价值就在这里。

它看起来有很多入口和工具，但真正重要的是背后的运行时设计。一条消息从真实世界进入 OpenClaw，到最后变成回复，中间会穿过几层清晰的边界：

```text
入口消息
  -> 统一请求
  -> 会话与上下文
  -> 模型运行循环
  -> 工具安全边界
  -> 回复投递
```

这篇文章就沿着“一条消息的旅程”，解释 OpenClaw 为什么这样设计。

## 一、入口层：先把真实世界的不确定性挡在外面

真实世界的消息入口非常不统一。

Telegram 有 message id、chat id、sender。Slack 有 workspace、channel、thread。WebChat 来自浏览器控制台。CLI 可能只是一个本地命令。移动端节点还会带设备状态和权限信息。

如果让后面的 agent runtime 直接面对这些差异，系统会很快失控。

所以 OpenClaw 的第一层，是把不同入口规范化成统一请求。

这个请求通常会包含：

```js
{
  runId: "tg-42",
  method: "agent",
  text: "明早提醒我看部署状态",
  sessionKey: "agent:main:telegram:@user",
  idempotencyKey: "telegram:personal:42",
  source: {
    kind: "channel",
    channel: "telegram",
    account: "personal",
    from: "@user",
    to: "@user",
    chatType: "direct"
  }
}
```

这里最关键的是三个字段。

`runId` 标识一次运行。

`sessionKey` 决定这条消息属于哪个 agent、哪个会话。

`source` 记录消息从哪里来，最后应该回到哪里。

还有一个很容易被忽视但非常重要的字段：`idempotencyKey`。真实渠道经常会重试、重复投递或网络抖动。如果没有幂等键，一个“创建提醒”的操作可能被重复执行。

入口层的职责不是思考答案，而是把混乱的真实世界整理成运行时能理解的 envelope。

这层边界让 OpenClaw 后面的核心逻辑不用关心 Telegram 和 Slack 的细节，也不会被渠道差异污染。

## 二、上下文层：模型回答前，先决定“它是谁”

很多 AI 应用把上下文理解成聊天历史。

对个人 AI 助理来说，这太窄了。

当用户说“明早提醒我看部署状态”时，一个长期运行的助理需要知道：

- 当前是哪个 agent？
- 这个 agent 的 workspace 在哪里？
- 用户偏好是什么？
- 过去和“部署状态”有关的记忆是什么？
- 当前会话之前发生过什么？
- 哪些技能和工具可用？
- 哪些文件应该进入系统提示词？

这些信息不会自然出现在模型里，必须由系统在运行前组装。

OpenClaw 会根据 `sessionKey` 找到 agent scope，再从 workspace、bootstrap 文件、记忆、会话历史和技能注册表中构造上下文。

workspace 可以理解成个人助理的长期环境。它可能包含：

```text
AGENTS.md
SOUL.md
USER.md
MEMORY.md
TOOLS.md
skills/
sessions/
memory/
```

但这里有一个重要取舍：不能把所有东西都塞进 prompt。

长期记忆越多，越需要筛选。会话历史越长，越需要压缩。workspace 文件越复杂，越需要预算控制。

更合理的策略是：

- 稳定身份和偏好作为 bootstrap 注入
- 当前问题相关的记忆通过搜索召回
- 当前 session 的近期历史进入 transcript
- 大文件和完整档案通过工具按需读取
- 所有进入 prompt 的内容都受 budget 限制

这一步决定了模型看到的世界。

很多所谓“模型没有理解我”的问题，根源其实不在模型本身，而在上下文层：该召回的记忆没有召回，旧历史挤掉了当前任务，或者工具暴露得不对。

个人 AI 助理的能力，很大程度来自上下文工程。

## 三、运行层：Agent Loop 不是一次模型调用

上下文准备好之后，才进入 agent loop。

如果把 agent loop 理解成一次 `model.generate()`，就会低估它的复杂度。

一次真实的助理运行更像这样：

```text
accepted
  -> queued
  -> started
  -> model inference
  -> assistant streaming
  -> tool call
  -> tool result
  -> model continuation
  -> persistence
  -> ended / error
```

这里有三个关键设计。

第一，提交任务和等待结果要分离。

用户发来消息后，系统可以先接受这次运行，返回一个 `runId`。调用方可以订阅事件，也可以等待这个 `runId` 结束。

这比长时间阻塞一个请求更稳。因为一次助理运行可能会持续很久，中间可能调用工具、等待网络、写入历史、触发压缩，也可能失败。

第二，同一个 session 要串行。

如果用户连续发两句话：

```text
帮我改部署脚本
顺便把刚才的改动提交
```

这两句话在语义上有顺序关系。如果它们并发执行，可能同时读写同一份文件、同一段会话历史或同一个工具状态。

所以 OpenClaw 需要按 session 排队。同一个 session 串行，不同 session 可以并行。

第三，运行过程要事件化。

一个 agent run 不只是最终字符串，它会持续产生事件：

- lifecycle：accepted、queued、start、end、error
- assistant：文本增量
- tool：工具开始、结束、失败

这些事件让系统可观察。前端可以显示流式回复，调试器可以看到工具参数，日志系统可以追踪错误，调用方可以等待真正的 lifecycle end。

这就是运行时和普通模型接口的区别。

## 四、LLM 是推理组件，不是权限中心

OpenClaw 可以接入真正的大模型，比如通过 OpenAI-compatible API。

但模型在架构中的位置很关键。

它应该位于 agent loop 之内，负责生成回复和提出工具调用意图：

```text
context transcript
  -> LLM
  -> assistant delta
  -> tool_calls
  -> guarded tool execution
  -> tool result
  -> LLM
  -> final payload
```

注意这里的词：工具调用意图。

模型可以说“我想调用 calendar.create 创建提醒”，但它不能直接执行这个工具。

真正执行前，系统必须检查：

- 工具是否存在
- 当前渠道是否允许
- 是否需要审批
- 参数是否安全
- 文件路径是否越界
- sandbox 是否允许

这就是个人助理安全的核心边界。

Prompt 可以提醒模型不要做危险行为，但 prompt 不是权限系统。模型可能被 prompt injection 诱导，也可能误判上下文。

真正的安全必须由系统侧的 policy、approval 和 sandbox 执行。

所以，LLM 是 OpenClaw 的推理组件，不是 OpenClaw 的权限中心。

## 五、工具层：能力越强，边界越要硬

个人助理的价值来自工具。

它可以创建提醒、读写文件、查询记忆、调用浏览器、执行命令、连接设备节点、访问第三方服务。

但工具越强，风险越高。

OpenClaw 的工具系统不是简单地把所有工具暴露给模型，而是分成几层：

```text
Skill discovery
  -> Prompt exposure
  -> Hook pipeline
  -> Tool policy
  -> Sandbox boundary
```

Skill 告诉模型“有什么能力、什么时候使用、怎么使用”。

Hook 可以在工具调用前审计或改写参数，也可以在工具调用后清洗结果。

Policy 决定某个工具调用是 allow、ask 还是 deny。

Sandbox 提供最后的硬边界。比如文件工具只能访问 workspace，不能通过 `../secret` 逃逸；某些 host exec 工具在 sandbox 模式下必须拒绝。

这里的核心原则是：

Skills 让模型知道可以请求什么，policy 和 sandbox 决定到底能不能做。

这样设计后，工具能力可以不断扩展，但系统不会把真实权限直接交给模型。

## 六、投递层：最后一公里也不能塞回模型

Agent Loop 结束后，系统得到的是 payload。

payload 不是最终消息。

最终发送到 Telegram、Slack 或 WebChat 之前，还要处理很多渠道细节：

- 是否是 `NO_REPLY`
- 是否需要合并多段 payload
- 长文本是否需要 chunk
- Slack thread 是否要保留
- Telegram markdown 是否要转义
- transport 失败是否要重试
- 重试失败是否进入 dead-letter
- 同一个 idempotency key 是否已经发送过

这些问题不应该交给模型，也不应该塞进 agent loop。

它们属于 reply delivery。

Reply Delivery 的职责是可靠投递，而不是重新思考答案。

这层独立出来后，架构会清楚很多：模型负责生成，工具层负责执行边界，投递层负责渠道适配和可靠性。

## 七、OpenClaw 真正解决的是什么

把这些层连起来看，OpenClaw 解决的不是“如何做一个聊天框”，而是如何让个人 AI 助理长期可靠地运行。

```text
Gateway 解决消息怎么进来
Context 解决助理是谁、知道什么
Agent Loop 解决一次运行如何执行和观察
LLM 负责生成和提出工具意图
Tools Safety 负责能力扩展和安全边界
Reply Delivery 解决结果如何可靠回到用户
```

这个拆法带来一个很重要的结果：每一层都可以独立演进。

你可以换模型，但不改入口和投递。  
你可以新增渠道，但不改 agent loop。  
你可以扩展工具，但不绕过 policy 和 sandbox。  
你可以调整记忆策略，但不污染回复投递。  

这就是运行时架构的价值。

## 结语

OpenClaw 最值得学习的地方，不是它接入了多少渠道，也不是它默认使用哪个模型。

真正重要的是，它把个人 AI 助理拆成了一套可控的工程系统：

```text
入口统一
上下文明确
运行可观察
工具可约束
投递可可靠
```

普通聊天机器人关心“用户说了什么，模型回什么”。

个人 AI 助理必须关心更多：

这句话属于哪个长期存在的助理，它在什么上下文里行动，能安全使用哪些工具，运行过程如何被观察，结果如何可靠回到用户。

大模型提供了推理能力。

但让个人 AI 助理真正可用、可控、可长期运行的，是模型之外的这套架构。
