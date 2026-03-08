/**
 * Unit 3: SQLite 持久化 — 数据库 Schema 与状态管理
 *
 * 使用真实的 SQLite（内存模式）演示 NanoClaw 的完整数据库操作
 */
import { fileURLToPath } from "url";
import Database from "better-sqlite3";
import type { NewMessage, RegisteredGroup, ScheduledTask } from "../shared/types.js";

export type { NewMessage, RegisteredGroup, ScheduledTask };

// ============================================================
// LEARN: 数据库单例 — 延迟初始化
// 导入此模块不会立即创建数据库，只有调用 initDb() 时才创建
// ============================================================
let db: Database.Database | null = null;

export function initDb(path: string = ":memory:"): Database.Database {
  if (db) return db;
  db = new Database(path);
  createSchema(db);
  return db;
}

export function getDb(): Database.Database {
  if (!db) return initDb();
  return db;
}

/** @internal 用于测试：重置数据库 */
export function _resetDb(): void {
  db = null;
}

function createSchema(database: Database.Database): void {
  database.exec(`
    CREATE TABLE IF NOT EXISTS chats (
      jid TEXT PRIMARY KEY,
      name TEXT,
      last_message_time TEXT,
      channel TEXT,
      is_group INTEGER DEFAULT 0
    );
    CREATE TABLE IF NOT EXISTS messages (
      id TEXT,
      chat_jid TEXT,
      sender TEXT,
      sender_name TEXT,
      content TEXT,
      timestamp TEXT,
      is_from_me INTEGER,
      is_bot_message INTEGER DEFAULT 0,
      PRIMARY KEY (id, chat_jid)
    );
    CREATE INDEX IF NOT EXISTS idx_timestamp ON messages(timestamp);
    CREATE TABLE IF NOT EXISTS scheduled_tasks (
      id TEXT PRIMARY KEY,
      group_folder TEXT NOT NULL,
      chat_jid TEXT NOT NULL,
      prompt TEXT NOT NULL,
      schedule_type TEXT NOT NULL,
      schedule_value TEXT NOT NULL,
      context_mode TEXT DEFAULT 'isolated',
      next_run TEXT,
      last_run TEXT,
      last_result TEXT,
      status TEXT DEFAULT 'active',
      created_at TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_next_run ON scheduled_tasks(next_run);
    CREATE TABLE IF NOT EXISTS task_run_logs (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      task_id TEXT NOT NULL,
      run_at TEXT NOT NULL,
      duration_ms INTEGER NOT NULL,
      status TEXT NOT NULL,
      result TEXT,
      error TEXT
    );
    CREATE TABLE IF NOT EXISTS router_state (
      key TEXT PRIMARY KEY,
      value TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS sessions (
      group_folder TEXT PRIMARY KEY,
      session_id TEXT NOT NULL
    );
    CREATE TABLE IF NOT EXISTS registered_groups (
      jid TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      folder TEXT NOT NULL UNIQUE,
      trigger_pattern TEXT NOT NULL,
      added_at TEXT NOT NULL,
      container_config TEXT,
      requires_trigger INTEGER DEFAULT 1
    );
  `);
}

// ============================================================
// LEARN: UPSERT 模式 — "有则更新，无则插入"
// ============================================================
export function storeChatMetadata(
  chatJid: string,
  timestamp: string,
  name?: string,
  channel?: string,
  isGroup?: boolean
): void {
  const d = getDb();
  const ch = channel ?? null;
  const group = isGroup === undefined ? null : isGroup ? 1 : 0;
  if (name) {
    d.prepare(
      `INSERT INTO chats (jid, name, last_message_time, channel, is_group) VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(jid) DO UPDATE SET
         name = excluded.name,
         last_message_time = MAX(last_message_time, excluded.last_message_time),
         channel = COALESCE(excluded.channel, channel),
         is_group = COALESCE(excluded.is_group, is_group)`
    ).run(chatJid, name, timestamp, ch, group);
  } else {
    d.prepare(
      `INSERT INTO chats (jid, name, last_message_time, channel, is_group) VALUES (?, ?, ?, ?, ?)
       ON CONFLICT(jid) DO UPDATE SET
         last_message_time = MAX(last_message_time, excluded.last_message_time)`
    ).run(chatJid, chatJid, timestamp, ch, group);
  }
}

export function storeMessage(msg: NewMessage): void {
  getDb()
    .prepare(
      `INSERT OR REPLACE INTO messages
       (id, chat_jid, sender, sender_name, content, timestamp, is_from_me, is_bot_message)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?)`
    )
    .run(
      msg.id, msg.chat_jid, msg.sender, msg.sender_name,
      msg.content, msg.timestamp,
      msg.is_from_me ? 1 : 0, msg.is_bot_message ? 1 : 0
    );
}

