/**
 * Unit 4: 容器运行器 — 容器挂载、进程生成与流式输出
 *
 * 模拟 Docker 容器的生命周期：挂载构建 → 命令生成 → 进程执行 → 流式输出解析
 */
import { fileURLToPath } from "url";
import type { RegisteredGroup, ContainerOutput } from "../shared/types.js";
import { OUTPUT_START_MARKER, OUTPUT_END_MARKER } from "../shared/types.js";

export type { ContainerOutput };
export { OUTPUT_START_MARKER, OUTPUT_END_MARKER };

// ============================================================
// LEARN: 配置常量 — 容器运行的"规格参数"
// ============================================================
export const CONTAINER_IMAGE = "nanoclaw-agent:latest";
export const CONTAINER_TIMEOUT = 1800000;
export const IDLE_TIMEOUT = 1800000;
export const CONTAINER_MAX_OUTPUT_SIZE = 10 * 1024 * 1024;
export const TIMEZONE = "Asia/Shanghai";
export const CONTAINER_RUNTIME_BIN = "docker";

// ============================================================
// LEARN: 卷挂载 — 容器能看到什么文件，完全由挂载决定
// ============================================================
export interface VolumeMount {
  hostPath: string;
  containerPath: string;
  readonly: boolean;
}

export function buildVolumeMounts(
  group: RegisteredGroup,
  isMain: boolean,
  projectRoot = "/project",
  groupsDir = "/groups",
  dataDir = "/data"
): VolumeMount[] {
  const mounts: VolumeMount[] = [];

  if (isMain) {
    mounts.push({ hostPath: projectRoot, containerPath: "/workspace/project", readonly: true });
    mounts.push({ hostPath: `${groupsDir}/${group.folder}`, containerPath: "/workspace/group", readonly: false });
  } else {
    mounts.push({ hostPath: `${groupsDir}/${group.folder}`, containerPath: "/workspace/group", readonly: false });
    mounts.push({ hostPath: `${groupsDir}/global`, containerPath: "/workspace/global", readonly: true });
  }

  mounts.push({ hostPath: `${dataDir}/sessions/${group.folder}/.claude`, containerPath: "/home/node/.claude", readonly: false });
  mounts.push({ hostPath: `${dataDir}/ipc/${group.folder}`, containerPath: "/workspace/ipc", readonly: false });
  mounts.push({ hostPath: `${dataDir}/sessions/${group.folder}/agent-runner-src`, containerPath: "/app/src", readonly: false });

  return mounts;
}

// ============================================================
// LEARN: Docker 命令构建
// ============================================================
export function buildContainerArgs(
  mounts: VolumeMount[],
  containerName: string
): string[] {
  const args: string[] = ["run", "-i", "--rm", "--name", containerName];
  args.push("-e", `TZ=${TIMEZONE}`);
  for (const mount of mounts) {
    const suffix = mount.readonly ? ":ro" : "";
    args.push("-v", `${mount.hostPath}:${mount.containerPath}${suffix}`);
  }
  args.push(CONTAINER_IMAGE);
  return args;
}

// ============================================================
// LEARN: 流式输出解析 — 从字节流中提取结构化数据
// ============================================================
export function parseStreamOutput(rawStream: string): ContainerOutput[] {
  const results: ContainerOutput[] = [];
  let buffer = rawStream;

  while (true) {
    const startIdx = buffer.indexOf(OUTPUT_START_MARKER);
    if (startIdx === -1) break;
    const endIdx = buffer.indexOf(OUTPUT_END_MARKER, startIdx);
    if (endIdx === -1) break;

    const jsonStr = buffer.slice(startIdx + OUTPUT_START_MARKER.length, endIdx).trim();
    buffer = buffer.slice(endIdx + OUTPUT_END_MARKER.length);

    try {
      results.push(JSON.parse(jsonStr));
    } catch (err) {
      console.log(`[解析] JSON 解析失败: ${err}`);
    }
  }

  return results;
}

