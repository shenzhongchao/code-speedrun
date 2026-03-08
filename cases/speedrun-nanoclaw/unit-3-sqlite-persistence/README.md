# Unit 3: SQLite 持久化 — 数据库 Schema 与状态管理

## 用大白话说

这个单元就像一个图书馆的档案系统：每条消息是一张卡片，每个群组是一个档案柜，每个定时任务是一张日程表。所有东西都有编号，方便查找和更新。

## 背景知识

NanoClaw 使用 [better-sqlite3](https://github.com/WiseLibs/better-sqlite3) 作为数据库。SQLite 是一个嵌入式数据库——不需要单独的数据库服务器，数据就存在一个文件里（`store/messages.db`）。这完美契合 NanoClaw "单进程"的设计哲学。

**为什么不用 PostgreSQL 或 MongoDB？** 因为 NanoClaw 是个人助手，不是多用户 SaaS。SQLite 的性能对于个人使用绰绰有余，而且零运维——不需要安装、配置、备份数据库服务器。

## 关键术语

- **better-sqlite3**: Node.js 的同步 SQLite 绑定，比异步 API 更简单且性能更好
- **Schema**: 数据库表结构定义，包括列名、类型、约束
- **UPSERT**: `INSERT ... ON CONFLICT DO UPDATE` 的简称，"有则更新，无则插入"
- **游标 (Cursor)**: `lastTimestamp` 和 `lastAgentTimestamp`，记录"读到哪里了"，避免重复处理
- **路由状态 (Router State)**: 键值对存储，保存轮询循环的进度信息

## 这个单元做了什么

使用真实的 SQLite（内存模式）演示 NanoClaw 的完整数据库操作：
1. 创建 schema（6 张表）
2. 存储和查询消息
3. 管理群组注册
4. 创建和查询定时任务
5. 会话和路由状态的持久化

## 关键代码走读

### 6 张核心表
- `chats`: 聊天元数据（JID、名称、最后活跃时间）— 用于群组发现
- `messages`: 消息内容 — 只为已注册群组存储
- `scheduled_tasks`: 定时任务 — cron/interval/once 三种调度类型
- `task_run_logs`: 任务执行日志 — 记录每次运行的结果和耗时
- `router_state`: 键值对 — 存储轮询游标等运行时状态
- `sessions`: 会话映射 — 群组文件夹 → Claude 会话 ID
- `registered_groups`: 已注册群组 — JID → 群组配置

### 消息游标机制
系统维护两个游标：`lastTimestamp`（全局"已看到"标记）和 `lastAgentTimestamp[chatJid]`（每群组"已处理"标记）。这两个游标的分离允许：消息被"看到"后立即前进全局游标，但只有成功处理后才前进群组游标。失败时可以回滚群组游标重试。

### UPSERT 模式
`storeChatMetadata()` 使用 `INSERT ... ON CONFLICT DO UPDATE`：如果 JID 已存在就更新时间戳，不存在就插入新行。这避免了"先查后插"的竞态条件。

## 运行方式

```bash
npm run unit3
```

## 预期输出

```
[数据库] Schema 已创建 (7 张表)
--- 存储聊天元数据 ---
[数据库] 存储聊天: family@g.us (家庭群)
[数据库] 存储聊天: work@g.us (工作群)
--- 存储消息 ---
[数据库] 存储消息: msg-001 到 family@g.us
[数据库] 存储消息: msg-002 到 family@g.us
[数据库] 存储消息: msg-003 到 work@g.us
--- 查询新消息 ---
[查询] 自 "" 以来的新消息: 3 条
[查询] 自 "2026-..." 以来的新消息: 0 条 (游标已前进)
--- 注册群组 ---
[数据库] 注册群组: family@g.us -> family-chat
[数据库] 注册群组: work@g.us -> work-chat
[查询] 已注册群组: 2 个
--- 定时任务 ---
[数据库] 创建任务: task-001 (cron: 0 9 * * 1-5)
[查询] 到期任务: 1 个
[数据库] 任务执行后更新: task-001, 下次运行: 2026-...
--- 会话管理 ---
[数据库] 保存会话: family-chat -> session-abc
[查询] 所有会话: {"family-chat":"session-abc"}
--- 路由状态 ---
[数据库] 保存路由状态: last_timestamp = 2026-...
[查询] 路由状态: last_timestamp = 2026-...
--- 演示结束 ---
```

## 练习

1. **添加消息搜索**: 写一个函数，按关键词搜索消息内容（提示：用 SQL 的 `LIKE` 操作符）
2. **实现任务暂停/恢复**: 写 `pauseTask(id)` 和 `resumeTask(id)` 函数，更新 `status` 字段
3. **用自己的话解释**: 为什么 NanoClaw 需要两个不同的时间戳游标（`lastTimestamp` 和 `lastAgentTimestamp`）？如果只用一个会出什么问题？

## 调试指南

- **观察点**: 在 `getNewMessages()` 的 SQL 查询处打断点，观察 WHERE 条件如何过滤消息
- **常见问题**: 如果查询返回空结果，检查时间戳格式是否为 ISO 8601（`2026-01-01T00:00:00.000Z`）
- **状态检查**: 用 `db.prepare('SELECT * FROM messages').all()` 直接查看所有消息