export function getNewMessages(
  jids: string[],
  lastTimestamp: string,
  botPrefix: string
): { messages: NewMessage[]; newTimestamp: string } {
  if (jids.length === 0) return { messages: [], newTimestamp: lastTimestamp };
  const placeholders = jids.map(() => "?").join(",");
  const sql = `
    SELECT id, chat_jid, sender, sender_name, content, timestamp
    FROM messages
    WHERE timestamp > ? AND chat_jid IN (${placeholders})
      AND is_bot_message = 0 AND content NOT LIKE ?
      AND content != '' AND content IS NOT NULL
    ORDER BY timestamp
  `;
  const rows = getDb()
    .prepare(sql)
    .all(lastTimestamp, ...jids, `${botPrefix}:%`) as NewMessage[];
  let newTimestamp = lastTimestamp;
  for (const row of rows) {
    if (row.timestamp > newTimestamp) newTimestamp = row.timestamp;
  }
  return { messages: rows, newTimestamp };
}

export function getMessagesSince(
  chatJid: string,
  sinceTimestamp: string,
  botPrefix: string
): NewMessage[] {
  const sql = `
    SELECT id, chat_jid, sender, sender_name, content, timestamp
    FROM messages
    WHERE chat_jid = ? AND timestamp > ?
      AND is_bot_message = 0 AND content NOT LIKE ?
      AND content != '' AND content IS NOT NULL
    ORDER BY timestamp
  `;
  return getDb()
    .prepare(sql)
    .all(chatJid, sinceTimestamp, `${botPrefix}:%`) as NewMessage[];
}

// --- 定时任务 ---
export function createTask(task: Omit<ScheduledTask, "last_run" | "last_result">): void {
  getDb()
    .prepare(
      `INSERT INTO scheduled_tasks
       (id, group_folder, chat_jid, prompt, schedule_type, schedule_value, context_mode, next_run, status, created_at)
       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)`
    )
    .run(
      task.id, task.group_folder, task.chat_jid, task.prompt,
      task.schedule_type, task.schedule_value, task.context_mode || "isolated",
      task.next_run, task.status, task.created_at
    );
}

export function getDueTasks(): ScheduledTask[] {
  const now = new Date().toISOString();
  return getDb()
    .prepare(
      `SELECT * FROM scheduled_tasks WHERE status = 'active' AND next_run IS NOT NULL AND next_run <= ? ORDER BY next_run`
    )
    .all(now) as ScheduledTask[];
}

export function getTaskById(id: string): ScheduledTask | undefined {
  return getDb().prepare("SELECT * FROM scheduled_tasks WHERE id = ?").get(id) as ScheduledTask | undefined;
}

export function getAllTasks(): ScheduledTask[] {
  return getDb().prepare("SELECT * FROM scheduled_tasks ORDER BY created_at DESC").all() as ScheduledTask[];
}

export function updateTask(id: string, updates: Partial<Pick<ScheduledTask, "status" | "next_run">>): void {
  const fields: string[] = [];
  const values: unknown[] = [];
  if (updates.status !== undefined) { fields.push("status = ?"); values.push(updates.status); }
  if (updates.next_run !== undefined) { fields.push("next_run = ?"); values.push(updates.next_run); }
  if (fields.length === 0) return;
  values.push(id);
  getDb().prepare(`UPDATE scheduled_tasks SET ${fields.join(", ")} WHERE id = ?`).run(...values);
}

export function deleteTask(id: string): void {
  getDb().prepare("DELETE FROM task_run_logs WHERE task_id = ?").run(id);
  getDb().prepare("DELETE FROM scheduled_tasks WHERE id = ?").run(id);
}

export function updateTaskAfterRun(id: string, nextRun: string | null, lastResult: string): void {
  const now = new Date().toISOString();
  getDb()
    .prepare(
      `UPDATE scheduled_tasks SET next_run = ?, last_run = ?, last_result = ?,
       status = CASE WHEN ? IS NULL THEN 'completed' ELSE status END WHERE id = ?`
    )
    .run(nextRun, now, lastResult, nextRun, id);
}

// --- 群组注册 ---
export function setRegisteredGroup(jid: string, group: RegisteredGroup): void {
  getDb()
    .prepare(
      `INSERT OR REPLACE INTO registered_groups
       (jid, name, folder, trigger_pattern, added_at, requires_trigger)
       VALUES (?, ?, ?, ?, ?, ?)`
    )
    .run(jid, group.name, group.folder, group.trigger, group.added_at,
      group.requiresTrigger === undefined ? 1 : group.requiresTrigger ? 1 : 0);
}

