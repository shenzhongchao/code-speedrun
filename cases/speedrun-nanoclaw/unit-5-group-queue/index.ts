/**
 * Unit 5: 分组队列 — 并发控制与每组排队
 *
 * 模拟 GroupQueue 的核心行为：
 * 每组串行、全局并发限制、消息积压处理、IPC 管道、排空逻辑
 */
import { fileURLToPath } from "url";

// ============================================================
// LEARN: 配置
// ============================================================
const DEFAULT_MAX_CONCURRENT = 2;

export interface QueuedTask {
  id: string;
  groupJid: string;
  fn: () => Promise<void>;
}

export interface GroupState {
  active: boolean;
  idleWaiting: boolean;
  isTaskContainer: boolean;
  pendingMessages: boolean;
  pendingTasks: QueuedTask[];
  groupFolder: string | null;
}

// ============================================================
// LEARN: GroupQueue — 并发调度的核心
// ============================================================
export class GroupQueue {
  private groups = new Map<string, GroupState>();
  private activeCount = 0;
  private waitingGroups: string[] = [];
  private maxConcurrent: number;
  private processMessagesFn: ((groupJid: string) => Promise<boolean>) | null = null;

  constructor(maxConcurrent = DEFAULT_MAX_CONCURRENT) {
    this.maxConcurrent = maxConcurrent;
  }

  private getGroup(groupJid: string): GroupState {
    let state = this.groups.get(groupJid);
    if (!state) {
      state = { active: false, idleWaiting: false, isTaskContainer: false, pendingMessages: false, pendingTasks: [], groupFolder: null };
      this.groups.set(groupJid, state);
    }
    return state;
  }

  setProcessMessagesFn(fn: (groupJid: string) => Promise<boolean>): void {
    this.processMessagesFn = fn;
  }

  getActiveCount(): number { return this.activeCount; }
  isGroupActive(groupJid: string): boolean { return this.getGroup(groupJid).active; }

  enqueueMessageCheck(groupJid: string): void {
    const state = this.getGroup(groupJid);
    if (state.active) {
      state.pendingMessages = true;
      console.log(`[队列] 群组 ${groupJid}: 容器活跃中，消息已标记待处理`);
      return;
    }
    if (this.activeCount >= this.maxConcurrent) {
      state.pendingMessages = true;
      if (!this.waitingGroups.includes(groupJid)) this.waitingGroups.push(groupJid);
      console.log(`[队列] 群组 ${groupJid}: 达到并发上限，加入等待队列`);
      return;
    }
    this.runForGroup(groupJid, "messages");
  }

  enqueueTask(groupJid: string, taskId: string, fn: () => Promise<void>): void {
    const state = this.getGroup(groupJid);
    if (state.pendingTasks.some((t) => t.id === taskId)) {
      console.log(`[队列] 群组 ${groupJid}: 任务 ${taskId} 已在队列中，跳过`);
      return;
    }
    if (state.active) {
      state.pendingTasks.push({ id: taskId, groupJid, fn });
      if (state.idleWaiting) this.closeStdin(groupJid);
      console.log(`[队列] 群组 ${groupJid}: 容器活跃中，任务 ${taskId} 已排队`);
      return;
    }
    if (this.activeCount >= this.maxConcurrent) {
      state.pendingTasks.push({ id: taskId, groupJid, fn });
      if (!this.waitingGroups.includes(groupJid)) this.waitingGroups.push(groupJid);
      console.log(`[队列] 群组 ${groupJid}: 达到并发上限，任务 ${taskId} 已排队`);
      return;
    }
    this.runTask(groupJid, { id: taskId, groupJid, fn });
  }

  sendMessage(groupJid: string, text: string): boolean {
    const state = this.getGroup(groupJid);
    if (!state.active || state.isTaskContainer) return false;
    state.idleWaiting = false;
    console.log(`[IPC] ${groupJid}: 通过管道发送消息到活跃容器`);
    return true;
  }

  notifyIdle(groupJid: string): void {
    const state = this.getGroup(groupJid);
    state.idleWaiting = true;
    if (state.pendingTasks.length > 0) this.closeStdin(groupJid);
  }

  closeStdin(groupJid: string): void {
    const state = this.getGroup(groupJid);
    if (!state.active) return;
    console.log(`[IPC] ${groupJid}: 发送关闭信号`);
  }

  private async runForGroup(groupJid: string, reason: "messages" | "drain"): Promise<void> {
    const state = this.getGroup(groupJid);
    state.active = true;
    state.idleWaiting = false;
    state.isTaskContainer = false;
    state.pendingMessages = false;
    this.activeCount++;
    console.log(`[队列] 群组 ${groupJid}: 启动容器处理消息 (活跃: ${this.activeCount}/${this.maxConcurrent})`);
    try {
      if (this.processMessagesFn) await this.processMessagesFn(groupJid);
    } catch (err) {
      console.log(`[队列] ${groupJid}: 处理出错: ${err}`);
    } finally {
      state.active = false;
      state.groupFolder = null;
      this.activeCount--;
      console.log(`[队列] ${groupJid}: 容器完成，释放槽位 (活跃: ${this.activeCount}/${this.maxConcurrent})`);
      this.drainGroup(groupJid);
    }
  }

