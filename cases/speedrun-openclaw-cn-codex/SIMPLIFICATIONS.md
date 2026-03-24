# 简化说明

这里列出每个单元相对原始代码库做了哪些简化或 stub。
你可以把它当成逐步恢复真实实现的清单。

> **提示**: 你可以让 coding agent 直接对照原仓库恢复任意一项，例如：
> “参考 ../openclaw/src/gateway/server-methods/chat.ts，把 unit-2 的真实 gateway auth 处理补回来”

## Unit 1: Overall

- [ ] Gateway 启动使用的是普通对象配置，而不是 `loadConfig()` 加完整启动校验（`src/gateway/server.impl.ts`, `src/config/config.ts`）
- [ ] 这里只接了一种内建 channel plugin；真实 OpenClaw 会动态加载大量 provider（`src/channels/plugins/`, `src/gateway/server-channels.ts`）
- [ ] 回复生成是规则文本，不是真实的模型驱动 agent 执行（`src/auto-reply/reply.ts`, `src/agents/`）
- [ ] 去掉了 transcript 持久化、中止控制和 tool event（`src/gateway/server-methods/chat.ts`, `src/gateway/chat-abort.ts`）

## Unit 2: Gateway Entry

- [ ] CLI 解析被缩减为一个命令 token 加 `--port`；真实 OpenClaw 还有 route-first parsing、lazy command registration 和 profile（`src/entry.ts`, `src/cli/run-main.ts`, `src/cli/program/`）
- [ ] 省略了 runtime guard、compile cache 初始化和进程 respawn 逻辑（`src/entry.ts`, `src/openclaw.mjs`）
- [ ] Gateway chat context 只保留了 speedrun 需要的字段；真实 context 还包含附件、provenance、能力信息和 auth 数据（`src/gateway/server-methods/chat.ts`）

## Unit 3: Channel Docking

- [ ] Plugin registry 是本地内存数据，不是真实的 plugin runtime registry（`src/channels/plugins/index.ts`, `src/plugins/runtime/index.ts`）
- [ ] Channel 启动只记录健康 runtime，没有后台任务与重启退避（`src/gateway/server-channels.ts`）
- [ ] Provider 规范化逻辑写死成一个 Telegram 形状的演示事件（`src/telegram/`, `src/channels/plugins/`）

## Unit 4: Session Routing

- [ ] Session key 逻辑只覆盖 direct 和 group；真实 OpenClaw 还支持 threads、ACP、cron 和 subagents（`src/routing/session-key.ts`, `src/sessions/session-key-utils.ts`）
- [ ] Agent 选择只检查显式 agent 或默认 agent（`src/agents/agent-scope.ts`）
- [ ] Send policy 规则只做 channel/chat-type 匹配，不是完整的配置驱动匹配器（`src/sessions/send-policy.ts`）

## Unit 5: Reply Dispatch

- [ ] Dedupe 用的是内存 `Set`，而不是更完整的 inbound dedupe 机制（`src/auto-reply/reply/inbound-dedupe.ts`, `src/auto-reply/reply/dispatch-from-config.ts`）
- [ ] Dispatcher 只处理最终文本 payload；streaming、typing、tool result 和 TTS 都省略了（`src/auto-reply/reply/reply-dispatcher.ts`, `src/tts/tts.ts`）
- [ ] 回复生成是同步本地规则；真实 OpenClaw 还会展开命令处理、模型选择、hooks 和 route-reply（`src/auto-reply/reply/`, `src/hooks/`）
