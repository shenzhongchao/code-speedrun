/**
 * Unit 7: Agent Runner — 容器内部的智能体运行时
 *
 * 模拟容器内的完整运行时：
 * stdin 输入 → MCP 工具服务器 → Claude SDK 查询 → 哨兵标记输出 → IPC 循环
 */
import { fileURLToPath } from "url";
import type { ContainerInput, ContainerOutput } from "../shared/types.js";
import { OUTPUT_START_MARKER, OUTPUT_END_MARKER } from "../shared/types.js";

export type { ContainerInput, ContainerOutput };
export { OUTPUT_START_MARKER, OUTPUT_END_MARKER };

// ============================================================
// LEARN: 哨兵标记输出
// ============================================================
export function writeOutput(output: ContainerOutput): void {
  console.log(OUTPUT_START_MARKER);
  console.log(JSON.stringify(output));
  console.log(OUTPUT_END_MARKER);
}

// ============================================================
// LEARN: MCP 工具服务器 — Claude 的"工具箱"
// ============================================================
export interface McpTool {
  name: string;
  description: string;
  handler: (args: Record<string, string>) => string;
}

const ipcFiles: Array<{ dir: string; filename: string; data: object }> = [];

function writeIpcFile(dir: string, data: object): string {
  const filename = `${Date.now()}-${Math.random().toString(36).slice(2, 8)}.json`;
  ipcFiles.push({ dir, filename, data });
  return filename;
}

export function createMcpTools(chatJid: string, groupFolder: string, isMain: boolean): McpTool[] {
  return [
    {
      name: "send_message",
      description: "发送消息到用户或群组",
      handler: (args) => {
        const filename = writeIpcFile("messages", { type: "message", chatJid, text: args.text, groupFolder, timestamp: new Date().toISOString() });
        console.log(`[mcp] send_message("${(args.text || "").slice(0, 20)}...") -> 写入 IPC 文件: messages/${filename}`);
        return "Message sent.";
      },
    },
    {
      name: "schedule_task",
      description: "创建定时任务",
      handler: (args) => {
        const filename = writeIpcFile("tasks", { type: "schedule_task", prompt: args.prompt, schedule_type: args.schedule_type, schedule_value: args.schedule_value, context_mode: args.context_mode || "group", targetJid: isMain && args.target_group_jid ? args.target_group_jid : chatJid, timestamp: new Date().toISOString() });
        console.log(`[mcp] schedule_task(${args.schedule_type} "${args.schedule_value}") -> 写入 IPC 文件: tasks/${filename}`);
        return `Task scheduled (${filename})`;
      },
    },
    {
      name: "list_tasks",
      description: "列出所有定时任务",
      handler: () => {
        const mockTasks = [
          { id: "task-001", prompt: "每日早安", schedule_type: "cron", schedule_value: "0 9 * * *", status: "active" },
          { id: "task-002", prompt: "周报提醒", schedule_type: "cron", schedule_value: "0 17 * * 5", status: "active" },
        ];
        console.log(`[mcp] list_tasks() -> 读取 current_tasks.json: ${mockTasks.length} 个任务`);
        return mockTasks.map((t) => `- [${t.id}] ${t.prompt} (${t.schedule_type}: ${t.schedule_value}) - ${t.status}`).join("\n");
      },
    },
    { name: "pause_task", description: "暂停定时任务", handler: (args) => { writeIpcFile("tasks", { type: "pause_task", taskId: args.task_id }); return `Task ${args.task_id} pause requested.`; } },
    { name: "resume_task", description: "恢复定时任务", handler: (args) => { writeIpcFile("tasks", { type: "resume_task", taskId: args.task_id }); return `Task ${args.task_id} resume requested.`; } },
    { name: "cancel_task", description: "取消定时任务", handler: (args) => { writeIpcFile("tasks", { type: "cancel_task", taskId: args.task_id }); return `Task ${args.task_id} cancellation requested.`; } },
    {
      name: "register_group",
      description: "注册新群组（仅主群组）",
      handler: (args) => {
        if (!isMain) return "Error: Only the main group can register new groups.";
        writeIpcFile("tasks", { type: "register_group", jid: args.jid, name: args.name, folder: args.folder, trigger: args.trigger });
        return `Group "${args.name}" registered.`;
      },
    },
  ];
}

// ============================================================
// LEARN: MessageStream — 异步迭代器
// ============================================================
export class MessageStream {
  private queue: string[] = [];
  private waiting: (() => void) | null = null;
  private done = false;

  push(text: string): void {
    this.queue.push(text);
    this.waiting?.();
  }

  end(): void {
    this.done = true;
    this.waiting?.();
  }

