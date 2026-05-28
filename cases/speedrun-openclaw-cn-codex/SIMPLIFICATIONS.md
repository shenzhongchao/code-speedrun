# 简化说明

这里列出每个单元相对原始 OpenClaw 做了哪些简化或 stub。
这些简化让 speedrun 保持可运行，但不掩盖 OpenClaw 的核心技术边界。

## Unit 1: Overall

- [ ] 只跑一个 Telegram direct message；真实 OpenClaw 同时支持 CLI、WebChat、多渠道、多 node 和自动化入口。
- [ ] 默认使用本地规则模拟模型输出；设置 `.env` 后可用 OpenAI-compatible API 或 Pi Agent SDK 跑真实模型，但仍未覆盖生产级 provider、auth profile、usage、retry 和 compaction。
- [ ] workspace、memory 和 skills 都是内存对象；真实实现会读写 `~/.openclaw` 下的 agent workspace、sessions 和 skills 目录。

## Unit 2: Gateway Entry

- [ ] WebSocket 握手、pairing、device signature、gateway token 和 TypeBox schema 校验被简化成普通对象。
- [ ] Channel plugin 只保留 Telegram 的 normalize 示例；真实项目有大量 provider、账号管理、健康状态和重连逻辑。
- [ ] `agent` 请求只保留 runId、sessionKey、idempotencyKey、source 和 text；真实请求还有 attachments、model/thinking/verbose、stream options 和 provenance。

## Unit 3: Session Context

- [ ] Bootstrap 文件从内存读取；真实 OpenClaw 会解析 workspace 路径、处理缺失文件、截断预算和 `agent:bootstrap` hooks。
- [ ] Memory search 是关键词匹配；真实代码有更完整的 memory 文件布局、工具入口和上下文预算策略。
- [ ] System prompt 只保留关键段落；真实 prompt 包含 tooling、安全、workspace、docs、sandbox、时间、reply tags、heartbeats、runtime 等固定 section。
- [ ] Skills 只是一组对象；真实 OpenClaw 会从 bundled、managed、workspace 三类来源发现并按 config/env/binary presence 过滤。

## Unit 4: Agent Loop

- [ ] `runEmbeddedAgent()` 默认不调用真实模型；真实 LLM 模式已覆盖 Chat Completions/tool_calls 往返，但没有实现 token streaming、usage accounting 和 provider fallback。
- [ ] Session lane 只用 Promise chain；真实运行时还有全局/会话队列、abort、timeout、session manager、history sanitization 和 compaction。
- [ ] Stream 事件只包括 lifecycle/tool/assistant 的核心形状；真实事件包含 token/block streaming、reasoning、tool update、usage、error fallback 等。
- [ ] `agent.wait` 没有超时参数；真实 wait 只等待 run lifecycle，不会停止正在运行的 agent。

## Unit 5: Tools Safety

- [ ] Tool policy 只实现 allow/ask/deny 三种结果；真实配置有 provider/model/channel/session 级覆盖和更多工具族。
- [ ] Sandbox 只用 `sandboxMode` 字符串表示；真实 OpenClaw 会准备 Docker workspace、browser sandbox、node/gateway/sandbox exec host 和 workspace-only 文件边界。
- [ ] Hook runner 只实现 `before_tool_call`/`after_tool_call`；真实插件 hooks 还覆盖 prompt build、agent lifecycle、message received/sending/sent、compaction 等。
- [ ] Skills install gating 只检查 binary 名称；真实 skills 还支持 metadata、installer specs、managed/workspace override 和 UI gating。

## Unit 6: Reply Delivery

- [ ] 只处理 text payload；真实 OpenClaw 还处理 block streaming、typing、reasoning visibility、tool summary、TTS、media 和 channel chunking。
- [ ] Dedupe 是内存 Set；真实实现要跨重试和进程生命周期处理 side effect 幂等。
- [ ] Transport 只模拟 Telegram/WebChat；真实项目有多渠道格式差异、reply tags、group activation 和 failure retry。
