# Simplifications

What was simplified or stubbed in each unit compared to the original codebase.
Use this checklist to progressively restore real implementations.

> **Tip**: 你可以让编码助手按条目逐个还原，例如：
> “把 unit-4 中的简化循环还原为 nanobot/agent/loop.py 的真实行为，并保留当前教学注释。”

## Unit 1: Overall
- [ ] `unit-1-overall/index.py` — 用单文件装配代替真实 CLI 子命令体系，真实入口在 `nanobot/cli/commands.py`
- [ ] Heartbeat 使用本地规则判定 provider，真实实现通过 LLM tool call 判定在 `nanobot/heartbeat/service.py`
- [ ] Cron 使用内存任务队列，真实实现带持久化 JSON store 在 `nanobot/cron/service.py`
- [ ] 省略 ChannelManager 多平台路由细节，真实逻辑在 `nanobot/channels/manager.py`

## Unit 2: 消息总线与会话归档
- [ ] `SessionStore` 仅内存存储，真实实现是 JSONL 文件与缓存并存于 `nanobot/session/manager.py`
- [ ] 忽略 `metadata/media/session_key_override` 的完整字段处理，真实结构在 `nanobot/bus/events.py`
- [ ] 未实现历史裁剪/consolidation 偏移，真实逻辑在 `nanobot/session/manager.py` 与 `nanobot/agent/memory.py`

## Unit 3: 提示词上下文组装
- [ ] 不从工作区读取真实 `AGENTS.md/SOUL.md/TOOLS.md` 文件，真实加载逻辑在 `nanobot/agent/context.py`
- [ ] Skills 只用静态摘要，不做可用性检查与 frontmatter 解析，真实逻辑在 `nanobot/agent/skills.py`
- [ ] Memory 仅字符串注入，不含 consolidate 回写流程，真实逻辑在 `nanobot/agent/memory.py`

## Unit 4: Agent Loop 工具执行循环
- [ ] 未实现 `/new`、`/help`、`/stop` 命令和任务取消管理，真实逻辑在 `nanobot/agent/loop.py`
- [ ] 未接入 MCP server 生命周期，真实逻辑在 `nanobot/agent/loop.py` 与 `nanobot/agent/tools/mcp.py`
- [ ] 省略 progress/tool_hint 向外通道的流式回传，真实逻辑在 `nanobot/agent/loop.py`
- [ ] 未实现 memory consolidation 触发条件与异步锁，真实逻辑在 `nanobot/agent/loop.py`

## Unit 5: 定时任务与心跳唤醒
- [ ] Cron 仅支持固定间隔，真实实现支持 `at/every/cron(tz)` 在 `nanobot/cron/service.py`
- [ ] 未实现 cron job 状态字段（last_status/last_error/delete_after_run），真实逻辑在 `nanobot/cron/types.py` 与 `nanobot/cron/service.py`
- [ ] Heartbeat 判定规则基于 markdown checkbox，真实实现通过 provider + 虚拟 heartbeat 工具在 `nanobot/heartbeat/service.py`

## Unit 6: Provider 抽象与工具协议
- [ ] Provider 仅 Mock，不含 LiteLLM 多厂商适配，真实实现在 `nanobot/providers/litellm_provider.py`
- [ ] 未实现 provider registry 匹配与 gateway 检测，真实逻辑在 `nanobot/providers/registry.py` 与 `nanobot/config/schema.py`
- [ ] ToolRegistry 省略参数 schema 校验细节，真实逻辑在 `nanobot/agent/tools/base.py` 与 `nanobot/agent/tools/registry.py`
- [ ] 仅保留 `list_dir` 演示工具，真实工具集在 `nanobot/agent/tools/`
