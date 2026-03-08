/**
 * Unit 8: Skills Engine — 技能安装、卸载与三方合并
 *
 * 模拟 Skills Engine 的完整生命周期：
 * manifest 解析 → 预检 → 备份 → 合并 → 状态记录 → 卸载回放
 */
import crypto from "crypto";

// ============================================================
// LEARN: 类型定义 — 技能系统的"数据字典"
// ============================================================
interface SkillManifest {
  skill: string;
  version: string;
  description: string;
  core_version: string;
  adds: string[];       // 新增的文件路径
  modifies: string[];   // 修改的文件路径
  structured?: {
    npm_dependencies?: Record<string, string>;
    env_additions?: string[];
  };
  conflicts: string[];  // 与哪些技能冲突
  depends: string[];    // 依赖哪些技能
  test?: string;        // 安装后运行的测试命令
}

interface AppliedSkill {
  name: string;
  version: string;
  applied_at: string;
  file_hashes: Record<string, string>;
}

interface SkillState {
  skills_system_version: string;
  core_version: string;
  applied_skills: AppliedSkill[];
}

// ============================================================
// LEARN: 模拟文件系统 — 用内存对象代替真实文件
// ============================================================
const fileSystem: Record<string, string> = {
  "src/index.ts": 'import { WhatsAppChannel } from "./channels/whatsapp.js";\n// ... 原始代码',
  "src/config.ts": 'export const ASSISTANT_NAME = "Andy";\n// ... 原始配置（用户已手动修改过）',
  "package.json": '{"dependencies": {"better-sqlite3": "^11.8.1"}}',
  ".env.example": "ASSISTANT_NAME=Andy\n",
};

// 基线快照（技能修改前的原始版本）
const baseFiles: Record<string, string> = {
  "src/index.ts": 'import { WhatsAppChannel } from "./channels/whatsapp.js";\n// ... 原始代码',
  "src/config.ts": 'export const ASSISTANT_NAME = "Andy";\n// ... 原始配置',
};

// 备份存储
let backup: Record<string, string> = {};

const state: SkillState = {
  skills_system_version: "0.1.0",
  core_version: "1.1.3",
  applied_skills: [],
};

// ============================================================
// LEARN: Manifest 解析 — 读取技能的"说明书"
// 真实实现从 manifest.yaml 读取，这里用对象模拟
// ============================================================
function readManifest(): SkillManifest {
  return {
    skill: "add-telegram",
    version: "1.0.0",
    description: "Add Telegram as a messaging channel",
    core_version: "1.1.0",
    adds: ["src/channels/telegram.ts"],
    modifies: ["src/index.ts", "src/config.ts"],
    structured: {
      npm_dependencies: { telegraf: "^4.0.0" },
      env_additions: ["TELEGRAM_BOT_TOKEN"],
    },
    conflicts: ["add-signal"],
    depends: [],
    test: "npm test",
  };
}

// ============================================================
// LEARN: 预检 — 安装前的"体检"
// 每一项检查都可能阻止安装，确保不会把系统搞坏
// ============================================================
function checkSystemVersion(manifest: SkillManifest): { ok: boolean; error?: string } {
  // 技能要求的系统版本不能高于当前版本
  const cmp = compareSemver(manifest.core_version, state.core_version);
  if (cmp > 0) {
    return { ok: false, error: `技能要求核心版本 ${manifest.core_version}，当前是 ${state.core_version}` };
  }
  return { ok: true };
}

function checkDependencies(manifest: SkillManifest): { ok: boolean; missing: string[] } {
  const appliedNames = new Set(state.applied_skills.map((s) => s.name));
  const missing = manifest.depends.filter((dep) => !appliedNames.has(dep));
  return { ok: missing.length === 0, missing };
}

function checkConflicts(manifest: SkillManifest): { ok: boolean; conflicting: string[] } {
  const appliedNames = new Set(state.applied_skills.map((s) => s.name));
  const conflicting = manifest.conflicts.filter((c) => appliedNames.has(c));
  return { ok: conflicting.length === 0, conflicting };
}

function compareSemver(a: string, b: string): number {
  const partsA = a.split(".").map(Number);
  const partsB = b.split(".").map(Number);
  for (let i = 0; i < Math.max(partsA.length, partsB.length); i++) {
    const diff = (partsA[i] || 0) - (partsB[i] || 0);
    if (diff !== 0) return diff;
  }
  return 0;
}

// ============================================================
// LEARN: 漂移检测 — 文件是否被手动修改过？
// 比较当前文件的 hash 和基线的 hash
// 如果不一致，说明用户或其他技能修改过，需要三方合并
// ============================================================
function computeHash(content: string): string {
  return crypto.createHash("sha256").update(content).digest("hex").slice(0, 12);
}

function detectDrift(modifies: string[]): string[] {
  const driftFiles: string[] = [];
  for (const relPath of modifies) {
    const current = fileSystem[relPath];
    const base = baseFiles[relPath];
    if (current && base && computeHash(current) !== computeHash(base)) {
      driftFiles.push(relPath);
    }
  }
  return driftFiles;
}

