/**
 * Unit 1: 端到端主流程 — 组装真实组件
 *
 * 这个文件不再用 console.log 模拟，而是从 Unit 2-7 导入真实组件，
 * 组装成完整的消息处理流程：
 *
 * WhatsApp 消息 → SQLite 存储 → 触发词检查 → 队列调度 →
 * 容器构建 → Agent Runner 查询 → 流式解析 → IPC 处理 → 回复发送
 */
import { fileURLToPath } from "url";

// --- 从各 Unit 导入真实组件 ---
import {
  WhatsAppChannel,
  formatMessages,
  routeOutbound,
  type Channel,
} from "../unit-2-whatsapp-channel/index.js";

import {
  initDb,
  _resetDb,
  storeMessage,
  storeChatMetadata,
  getMessagesSince,
  setRegisteredGroup,
  getAllRegisteredGroups,
  setSession,
  getAllSessions,
  setRouterState,
  getRouterState,
  createTask,
  getDueTasks,
  updateTaskAfterRun,
} from "../unit-3-sqlite-persistence/index.js";

import {
  buildVolumeMounts,
  buildContainerArgs,
  parseStreamOutput,
  CONTAINER_RUNTIME_BIN,
  OUTPUT_START_MARKER,
  OUTPUT_END_MARKER,
} from "../unit-4-container-runner/index.js";

import { GroupQueue } from "../unit-5-group-queue/index.js";

import {
  IpcProcessor,
  calculateNextRunForTask,
} from "../unit-6-ipc-scheduler/index.js";

import {
  createMcpTools,
  simulateQuery,
  writeOutput,
} from "../unit-7-agent-runner/index.js";

import type {
  NewMessage,
  RegisteredGroup,
  ContainerOutput,
} from "../shared/types.js";

// ============================================================
// 配置
// ============================================================
const ASSISTANT_NAME = "Andy";
const MAIN_GROUP_FOLDER = "main";
const TRIGGER_PATTERN = new RegExp(`@${ASSISTANT_NAME}\\b`, "i");

// ============================================================
// LEARN: 系统初始化 — 组装所有组件
// 类比：开店前的准备工作 — 连接数据库、注册群组、启动通道
// ============================================================
function   initSystem(): {
  channels: Channel[];
  wa: WhatsAppChannel;
  queue: GroupQueue;
  ipc: IpcProcessor;
  sessions: Record<string, string>;
} {
  // 1. 初始化 SQLite（真实的，来自 Unit 3）
  _resetDb();
  initDb();
  console.log("[系统] SQLite 数据库已初始化（内存模式）");

  // 2. 注册群组（写入真实数据库）
  const mainJid = "main-channel@g.us";
  const familyJid = "family-chat@g.us";

  setRegisteredGroup(mainJid, {
    name: "主频道",
    folder: MAIN_GROUP_FOLDER,
    trigger: `@${ASSISTANT_NAME}`,
    added_at: new Date().toISOString(),
    requiresTrigger: false, // 主频道不需要触发词
  });
  setRegisteredGroup(familyJid, {
    name: "家庭群",
    folder: "family-chat",
    trigger: `@${ASSISTANT_NAME}`,
    added_at: new Date().toISOString(),
    requiresTrigger: true,
  });
  console.log("[系统] 已注册 2 个群组（写入 SQLite）");

  // 3. 从数据库加载群组（验证持久化）
  const registeredGroups = getAllRegisteredGroups();
  console.log(`[系统] 从数据库加载群组: ${Object.keys(registeredGroups).length} 个`);

  // 4. 加载会话
  const sessions = getAllSessions();

  // 5. 创建 GroupQueue（真实的，来自 Unit 5）
  const queue = new GroupQueue(/* maxConcurrent */ 3);

  // 6. 创建 IPC 处理器（真实的，来自 Unit 6）
  const ipc = new IpcProcessor({
    registeredGroups,
    onCreateTask: (task) => {
      createTask(task);
      console.log(`[IPC→DB] 定时任务已写入数据库: ${task.id}`);
    },
    onSendMessage: (chatJid, text) => {
      // IPC 消息发送 → 通过通道路由
      routeOutbound(channels, chatJid, text).catch((err) =>
        console.log(`[IPC→通道] 发送失败: ${err.message}`)
      );
    },
    onRegisterGroup: (jid, group) => {
      setRegisteredGroup(jid, group);
      console.log(`[IPC→DB] 新群组已写入数据库: ${jid}`);
    },
  });

  // 7. 创建 WhatsApp 通道（真实的，来自 Unit 2）
  const wa = new WhatsAppChannel({
    onMessage: (chatJid, msg) => {
      // LEARN: 消息到达的完整链路
      // WhatsApp 收到消息 → 存入 SQLite → 存聊天元数据 → 入队
      storeMessage({ ...msg, chat_jid: chatJid });
      storeChatMetadata(chatJid, msg.timestamp, undefined, "whatsapp", true);
      console.log(`[链路] 消息已存入 SQLite: ${msg.id}`);

      // 入队（GroupQueue 决定何时处理）
      queue.enqueueMessageCheck(chatJid);
    },
    assistantName: ASSISTANT_NAME,
  });

  const channels: Channel[] = [wa];

  // 8. 设置 GroupQueue 的处理函数 — 这是核心组装点
  queue.setProcessMessagesFn(async (groupJid: string) => {
    return await processGroupMessages(
      groupJid,
      registeredGroups,
      sessions,
      channels,
      ipc
    );
  });

  return { channels, wa, queue, ipc, sessions };
}

