/**
 * Unit 6: IPC 与调度器 — 文件系统通信与定时任务
 *
 * 模拟 IPC 监听器的权限控制和调度器的 cron 解析
 */
import { fileURLToPath } from "url";
import { CronExpressionParser } from "cron-parser";
import type { RegisteredGroup, ScheduledTask } from "../shared/types.js";

export type { RegisteredGroup, ScheduledTask };

// ============================================================
// LEARN: IPC 消息类型
// ============================================================
export interface IpcMessage {
  type: string;
  chatJid?: string;
  text?: string;
  prompt?: string;
  schedule_type?: string;
  schedule_value?: string;
  context_mode?: string;
  targetJid?: string;
  taskId?: string;
  jid?: string;
  name?: string;
  folder?: string;
  trigger?: string;
}

// ============================================================
// LEARN: IpcProcessor — 封装 IPC 状态，让外部可以注入群组和任务存储
// ============================================================
export class IpcProcessor {
  private registeredGroups: Record<string, RegisteredGroup>;
  private onCreateTask: ((task: ScheduledTask) => void) | null;
  private onPauseTask: ((taskId: string) => void) | null;
  private onSendMessage: ((chatJid: string, text: string) => void) | null;
  private onRegisterGroup: ((jid: string, group: RegisteredGroup) => void) | null;

  constructor(opts: {
    registeredGroups: Record<string, RegisteredGroup>;
    onCreateTask?: (task: ScheduledTask) => void;
    onPauseTask?: (taskId: string) => void;
    onSendMessage?: (chatJid: string, text: string) => void;
    onRegisterGroup?: (jid: string, group: RegisteredGroup) => void;
  }) {
    this.registeredGroups = opts.registeredGroups;
    this.onCreateTask = opts.onCreateTask || null;
    this.onPauseTask = opts.onPauseTask || null;
    this.onSendMessage = opts.onSendMessage || null;
    this.onRegisterGroup = opts.onRegisterGroup || null;
  }

