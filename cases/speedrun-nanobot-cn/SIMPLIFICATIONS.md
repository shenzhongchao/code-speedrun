# 简化清单

与原始 nanobot 代码库相比，每个单元做了哪些简化。
可以作为逐步还原真实实现的扩展路线图。

> **提示**：你可以让编码 Agent（Claude Code、Cursor 等）帮你还原任意一项。
> 指向原始项目和本 speedrun，例如：
> "参考 ../nanobot/nanobot/agent/loop.py，在 unit-1 中还原真实的 [功能]"

## Unit 1: 全局总览
- [ ] `AgentLoop` — 简化为同步处理，真实版本支持并发消息处理（`asyncio.create_task`）和全局处理锁（`nanobot/agent/loop.py`）
- [ ] `/stop` 命令 — 未实现，真实版本支持取消正在执行的任务和子代理（`nanobot/agent/loop.py:_handle_stop`）
- [ ] `/new` 命令 — 未实现，真实版本支持归档记忆后清空会话（`nanobot/agent/loop.py:_process_message`）
- [ ] 进度推送 — 未实现，真实版本在工具调用时向渠道推送中间状态（`_bus_progress`）
- [ ] 工具结果截断 — 未实现，真实版本将超过 500 字符的工具结果截断后存储（`_save_turn`）
- [ ] MCP 服务器连接 — 未实现，真实版本支持连接外部 MCP 服务器并注册其工具（`nanobot/agent/tools/mcp.py`）
- [ ] 子代理系统 — 未实现，真实版本支持后台生成子代理执行长任务（`nanobot/agent/subagent.py`）
- [ ] `<think>` 标签清理 — 未实现，真实版本会移除某些模型嵌入的思维链标签（`_strip_think`）

## Unit 2: 消息总线
- [ ] 渠道管理器 — 未实现，真实版本有 `ChannelManager` 管理 10+ 聊天平台（`nanobot/channels/manager.py`）
- [ ] 各渠道实现 — 未实现 Telegram、Discord、WhatsApp、飞书、钉钉、Slack、Email、QQ、Matrix、Mochat（`nanobot/channels/`）
- [ ] WhatsApp Bridge — 未实现 Node.js WebSocket 桥接（`bridge/`）
- [ ] 访问控制 — 未实现 `allowFrom` 白名单机制（`nanobot/channels/base.py:is_allowed`）
- [ ] `session_key_override` — 未实现线程级会话隔离

## Unit 3: 工具系统
- [ ] WriteFileTool / EditFileTool / ListDirTool — 未实现，真实版本有完整的文件操作工具集（`nanobot/agent/tools/filesystem.py`）
- [ ] WebSearchTool / WebFetchTool — 未实现，真实版本集成 Brave Search API 和 Readability 解析（`nanobot/agent/tools/web.py`）
- [ ] SpawnTool — 未实现，真实版本支持生成后台子代理（`nanobot/agent/tools/spawn.py`）
- [ ] CronTool — 未实现，真实版本让 Agent 自己管理定时任务（`nanobot/agent/tools/cron.py`）
- [ ] MessageTool — 未实现，真实版本支持跨渠道消息发送（`nanobot/agent/tools/message.py`）
- [ ] MCP 工具包装器 — 未实现，真实版本将 MCP 服务器的工具包装为原生工具（`nanobot/agent/tools/mcp.py`）
- [ ] 路径遍历保护 — 简化，真实版本有 `allowed_dir` 限制和路径解析（`_resolve_path`）
- [ ] ExecTool 白名单模式 — 未实现，真实版本支持 `allow_patterns`
- [ ] ExecTool 工作目录限制 — 简化，真实版本有 `restrict_to_workspace` 选项