// ============================================================
// LEARN: 核心处理函数 — 组装 Unit 2-7 的真实组件
// 这是整个系统的"心脏"，每一步都调用真实实现
// ============================================================
async function processGroupMessages(
  chatJid: string,
  registeredGroups: Record<string, RegisteredGroup>,
  sessions: Record<string, string>,
  channels: Channel[],
  ipc: IpcProcessor
): Promise<boolean> {
  const group = registeredGroups[chatJid];
  if (!group) {
    console.log(`[处理] 未注册的群组: ${chatJid}，跳过`);
    return false;
  }

  const isMainGroup = group.folder === MAIN_GROUP_FOLDER;

  // 1. 从 SQLite 查询新消息（Unit 3 的真实查询）
  const cursor = getRouterState(`cursor:${chatJid}`) || "";
  const missedMessages = getMessagesSince(chatJid, cursor, ASSISTANT_NAME);

  if (missedMessages.length === 0) {
    console.log(`[处理] ${group.folder}: 无新消息`);
    return false;
  }
  console.log(`[处理] ${group.folder}: 发现 ${missedMessages.length} 条新消息`);

  // 2. 触发词检查（非主频道必须包含 @Andy）
  if (!isMainGroup && group.requiresTrigger !== false) {
    const hasTrigger = missedMessages.some((m) =>
      TRIGGER_PATTERN.test(m.content.trim())
    );
    if (!hasTrigger) {
      console.log(`[处理] ${group.folder}: 无触发词，跳过`);
      return false;
    }
    console.log(`[处理] ${group.folder}: 检测到触发词`);
  }

  // 3. 格式化消息为 XML（Unit 2 的真实函数）
  const prompt = formatMessages(missedMessages);
  console.log(`[处理] ${group.folder}: 格式化 ${missedMessages.length} 条消息为 XML`);

  // 4. 更新游标（保存到 SQLite）
  const previousCursor = cursor;
  const newCursor = missedMessages[missedMessages.length - 1].timestamp;
  setRouterState(`cursor:${chatJid}`, newCursor);

  // 5. 构建容器挂载和命令（Unit 4 的真实函数）
  const mounts = buildVolumeMounts(group, isMainGroup);
  const containerName = `nanoclaw-${group.folder}-${Date.now()}`;
  const containerArgs = buildContainerArgs(mounts, containerName);
  console.log(`[容器] ${CONTAINER_RUNTIME_BIN} ${containerArgs.slice(0, 3).join(" ")}... (${mounts.length} 个挂载)`);

  // 6. 容器内部：创建 MCP 工具 + 查询 Claude（Unit 7 的真实函数）
  const mcpTools = createMcpTools(chatJid, group.folder, isMainGroup);
  console.log(`[容器内] MCP 工具就绪: ${mcpTools.map((t) => t.name).join(", ")}`);

  const sessionId = sessions[group.folder];
  const queryResult = await simulateQuery(prompt, sessionId, mcpTools);

  // 7. 更新会话（写入 SQLite）
  sessions[group.folder] = queryResult.newSessionId;
  setSession(group.folder, queryResult.newSessionId);

  // 8. 构造容器输出并通过哨兵标记解析（Unit 4 的真实解析器）
  const rawStream = [
    "Agent processing...\n",
    `${OUTPUT_START_MARKER}${JSON.stringify({
      status: "success",
      result: queryResult.result,
      newSessionId: queryResult.newSessionId,
    } as ContainerOutput)}${OUTPUT_END_MARKER}\n`,
  ].join("");

  const outputs = parseStreamOutput(rawStream);
  console.log(`[解析] 从流式输出中提取到 ${outputs.length} 个结果`);

  // 9. 处理每个输出
  for (const output of outputs) {
    if (output.status === "success" && output.result) {
      // 通过真实通道发送回复（Unit 2 的路由）
      await routeOutbound(channels, chatJid, output.result);
    } else if (output.status === "error") {
      console.log(`[处理] 容器返回错误: ${output.error}`);
      // 回滚游标
      setRouterState(`cursor:${chatJid}`, previousCursor);
    }
  }

  return true;
}