  process(data: IpcMessage, sourceGroup: string, isMain: boolean): void {
    switch (data.type) {
      case "message": {
        const targetGroup = this.registeredGroups[data.chatJid || ""];
        const authorized = isMain || (targetGroup && targetGroup.folder === sourceGroup);
        if (authorized && data.chatJid && data.text) {
          console.log(`[IPC] ✅ ${isMain ? "主群组" : "非主群组"}发送消息${isMain ? "" : "到自己的聊天"}: 已授权`);
          this.onSendMessage?.(data.chatJid, data.text);
        } else {
          console.log(`[IPC] ❌ 非主群组跨组发送: 已拦截`);
        }
        break;
      }

      case "schedule_task": {
        if (!data.prompt || !data.schedule_type || !data.schedule_value || !data.targetJid) {
          console.log(`[IPC] ❌ 创建任务: 缺少必要字段`);
          break;
        }
        const targetEntry = this.registeredGroups[data.targetJid];
        if (!targetEntry) { console.log(`[IPC] ❌ 创建任务: 目标群组未注册`); break; }
        if (!isMain && targetEntry.folder !== sourceGroup) { console.log(`[IPC] ❌ 非主群组跨组创建任务: 已拦截`); break; }

        const nextRun = calculateNextRun(data.schedule_type, data.schedule_value);
        if (nextRun === undefined) { console.log(`[IPC] ❌ 无效的调度表达式: ${data.schedule_value}`); break; }

        const task: ScheduledTask = {
          id: `task-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
          group_folder: targetEntry.folder,
          chat_jid: data.targetJid,
          prompt: data.prompt,
          schedule_type: data.schedule_type,
          schedule_value: data.schedule_value,
          context_mode: data.context_mode || "isolated",
          next_run: nextRun,
          last_run: null,
          last_result: null,
          status: "active",
          created_at: new Date().toISOString(),
        };
        console.log(`[IPC] 创建任务: ${data.schedule_type} "${data.schedule_value}" -> 下次运行: ${nextRun?.slice(0, 19)}`);
        this.onCreateTask?.(task);
        break;
      }

      case "pause_task": {
        if (data.taskId) {
          console.log(`[IPC] ✅ 任务 ${data.taskId} 已暂停`);
          this.onPauseTask?.(data.taskId);
        }
        break;
      }

      case "register_group": {
        if (!isMain) { console.log(`[IPC] ❌ 非主群组尝试注册: 已拦截`); break; }
        if (data.jid && data.name && data.folder && data.trigger) {
          const group: RegisteredGroup = {
            name: data.name, folder: data.folder, trigger: data.trigger,
            added_at: new Date().toISOString(),
          };
          this.registeredGroups[data.jid] = group;
          console.log(`[IPC] 主群组注册新群组: ${data.jid} -> ${data.folder} ✅`);
          this.onRegisterGroup?.(data.jid, group);
        }
        break;
      }

      default:
        console.log(`[IPC] ⚠️ 未知消息类型: ${data.type}`);
    }
  }
}

// ============================================================
// LEARN: 调度计算 — 三种调度类型
// ============================================================
export function calculateNextRun(scheduleType: string, scheduleValue: string): string | null | undefined {
  if (scheduleType === "cron") {
    try {
      const interval = CronExpressionParser.parse(scheduleValue);
      return interval.next().toISOString();
    } catch { return undefined; }
  } else if (scheduleType === "interval") {
    const ms = parseInt(scheduleValue, 10);
    if (isNaN(ms) || ms <= 0) return undefined;
    return new Date(Date.now() + ms).toISOString();
  } else if (scheduleType === "once") {
    const scheduled = new Date(scheduleValue);
    if (isNaN(scheduled.getTime())) return undefined;
    return scheduled.toISOString();
  }
  return null;
}

export function calculateNextRunForTask(task: ScheduledTask): string | null {
  const result = calculateNextRun(task.schedule_type, task.schedule_value);
  return result === undefined ? null : result;
}

// ============================================================
// 演示
// ============================================================
async function main(): Promise<void> {
  const groups: Record<string, RegisteredGroup> = {
    "chat@g.us": { name: "主频道", folder: "main", trigger: "@Andy", added_at: new Date().toISOString() },
    "family-chat@g.us": { name: "家庭群", folder: "family", trigger: "@Andy", added_at: new Date().toISOString() },
  };

  const tasks: ScheduledTask[] = [];

  const ipc = new IpcProcessor({
    registeredGroups: groups,
    onCreateTask: (t) => tasks.push(t),
    onSendMessage: (jid, text) => console.log(`[回调] 发送消息到 ${jid}: ${text}`),
    onRegisterGroup: (jid, g) => console.log(`[回调] 注册群组: ${jid} -> ${g.folder}`),
  });

  console.log("--- IPC: 发送消息 ---");
  console.log(`[IPC] 处理消息: main -> chat@g.us "你好"`);
  ipc.process({ type: "message", chatJid: "chat@g.us", text: "你好" }, "main", true);
  console.log(`[IPC] 处理消息: family -> chat@g.us "你好"`);
  ipc.process({ type: "message", chatJid: "chat@g.us", text: "你好" }, "family", false);
  console.log(`[IPC] 处理消息: family -> family-chat@g.us "你好"`);
  ipc.process({ type: "message", chatJid: "family-chat@g.us", text: "你好" }, "family", false);

  console.log("\n--- IPC: 创建定时任务 ---");
  ipc.process({ type: "schedule_task", prompt: "发送每日早安", schedule_type: "cron", schedule_value: "0 9 * * 1-5", targetJid: "chat@g.us" }, "main", true);
  ipc.process({ type: "schedule_task", prompt: "每小时检查", schedule_type: "interval", schedule_value: "3600000", targetJid: "chat@g.us" }, "main", true);
  const futureTime = new Date(Date.now() + 86400000).toISOString();
  ipc.process({ type: "schedule_task", prompt: "明天提醒", schedule_type: "once", schedule_value: futureTime, targetJid: "chat@g.us" }, "main", true);

  console.log("\n--- IPC: 注册群组 ---");
  ipc.process({ type: "register_group", jid: "work@g.us", name: "工作群", folder: "work-chat", trigger: "@Andy" }, "main", true);
  ipc.process({ type: "register_group", jid: "hack@g.us", name: "黑客群", folder: "hack", trigger: "@Andy" }, "family", false);

  console.log("\n--- 调度器: 检查到期任务 ---");
  if (tasks.length > 0) {
    tasks[0].next_run = new Date(Date.now() - 1000).toISOString();
    tasks[0].id = "task-demo";
    tasks[0].prompt = "发送每日早安";
  }

  console.log("[调度器] 检查到期任务...");
  const now = new Date().toISOString();
  const dueTasks = tasks.filter((t) => t.status === "active" && t.next_run && t.next_run <= now);
  if (dueTasks.length === 0) {
    console.log("[调度器] 没有到期任务");
  } else {
    console.log(`[调度器] 发现 ${dueTasks.length} 个到期任务`);
    for (const task of dueTasks) {
      console.log(`[调度器] 执行任务 ${task.id}: "${task.prompt}"`);
      await new Promise((r) => setTimeout(r, 50));
      const nextRun = calculateNextRunForTask(task);
      task.next_run = nextRun;
      task.status = nextRun ? "active" : "completed";
      console.log("[调度器] 任务完成，计算下次运行时间...");
      if (nextRun) console.log(`[调度器] 下次运行: ${nextRun.slice(0, 19)}`);
      else console.log("[调度器] 一次性任务，已标记完成");
    }
  }

  console.log("\n--- 演示结束 ---");
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch(console.error);
}