export function getAllRegisteredGroups(): Record<string, RegisteredGroup> {
  const rows = getDb().prepare("SELECT * FROM registered_groups").all() as Array<{
    jid: string; name: string; folder: string; trigger_pattern: string;
    added_at: string; requires_trigger: number | null;
  }>;
  const result: Record<string, RegisteredGroup> = {};
  for (const row of rows) {
    result[row.jid] = {
      name: row.name, folder: row.folder, trigger: row.trigger_pattern,
      added_at: row.added_at,
      requiresTrigger: row.requires_trigger === null ? undefined : row.requires_trigger === 1,
    };
  }
  return result;
}

// --- 会话 ---
export function setSession(groupFolder: string, sessionId: string): void {
  getDb().prepare("INSERT OR REPLACE INTO sessions (group_folder, session_id) VALUES (?, ?)").run(groupFolder, sessionId);
}

export function getAllSessions(): Record<string, string> {
  const rows = getDb().prepare("SELECT group_folder, session_id FROM sessions").all() as Array<{ group_folder: string; session_id: string }>;
  const result: Record<string, string> = {};
  for (const row of rows) result[row.group_folder] = row.session_id;
  return result;
}

// --- 路由状态 ---
export function setRouterState(key: string, value: string): void {
  getDb().prepare("INSERT OR REPLACE INTO router_state (key, value) VALUES (?, ?)").run(key, value);
}

export function getRouterState(key: string): string | undefined {
  const row = getDb().prepare("SELECT value FROM router_state WHERE key = ?").get(key) as { value: string } | undefined;
  return row?.value;
}

// ============================================================
// 独立运行时的演示
// ============================================================
function main(): void {
  initDb();
  console.log("[数据库] Schema 已创建 (7 张表)");

  console.log("--- 存储聊天元数据 ---");
  const now = new Date().toISOString();
  storeChatMetadata("family@g.us", now, "家庭群", "whatsapp", true);
  console.log(`[数据库] 存储聊天: family@g.us (家庭群)`);
  storeChatMetadata("work@g.us", now, "工作群", "whatsapp", true);
  console.log(`[数据库] 存储聊天: work@g.us (工作群)`);

  console.log("--- 存储消息 ---");
  const baseTime = Date.now();
  const msgs: NewMessage[] = [
    { id: "msg-001", chat_jid: "family@g.us", sender: "zhangsan@s.whatsapp.net", sender_name: "张三", content: "@Andy 明天几点出发？", timestamp: new Date(baseTime + 1000).toISOString(), is_from_me: false, is_bot_message: false },
    { id: "msg-002", chat_jid: "family@g.us", sender: "lisi@s.whatsapp.net", sender_name: "李四", content: "我觉得 9 点比较好", timestamp: new Date(baseTime + 2000).toISOString(), is_from_me: false, is_bot_message: false },
    { id: "msg-003", chat_jid: "work@g.us", sender: "wangwu@s.whatsapp.net", sender_name: "王五", content: "@Andy 帮我查一下项目进度", timestamp: new Date(baseTime + 3000).toISOString(), is_from_me: false, is_bot_message: false },
  ];
  for (const msg of msgs) { storeMessage(msg); console.log(`[数据库] 存储消息: ${msg.id} 到 ${msg.chat_jid}`); }

  console.log("--- 查询新消息 ---");
  const result1 = getNewMessages(["family@g.us", "work@g.us"], "", "Andy");
  console.log(`[查询] 自 "" 以来的新消息: ${result1.messages.length} 条`);
  const result2 = getNewMessages(["family@g.us", "work@g.us"], result1.newTimestamp, "Andy");
  console.log(`[查询] 游标前进后: ${result2.messages.length} 条`);

  console.log("--- 注册群组 ---");
  setRegisteredGroup("family@g.us", { name: "家庭群", folder: "family-chat", trigger: "@Andy", added_at: now, requiresTrigger: true });
  console.log(`[数据库] 注册群组: family@g.us -> family-chat`);
  const groups = getAllRegisteredGroups();
  console.log(`[查询] 已注册群组: ${Object.keys(groups).length} 个`);

  console.log("--- 定时任务 ---");
  createTask({ id: "task-001", group_folder: "family-chat", chat_jid: "family@g.us", prompt: "发送每日早安问候", schedule_type: "cron", schedule_value: "0 9 * * 1-5", context_mode: "isolated", next_run: new Date(Date.now() - 60000).toISOString(), status: "active", created_at: now });
  const dueTasks = getDueTasks();
  console.log(`[查询] 到期任务: ${dueTasks.length} 个`);

  console.log("--- 会话管理 ---");
  setSession("family-chat", "session-abc");
  console.log(`[查询] 所有会话: ${JSON.stringify(getAllSessions())}`);

  console.log("--- 路由状态 ---");
  setRouterState("last_timestamp", now);
  console.log(`[查询] last_timestamp = ${getRouterState("last_timestamp")?.slice(0, 19)}`);

  console.log("--- 演示结束 ---");
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main();
}