// ============================================================
// LEARN: 调度器检查 — 组合 Unit 3 和 Unit 6
// ============================================================
async function runSchedulerCheck(
  registeredGroups: Record<string, RegisteredGroup>,
  queue: GroupQueue,
  channels: Channel[]
): Promise<void> {
  // 从 SQLite 查询到期任务（Unit 3 的真实查询）
  const dueTasks = getDueTasks();
  if (dueTasks.length === 0) {
    console.log("[调度器] 没有到期任务");
    return;
  }

  console.log(`[调度器] 发现 ${dueTasks.length} 个到期任务`);

  for (const task of dueTasks) {
    console.log(`[调度器] 入队任务 ${task.id}: "${task.prompt}"`);

    // 通过 GroupQueue 调度（Unit 5 的真实队列）
    queue.enqueueTask(task.chat_jid, task.id, async () => {
      console.log(`[调度器] 执行任务 ${task.id}`);

      // 计算下次运行时间（Unit 6 的真实计算）
      const nextRun = calculateNextRunForTask(task);

      // 更新数据库（Unit 3 的真实写入）
      updateTaskAfterRun(task.id, nextRun, "completed");
      console.log(
        `[调度器] 任务 ${task.id} 完成，下次运行: ${nextRun?.slice(0, 19) || "(无)"}`
      );
    });
  }
}

