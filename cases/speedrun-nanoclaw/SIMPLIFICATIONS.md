# 简化清单

每个单元相对原始代码库做了哪些简化或 stub。
可以把这个清单当作"渐进还原"的路线图。

> **提示**: 你可以让编码智能体（Claude Code、Cursor 等）帮你还原任意一项。
> 指向原始项目和本 speedrun，例如：
> "参照 ../nanoclaw/src/db.ts 在 unit-3 中还原真实的数据库实现"

## Unit 1: 全局总览
- [ ] `whatsapp.ts` — stub 为内存消息队列，真实实现使用 baileys 库连接 WhatsApp (`src/channels/whatsapp.ts`)
- [ ] `db.ts` — stub 为内存对象，真实实现使用 SQLite (`src/db.ts`)
- [ ] `container-runner.ts` — stub 为 setTimeout 模拟，真实实现 spawn Docker 容器 (`src/container-runner.ts`)
- [ ] `group-queue.ts` — stub 为直接调用，真实实现有并发限制和排队 (`src/group-queue.ts`)
- [ ] `ipc.ts` — stub 为空操作，真实实现轮询文件系统 (`src/ipc.ts`)
- [ ] `task-scheduler.ts` — stub 为空操作，真实实现有 cron 解析和定时执行 (`src/task-scheduler.ts`)
- [ ] 错误处理 — 移除了大部分 try/catch，真实实现有完整的错误恢复和重试
- [ ] 挂载安全 — 完全省略，真实实现有 allowlist 验证 (`src/mount-security.ts`)

## Unit 2: WhatsApp 通道
- [ ] `baileys` 库 — stub 为事件发射器模拟，真实实现连接 WhatsApp Web (`@whiskeysockets/baileys`)
- [ ] QR 码认证 — 省略，真实实现通过终端显示 QR 码
- [ ] LID 翻译 — 省略，真实实现将 LID JID 转换为手机号 JID
- [ ] 消息队列 — 简化为同步发送，真实实现有断线重连后的队列刷新
- [ ] 群组元数据同步 — stub 为静态数据，真实实现每 24 小时从 WhatsApp 同步

## Unit 3: SQLite 持久化
- [ ] JSON 迁移 — 省略，真实实现从旧版 JSON 文件迁移到 SQLite (`migrateJsonState()`)
- [ ] 列迁移 — 省略 ALTER TABLE 迁移逻辑，直接使用最终 schema
- [ ] 路由状态 — 简化为单键存取，真实实现有多键状态管理

## Unit 4: 容器运行器
- [ ] Docker 进程 — stub 为模拟子进程，真实实现 `spawn('docker', [...])` (`src/container-runner.ts`)
- [ ] 卷挂载构建 — 简化为打印挂载列表，真实实现有复杂的权限和路径解析 (`buildVolumeMounts()`)
- [ ] 密钥传递 — 省略 stdin 密钥注入，真实实现通过 stdin 传递 API key
- [ ] 超时管理 — 简化为固定超时，真实实现有活动重置和优雅停止
- [ ] 日志写入 — 省略容器日志文件写入

## Unit 5: 分组队列
- [ ] 重试逻辑 — 简化为固定延迟，真实实现有指数退避 (`scheduleRetry()`)
- [ ] 优雅关闭 — 省略，真实实现有 `shutdown()` 方法分离容器
- [ ] IPC 文件写入 — stub 为控制台输出，真实实现写入 JSON 文件到 IPC 目录

## Unit 6: IPC 与调度器
- [ ] 文件系统轮询 — stub 为内存队列，真实实现轮询 `data/ipc/` 目录 (`src/ipc.ts`)
- [ ] 群组注册 — 简化为内存操作，真实实现有文件夹验证和数据库持久化
- [ ] cron 解析 — 使用真实的 `cron-parser` 库，但省略了时区配置
- [ ] 任务运行日志 — 省略 `task_run_logs` 表写入

## Unit 7: Agent Runner
- [ ] Claude Agent SDK — stub 为模拟回复，真实实现调用 `@anthropic-ai/claude-agent-sdk` 的 `query()` (`container/agent-runner/src/index.ts`)
- [ ] MCP Server — stub 为函数调用，真实实现用 `@modelcontextprotocol/sdk` 创建 stdio 服务器 (`container/agent-runner/src/ipc-mcp-stdio.ts`)
- [ ] MessageStream — 简化为字符串队列，真实实现是 `AsyncIterable<SDKUserMessage>` 供 SDK 消费
- [ ] IPC 输入轮询 — stub 为预设消息，真实实现轮询 `/workspace/ipc/input/` 目录
- [ ] Hooks — 仅演示逻辑，真实实现通过 SDK 的 `hooks` 配置注入
- [ ] 会话恢复 — 省略 `resume` 和 `resumeSessionAt` 的完整逻辑
- [ ] 对话归档 — 省略 transcript 解析和 markdown 格式化的完整实现

## Unit 8: Skills Engine
- [ ] Manifest 解析 — stub 为硬编码对象，真实实现从 `manifest.yaml` 读取 (`skills-engine/manifest.ts`)
- [ ] 三方合并 — stub 为字符串拼接，真实实现调用 `git merge-file` (`skills-engine/merge.ts`)
- [ ] 状态持久化 — stub 为内存对象，真实实现读写 `.nanoclaw/state.yaml` (`skills-engine/state.ts`)
- [ ] 文件系统操作 — stub 为内存 Map，真实实现操作真实文件并创建 `.nanoclaw/base/` 基线快照
- [ ] 锁机制 — 省略，真实实现用 `.nanoclaw/lock` 文件防止并发 (`skills-engine/lock.ts`)
- [ ] 回放 (Replay) — 简化为日志输出，真实实现从基线重新 `applySkill` 所有剩余技能 (`skills-engine/replay.ts`)
- [ ] 自定义修改 (Custom Patches) — 省略，真实实现用 `git diff` 生成 patch 并在卸载后重新应用
- [ ] 路径重映射 (Path Remap) — 省略，真实实现支持核心文件重命名后技能仍能定位 (`skills-engine/path-remap.ts`)
- [ ] 更新流程 (Update) — 省略，真实实现支持从上游拉取新版本并重新应用技能 (`skills-engine/update.ts`)