  async *[Symbol.asyncIterator](): AsyncGenerator<string> {
    while (true) {
      while (this.queue.length > 0) yield this.queue.shift()!;
      if (this.done) return;
      await new Promise<void>((r) => { this.waiting = r; });
      this.waiting = null;
    }
  }
}

// ============================================================
// LEARN: 模拟 Claude Agent SDK 的 query()
// ============================================================
export async function simulateQuery(
  prompt: string,
  sessionId: string | undefined,
  _mcpTools: McpTool[]
): Promise<{ result: string; newSessionId: string; lastAssistantUuid: string }> {
  console.log(`[agent-runner] 开始查询 (会话: ${sessionId || "new"})`);
  console.log(`[sdk] 收到 prompt: "${prompt.slice(0, 40)}..."`);
  await new Promise((r) => setTimeout(r, 100));

  const isFollowup = prompt.includes("谢谢") || prompt.includes("明天");
  const result = isFollowup ? "明天可能会下雨" : "今天天气不错！";
  const newSessionId = sessionId || `session-new-${Date.now().toString(36)}`;
  console.log(`[sdk] Claude 回复: "${result}"`);

  return { result, newSessionId, lastAssistantUuid: `uuid-${Math.random().toString(36).slice(2, 8)}` };
}

// ============================================================
// LEARN: Hooks 安全机制
// ============================================================
export function demonstrateHooks(): void {
  console.log("--- Hooks 演示 ---");
  const SECRET_ENV_VARS = ["ANTHROPIC_API_KEY", "CLAUDE_CODE_OAUTH_TOKEN"];
  const bashCommand = "echo $ANTHROPIC_API_KEY";
  const sanitized = `unset ${SECRET_ENV_VARS.join(" ")} 2>/dev/null; ${bashCommand}`;
  console.log(`[hook] PreToolUse/Bash: 注入 "unset ${SECRET_ENV_VARS.join(" ")}; " 前缀`);
  console.log(`[hook]   原始命令: ${bashCommand}`);
  console.log(`[hook]   处理后:   ${sanitized}`);
  console.log(`[hook] PreCompact: 归档对话到 conversations/2026-02-26-天气查询.md`);
}

// ============================================================
// 演示
// ============================================================
async function main(): Promise<void> {
  console.log("--- 模拟容器启动 ---");
  const containerInput: ContainerInput = {
    prompt: '<messages>\n<message sender="张三" time="2026-02-26T10:00:00">@Andy 今天天气怎么样？</message>\n</messages>',
    sessionId: "session-abc",
    groupFolder: "test-group",
    chatJid: "chat-123@g.us",
    isMain: false,
    assistantName: "Andy",
    secrets: { ANTHROPIC_API_KEY: "sk-ant-xxx..." },
  };

  console.log(`[agent-runner] 从 stdin 读取输入...`);
  console.log(`[agent-runner] 群组: ${containerInput.groupFolder}, 会话: ${containerInput.sessionId}, 是否主频道: ${containerInput.isMain}`);
  delete containerInput.secrets;
  console.log(`[agent-runner] 删除临时输入文件（含密钥）`);

  console.log("\n--- MCP 工具服务器 ---");
  const mcpTools = createMcpTools(containerInput.chatJid, containerInput.groupFolder, containerInput.isMain);
  console.log(`[mcp] 注册工具: ${mcpTools.map((t) => t.name).join(", ")}`);
  mcpTools.find((t) => t.name === "send_message")!.handler({ text: "你好世界，这是一条测试消息" });
  mcpTools.find((t) => t.name === "schedule_task")!.handler({ prompt: "每日早安", schedule_type: "cron", schedule_value: "0 9 * * *", context_mode: "isolated" });
  mcpTools.find((t) => t.name === "list_tasks")!.handler({});

  console.log("\n--- 查询循环 ---");
  let sessionId = containerInput.sessionId;

  const result1 = await simulateQuery(containerInput.prompt, sessionId, mcpTools);
  sessionId = result1.newSessionId;
  writeOutput({ status: "success", result: result1.result, newSessionId: sessionId });
  console.log(`[agent-runner] 查询 #1 完成，等待 IPC 输入...`);

  // 模拟收到新消息
  const nextMessage = "谢谢！明天呢？";
  console.log(`[agent-runner] 收到新消息: "${nextMessage}"`);
  const result2 = await simulateQuery(nextMessage, sessionId, mcpTools);
  sessionId = result2.newSessionId;
  writeOutput({ status: "success", result: result2.result, newSessionId: sessionId });

  console.log(`[agent-runner] 收到 _close 哨兵，退出`);

  console.log("");
  demonstrateHooks();
  console.log("\n--- 演示结束 ---");
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch(console.error);
}