  private async runTask(groupJid: string, task: QueuedTask): Promise<void> {
    const state = this.getGroup(groupJid);
    state.active = true;
    state.idleWaiting = false;
    state.isTaskContainer = true;
    this.activeCount++;
    console.log(`[队列] 群组 ${groupJid}: 执行任务 ${task.id} (活跃: ${this.activeCount}/${this.maxConcurrent})`);
    try {
      await task.fn();
    } catch (err) {
      console.log(`[队列] ${groupJid}: 任务 ${task.id} 出错: ${err}`);
    } finally {
      state.active = false;
      state.isTaskContainer = false;
      state.groupFolder = null;
      this.activeCount--;
      console.log(`[队列] ${groupJid}: 任务完成，释放槽位 (活跃: ${this.activeCount}/${this.maxConcurrent})`);
      this.drainGroup(groupJid);
    }
  }

  private drainGroup(groupJid: string): void {
    const state = this.getGroup(groupJid);
    if (state.pendingTasks.length > 0) {
      const task = state.pendingTasks.shift()!;
      console.log(`[队列] ${groupJid}: 优先处理待执行任务 ${task.id}`);
      this.runTask(groupJid, task);
      return;
    }
    if (state.pendingMessages) {
      console.log(`[队列] ${groupJid}: 发现积压消息，继续处理`);
      this.runForGroup(groupJid, "drain");
      return;
    }
    console.log(`[队列] ${groupJid}: 无积压，空闲`);
    this.drainWaiting();
  }

  private drainWaiting(): void {
    while (this.waitingGroups.length > 0 && this.activeCount < this.maxConcurrent) {
      const nextJid = this.waitingGroups.shift()!;
      const state = this.getGroup(nextJid);
      if (state.pendingTasks.length > 0) {
        const task = state.pendingTasks.shift()!;
        console.log(`[队列] ${nextJid}: 从等待队列启动任务 ${task.id}`);
        this.runTask(nextJid, task);
      } else if (state.pendingMessages) {
        console.log(`[队列] ${nextJid}: 从等待队列启动消息处理`);
        this.runForGroup(nextJid, "drain");
      }
    }
  }
}

// ============================================================
// 演示
// ============================================================
async function main(): Promise<void> {
  const queue = new GroupQueue();
  queue.setProcessMessagesFn(async (groupJid) => {
    console.log(`[处理] ${groupJid}: 处理消息中...`);
    await new Promise((r) => setTimeout(r, 100));
    console.log(`[处理] ${groupJid}: 处理完成`);
    return true;
  });

  console.log("--- 场景 1: 基本消息处理 ---");
  queue.enqueueMessageCheck("group-A");
  await new Promise((r) => setTimeout(r, 300));

  console.log("\n--- 场景 2: 消息积压 ---");
  const queue2 = new GroupQueue();
  queue2.setProcessMessagesFn(async (groupJid) => {
    console.log(`[处理] ${groupJid}: 处理消息中...`);
    await new Promise((r) => setTimeout(r, 100));
    console.log(`[处理] ${groupJid}: 处理完成`);
    return true;
  });
  queue2.enqueueMessageCheck("group-A");
  await new Promise((r) => setTimeout(r, 10));
  queue2.enqueueMessageCheck("group-A");
  await new Promise((r) => setTimeout(r, 500));

  console.log("\n--- 场景 3: 并发限制 ---");
  const queue3 = new GroupQueue();
  queue3.setProcessMessagesFn(async (groupJid) => {
    console.log(`[处理] ${groupJid}: 处理消息中...`);
    await new Promise((r) => setTimeout(r, 150));
    console.log(`[处理] ${groupJid}: 处理完成`);
    return true;
  });
  queue3.enqueueMessageCheck("group-A");
  queue3.enqueueMessageCheck("group-B");
  queue3.enqueueMessageCheck("group-C");
  await new Promise((r) => setTimeout(r, 600));

  console.log("\n--- 场景 4: IPC 管道 ---");
  const queue4 = new GroupQueue();
  queue4.setProcessMessagesFn(async (groupJid) => {
    console.log(`[处理] ${groupJid}: 处理消息中...`);
    await new Promise((r) => setTimeout(r, 50));
    const sent = queue4.sendMessage(groupJid, "新消息通过管道发送");
    if (!sent) console.log(`[IPC] ${groupJid}: 管道发送失败`);
    await new Promise((r) => setTimeout(r, 50));
    console.log(`[处理] ${groupJid}: 处理完成`);
    return true;
  });
  queue4.enqueueMessageCheck("group-A");
  await new Promise((r) => setTimeout(r, 300));

  console.log("\n--- 场景 5: 任务优先于消息 ---");
  const queue5 = new GroupQueue();
  queue5.setProcessMessagesFn(async (groupJid) => {
    console.log(`[处理] ${groupJid}: 处理消息中...`);
    await new Promise((r) => setTimeout(r, 50));
    console.log(`[处理] ${groupJid}: 处理完成`);
    return true;
  });
  queue5.enqueueMessageCheck("group-A");
  await new Promise((r) => setTimeout(r, 10));
  queue5.enqueueTask("group-A", "task-001", async () => {
    console.log(`[处理] group-A: 执行任务 task-001`);
    await new Promise((r) => setTimeout(r, 50));
  });
  queue5.enqueueMessageCheck("group-A");
  await new Promise((r) => setTimeout(r, 600));

  console.log("\n--- 演示结束 ---");
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch(console.error);
}