// ============================================================
// LEARN: 三方合并 — 技能安装的核心算法
// 类比：三个人同时编辑一份文档
// - base: 文档的原始版本（共同祖先）
// - current: 你修改后的版本
// - skill: 技能想要的版本
// git merge-file 会自动合并不冲突的部分
//
// 真实实现调用 git merge-file，这里模拟合并结果
// ============================================================
function simulateThreeWayMerge(
  currentContent: string,
  baseContent: string,
  skillContent: string
): { clean: boolean; result: string } {
  // 简化模拟：如果 current 和 base 相同（无漂移），直接用 skill 版本
  // 如果有漂移，模拟成功合并（真实场景可能有冲突）
  if (currentContent === baseContent) {
    return { clean: true, result: skillContent };
  }
  // 模拟：漂移 + 技能修改 = 合并两者的改动
  return {
    clean: true,
    result: currentContent + "\n// --- 技能合并的改动 ---\n" + skillContent.split("\n").slice(1).join("\n"),
  };
}

// ============================================================
// LEARN: 备份与回滚 — 原子性保证
// 安装前备份所有会被修改的文件
// 任何步骤失败 → 从备份恢复 → 清理备份
// ============================================================
function createBackup(files: string[]): void {
  backup = {};
  let count = 0;
  for (const f of files) {
    if (fileSystem[f]) {
      backup[f] = fileSystem[f];
      count++;
    }
  }
  console.log(`[备份] 已备份 ${count} 个文件`);
}

function restoreBackup(): void {
  for (const [f, content] of Object.entries(backup)) {
    fileSystem[f] = content;
  }
  console.log("[备份] 已从备份恢复");
}

function clearBackup(): void {
  backup = {};
  console.log("[备份] 已清理");
}

// ============================================================
// LEARN: applySkill — 完整的安装流程
// 这是 Skills Engine 最核心的函数
// ============================================================
function applySkill(manifest: SkillManifest): { success: boolean; error?: string } {
  // 1. 预检
  const sysCheck = checkSystemVersion(manifest);
  if (!sysCheck.ok) return { success: false, error: sysCheck.error };

  const deps = checkDependencies(manifest);
  if (!deps.ok) return { success: false, error: `缺少依赖: ${deps.missing.join(", ")}` };

  const conflicts = checkConflicts(manifest);
  if (!conflicts.ok) return { success: false, error: `冲突技能: ${conflicts.conflicting.join(", ")}` };

  // 2. 漂移检测
  const driftFiles = detectDrift(manifest.modifies);

  // 3. 备份
  const filesToBackup = [...manifest.modifies, ...manifest.adds, "package.json", ".env.example"];
  createBackup(filesToBackup);

  try {
    // 4. 复制新文件
    for (const relPath of manifest.adds) {
      // 真实实现从 skill/add/ 目录复制
      fileSystem[relPath] = `// ${relPath} — 由技能 ${manifest.skill} 添加\nimport { Telegraf } from "telegraf";\n// ... Telegram 通道实现`;
      console.log(`[安装] 复制新文件: ${relPath}`);
    }

    // 5. 三方合并修改文件
    for (const relPath of manifest.modifies) {
      const current = fileSystem[relPath] || "";
      const base = baseFiles[relPath] || current;
      // 模拟技能想要的版本
      const skillVersion = base + `\nimport { TelegramChannel } from "./channels/telegram.js";`;

      const mergeResult = simulateThreeWayMerge(current, base, skillVersion);

      if (!mergeResult.clean) {
        // 冲突 → 回滚
        restoreBackup();
        clearBackup();
        return { success: false, error: `合并冲突: ${relPath}` };
      }

      const hasDrift = driftFiles.includes(relPath);
      fileSystem[relPath] = mergeResult.result;
      console.log(
        `[合并] ${relPath}: 三方合并 ✅ 无冲突${hasDrift ? " (漂移已自动合并)" : ""}`
      );
    }

    // 6. 结构化操作
    if (manifest.structured?.npm_dependencies) {
      const pkg = JSON.parse(fileSystem["package.json"]);
      pkg.dependencies = { ...pkg.dependencies, ...manifest.structured.npm_dependencies };
      fileSystem["package.json"] = JSON.stringify(pkg);
      const deps = Object.entries(manifest.structured.npm_dependencies)
        .map(([k, v]) => `${k}@${v}`)
        .join(", ");
      console.log(`[结构化] 合并 npm 依赖: ${deps}`);
    }

    if (manifest.structured?.env_additions) {
      for (const env of manifest.structured.env_additions) {
        fileSystem[".env.example"] += `${env}=\n`;
        console.log(`[结构化] 合并 .env: ${env}`);
      }
    }

    console.log("[安装] npm install 完成");

    // 7. 记录状态
    const fileHashes: Record<string, string> = {};
    for (const relPath of [...manifest.adds, ...manifest.modifies]) {
      if (fileSystem[relPath]) {
        fileHashes[relPath] = computeHash(fileSystem[relPath]);
      }
    }

    state.applied_skills.push({
      name: manifest.skill,
      version: manifest.version,
      applied_at: new Date().toISOString(),
      file_hashes: fileHashes,
    });
    console.log(
      `[状态] 记录技能: ${manifest.skill} v${manifest.version}, ${Object.keys(fileHashes).length} 个文件哈希`
    );

    // 8. 清理
    clearBackup();

    return { success: true };
  } catch (err) {
    restoreBackup();
    clearBackup();
    return { success: false, error: String(err) };
  }
}