## Unit 4: LLM 提供者
- [ ] LiteLLMProvider — 用 MockProvider 替代，真实版本通过 LiteLLM 调用真实 API（`nanobot/providers/litellm_provider.py`）
- [ ] CustomProvider — 未实现，真实版本支持直接调用 OpenAI 兼容端点（`nanobot/providers/custom_provider.py`）
- [ ] OpenAI Codex Provider — 未实现，真实版本支持 OAuth 认证（`nanobot/providers/openai_codex_provider.py`）
- [ ] 提示词缓存 — 未实现，真实版本为 Anthropic 等提供者注入 `cache_control`（`_apply_cache_control`）
- [ ] 模型前缀解析 — 简化，真实版本有复杂的前缀规则（`_resolve_model`、`_canonicalize_explicit_prefix`）
- [ ] 模型参数覆盖 — 未实现，真实版本支持按模型覆盖 temperature 等参数（`model_overrides`）
- [ ] 空内容清理 — 未实现，真实版本处理 MCP 工具返回空内容的情况（`_sanitize_empty_content`）
- [ ] 提供者注册表 — 简化为 6 个提供者，真实版本有 16+ 个（`nanobot/providers/registry.py`）
- [ ] 语音转录 — 未实现，真实版本支持 Groq Whisper 语音转文字（`nanobot/providers/transcription.py`）

## Unit 5: 上下文与记忆
- [ ] 技能加载器 — 未实现，真实版本有 `SkillsLoader` 加载和管理技能（`nanobot/agent/skills.py`）
- [ ] 技能摘要 — 未实现，真实版本生成 XML 格式的技能列表供 LLM 参考
- [ ] 记忆整合（LLM 版）— 简化为直接写入，真实版本通过 LLM 虚拟工具调用（`save_memory`）自动总结（`nanobot/agent/memory.py:consolidate`）
- [ ] 媒体编码 — 未实现，真实版本支持图片 base64 编码的多模态输入（`_build_user_content`）
- [ ] 异步整合 — 未实现，真实版本在后台异步执行记忆整合，不阻塞消息处理

## Unit 6: 会话管理
- [ ] 旧版路径迁移 — 未实现，真实版本支持从 `~/.nanobot/sessions/` 迁移（`_get_legacy_session_path`）
- [ ] 会话列表 — 未实现，真实版本有 `list_sessions()` 方法
- [ ] 工具结果截断存储 — 未实现，真实版本在保存时截断过长的工具结果
- [ ] 图片占位符 — 未实现，真实版本将 base64 图片替换为 `[image]` 占位符存储

## Unit 7: 定时任务与心跳
- [ ] Cron 表达式 — 未实现，真实版本通过 `croniter` 库支持标准 cron 表达式（`nanobot/cron/service.py`）
- [ ] 时区支持 — 未实现，真实版本支持 `zoneinfo` 时区感知的 cron 调度
- [ ] 任务启用/禁用 — 简化，真实版本有 `enable_job()` 方法
- [ ] 任务投递 — 未实现，真实版本支持将任务结果投递到指定渠道（`deliver`、`channel`、`to`）
- [ ] 心跳 LLM 决策 — 简化为关键词匹配，真实版本通过 LLM 虚拟工具调用决策（`nanobot/heartbeat/service.py:_decide`）
- [ ] 心跳结果投递 — 未实现，真实版本将结果发送到最近活跃的渠道
- [ ] 定时器自动重置 — 简化为手动 tick，真实版本有 `_arm_timer` 自动调度下一次执行

## 全局简化
- [ ] CLI 命令系统 — 未实现，真实版本有 Typer CLI（`nanobot/cli/commands.py`）
- [ ] 配置系统 — 未实现，真实版本有 Pydantic 配置模型和 JSON 配置文件（`nanobot/config/`）
- [ ] Docker 部署 — 未实现，真实版本有 Dockerfile 和 docker-compose.yml
- [ ] 日志系统 — 未实现，真实版本使用 loguru 结构化日志
- [ ] 错误处理 — 大幅简化，真实版本有完善的异常处理和优雅降级
- [ ] 内置技能 — 未实现，真实版本有 github、weather、tmux、cron 等内置技能（`nanobot/skills/`）
- [ ] 引导模板 — 未实现，真实版本有 AGENTS.md、SOUL.md 等模板文件（`nanobot/templates/`）