// ============================================================
// LEARN: 容器生命周期模拟
// ============================================================
export async function simulateContainerRun(
  group: RegisteredGroup,
  isMain: boolean,
  shouldTimeout = false
): Promise<ContainerOutput | null> {
  const containerName = `nanoclaw-${group.folder}-${Date.now()}`;
  const mounts = buildVolumeMounts(group, isMain);
  const _args = buildContainerArgs(mounts, containerName);

  console.log(`[容器] 启动容器 ${containerName}`);

  if (shouldTimeout) {
    console.log(`[容器] 超时！正在优雅停止...`);
    console.log(`[容器] 执行: ${CONTAINER_RUNTIME_BIN} stop ${containerName}`);
    console.log(`[容器] 容器退出，代码: 137 (被杀)`);
    return null;
  }

  const simulatedStdout = [
    "Agent starting up...\n",
    "Processing query...\n",
    `${OUTPUT_START_MARKER}{"status":"success","result":"这是智能体的回复","newSessionId":"session-new-123"}${OUTPUT_END_MARKER}\n`,
    "Cleanup complete.\n",
  ].join("");

  console.log("[容器] 收到数据块...");
  const outputs = parseStreamOutput(simulatedStdout);

  for (const output of outputs) {
    console.log("[解析] 找到输出标记对，解析 JSON...");
    console.log(`[输出] status=${output.status}, result="${output.result}"`);
    if (output.newSessionId) {
      console.log(`[输出] 新会话 ID: ${output.newSessionId}`);
    }
  }

  await new Promise((r) => setTimeout(r, 5));
  console.log(`[容器] 容器退出，代码: 0，耗时: 205ms`);
  return outputs[0] || null;
}

// ============================================================
// LEARN: 密钥传递 — 通过 stdin 而非环境变量
// ============================================================
export function demonstrateSecretPassing(): void {
  console.log("--- 密钥传递机制 ---");
  const input: any = {
    prompt: "用户的问题",
    groupFolder: "main",
    chatJid: "chat@g.us",
    isMain: true,
    secrets: { ANTHROPIC_API_KEY: "sk-ant-xxx..." },
  };
  console.log("[密钥] 通过 stdin 传递密钥到容器");
  console.log(`[密钥] 传递的键: ${Object.keys(input.secrets).join(", ")}`);
  delete input.secrets;
  console.log("[密钥] 已从 input 对象中删除密钥（不会出现在日志中）");
  console.log(`[密钥] input.secrets = ${input.secrets}`);
}

// ============================================================
// 演示
// ============================================================
async function main(): Promise<void> {
  const mainGroup: RegisteredGroup = { name: "主频道", folder: "main", trigger: "@Andy", added_at: new Date().toISOString() };
  const familyGroup: RegisteredGroup = { name: "家庭群", folder: "family", trigger: "@Andy", added_at: new Date().toISOString() };

  console.log("--- 构建挂载列表 (主群组) ---");
  const mainMounts = buildVolumeMounts(mainGroup, true);
  for (const m of mainMounts) console.log(`[挂载] ${m.hostPath} -> ${m.containerPath} (${m.readonly ? "只读" : "读写"})`);

  console.log("--- 构建挂载列表 (普通群组) ---");
  const familyMounts = buildVolumeMounts(familyGroup, false);
  for (const m of familyMounts) console.log(`[挂载] ${m.hostPath} -> ${m.containerPath} (${m.readonly ? "只读" : "读写"})`);

  console.log("--- 构建 Docker 命令 ---");
  const args = buildContainerArgs(mainMounts, "nanoclaw-main-xxx");
  console.log(`[命令] ${CONTAINER_RUNTIME_BIN} ${args.join(" ").slice(0, 100)}...`);

  console.log("--- 模拟容器执行 (流式输出) ---");
  await simulateContainerRun(mainGroup, true);

  console.log("--- 模拟超时场景 ---");
  await simulateContainerRun(familyGroup, false, true);

  demonstrateSecretPassing();
  console.log("--- 演示结束 ---");
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  main().catch(console.error);
}