// ============================================================
// LEARN: uninstallSkill — 卸载流程
// 不能简单撤销 diff，因为后续技能可能依赖这个技能的改动
// 正确做法：从基线重新回放（replay）剩余技能
// ============================================================
function uninstallSkill(skillName: string): { success: boolean; error?: string } {
  const skillEntry = state.applied_skills.find((s) => s.name === skillName);
  if (!skillEntry) {
    return { success: false, error: `技能 "${skillName}" 未安装` };
  }

  console.log(`[卸载] 卸载技能: ${skillName}`);

  // 1. 找出该技能独占的文件（不被其他技能使用）
  const remainingSkills = state.applied_skills.filter((s) => s.name !== skillName);
  const remainingFiles = new Set<string>();
  for (const s of remainingSkills) {
    for (const f of Object.keys(s.file_hashes)) remainingFiles.add(f);
  }

  // 2. 恢复/删除独占文件
  for (const filePath of Object.keys(skillEntry.file_hashes)) {
    if (remainingFiles.has(filePath)) continue;
    if (baseFiles[filePath]) {
      fileSystem[filePath] = baseFiles[filePath];
      console.log(`[卸载] 从基线恢复: ${filePath}`);
    } else {
      delete fileSystem[filePath];
      console.log(`[卸载] 删除独占文件: ${filePath} (删除)`);
    }
  }

  // 3. 回放剩余技能
  if (remainingSkills.length > 0) {
    console.log(`[卸载] 回放剩余技能: ${remainingSkills.map((s) => s.name).join(", ")}`);
    // 真实实现会调用 replaySkills()，从基线开始重新 applySkill
    for (const s of remainingSkills) {
      console.log(`[卸载] 运行测试: ${s.name} ✅`);
    }
  }

  // 4. 更新状态
  state.applied_skills = remainingSkills;
  console.log("[状态] 已更新");

  return { success: true };
}

// ============================================================
// 演示
// ============================================================
function main(): void {
  // --- 解析 Manifest ---
  console.log("--- 解析 Manifest ---");
  const manifest = readManifest();
  console.log(`[manifest] 技能: ${manifest.skill} v${manifest.version}`);
  console.log(`[manifest] 核心版本要求: ${manifest.core_version}`);
  console.log(`[manifest] 新增文件: ${manifest.adds.join(", ")}`);
  console.log(`[manifest] 修改文件: ${manifest.modifies.join(", ")}`);
  console.log(`[manifest] 依赖: ${manifest.depends.length > 0 ? manifest.depends.join(", ") : "(无)"}`);
  console.log(`[manifest] 冲突: ${manifest.conflicts.join(", ")}`);

  // --- 预检 ---
  console.log("\n--- 预检 ---");
  const sysCheck = checkSystemVersion(manifest);
  console.log(`[预检] 系统版本: ${sysCheck.ok ? "✅" : "❌"} ${manifest.core_version} <= ${state.core_version}`);

  const deps = checkDependencies(manifest);
  console.log(`[预检] 依赖检查: ${deps.ok ? "✅ 无缺失" : "❌ 缺失: " + deps.missing.join(", ")}`);

  const conflicts = checkConflicts(manifest);
  console.log(`[预检] 冲突检查: ${conflicts.ok ? "✅ " + manifest.conflicts[0] + " 未安装" : "❌ 冲突"}`);

  // --- 漂移检测 ---
  console.log("\n--- 漂移检测 ---");
  const driftFiles = detectDrift(manifest.modifies);
  for (const relPath of manifest.modifies) {
    const hasDrift = driftFiles.includes(relPath);
    console.log(`[漂移] ${relPath}: ${hasDrift ? "⚠️ 检测到漂移 (将使用三方合并)" : "无漂移 (hash 匹配)"}`);
  }

  // --- 安装技能 ---
  console.log("\n--- 安装技能 ---");
  const result = applySkill(manifest);
  console.log(`[结果] ${result.success ? "✅ 安装成功" : "❌ " + result.error}`);

  // --- 安装第二个技能（用于演示卸载回放）---
  state.applied_skills.push({
    name: "add-slack",
    version: "1.0.0",
    applied_at: new Date().toISOString(),
    file_hashes: { "src/channels/slack.ts": "abc123", "src/index.ts": "def456" },
  });

  // --- 模拟卸载 ---
  console.log("\n--- 模拟卸载 ---");
  const uninstallResult = uninstallSkill("add-telegram");
  console.log(`[结果] ${uninstallResult.success ? "✅ 卸载成功" : "❌ " + uninstallResult.error}`);

  console.log("\n--- 演示结束 ---");
}

main();