// ============================================================
// 演示 — 端到端流程
// ============================================================
async function main(): Promise<void> {
  console.log("========================================");
  console.log("  NanoClaw 端到端流程（真实组件组装）");
  console.log("========================================\n");

  // --- 初始化 ---
  const { wa, queue, ipc, sessions } = initSystem();
  await wa.connect();
  console.log("[系统] WhatsApp 通道已连接\n");

  // --- 场景 1: 普通群组消息（需要触发词）---
  console.log("=== 场景 1: 普通群组消息（需要触发词）===");
  console.log("[模拟] 张三在家庭群发送: @Andy 今天天气怎么样？\n");

  wa.simulateIncomingMessage(
    "family-chat@g.us",
    "张三",
    "@Andy 今天天气怎么样？"
  );

  // 等待 GroupQueue 处理完成
  await new Promise((r) => setTimeout(r, 500));

  // --- 场景 2: 无触发词的消息（应被跳过）---
  console.log("\n=== 场景 2: 无触发词的消息（应被跳过）===");
  console.log("[模拟] 李四在家庭群发送: 今天中午吃什么？\n");

  wa.simulateIncomingMessage(
    "family-chat@g.us",
    "李四",
    "今天中午吃什么？"
  );
  await new Promise((r) => setTimeout(r, 300));

  // --- 场景 3: 主频道消息（不需要触发词）---
  console.log("\n=== 场景 3: 主频道消息（不需要触发词）===");
  console.log("[模拟] 王五在主频道发送: 帮我查一下项目进度\n");

  wa.simulateIncomingMessage(
    "main-channel@g.us",
    "王五",
    "帮我查一下项目进度"
  );
  await new Promise((r) => setTimeout(r, 500));

  // --- 场景 4: IPC 处理（容器发来的消息）---
  console.log("\n=== 场景 4: IPC 消息处理 ===");
  const registeredGroups = getAllRegisteredGroups();

  console.log("[模拟] 主群组容器通过 IPC 创建定时任务\n");
  ipc.process(
    {
      type: "schedule_task",
      prompt: "发送每日早安",
      schedule_type: "cron",
      schedule_value: "0 9 * * 1-5",
      targetJid: "main-channel@g.us",
    },
    MAIN_GROUP_FOLDER,
    true
  );

  console.log("\n[模拟] 非主群组尝试跨组发送消息（应被拦截）\n");
  ipc.process(
    { type: "message", chatJid: "main-channel@g.us", text: "偷偷发消息" },
    "family-chat",
    false
  );

  console.log("\n[模拟] 主群组通过 IPC 注册新群组\n");
  ipc.process(
    {
      type: "register_group",
      jid: "work@g.us",
      name: "工作群",
      folder: "work-chat",
      trigger: "@Andy",
    },
    MAIN_GROUP_FOLDER,
    true
  );

  // --- 场景 5: 调度器检查 ---
  console.log("\n=== 场景 5: 调度器检查 ===");

  // 创建一个已到期的任务
  createTask({
    id: "task-morning",
    group_folder: MAIN_GROUP_FOLDER,
    chat_jid: "main-channel@g.us",
    prompt: "发送每日早安",
    schedule_type: "cron",
    schedule_value: "0 9 * * 1-5",
    context_mode: "isolated",
    next_run: new Date(Date.now() - 60000).toISOString(), // 已过期
    status: "active",
    created_at: new Date().toISOString(),
  });
  console.log("[模拟] 创建了一个已到期的定时任务\n");

  const updatedGroups = getAllRegisteredGroups();
  await runSchedulerCheck(updatedGroups, queue, [wa]);
  await new Promise((r) => setTimeout(r, 300));

  // --- 场景 6: 断线队列 ---
  console.log("\n=== 场景 6: 断线消息队列 ===");
  wa.simulateDisconnect();
  console.log("[模拟] WhatsApp 断线");
  await wa.sendMessage("family-chat@g.us", "这条消息会被缓存");
  console.log(`[通道] 队列中有 ${wa.getQueueLength()} 条待发消息`);
  await wa.simulateReconnect();
  console.log("[模拟] WhatsApp 重连，队列已清空\n");

  // --- 验证数据库状态 ---
  console.log("=== 最终状态验证 ===");
  const finalGroups = getAllRegisteredGroups();
  const finalSessions = getAllSessions();
  console.log(`[数据库] 已注册群组: ${Object.keys(finalGroups).length} 个 (${Object.values(finalGroups).map((g) => g.folder).join(", ")})`);
  console.log(`[数据库] 活跃会话: ${Object.keys(finalSessions).length} 个`);
  for (const [folder, sid] of Object.entries(finalSessions)) {
    console.log(`[数据库]   ${folder}: ${sid}`);
  }

  console.log("\n========================================");
  console.log("  演示结束");
  console.log("========================================");
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch(console.error);
}
