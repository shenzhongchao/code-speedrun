import { fileURLToPath } from "node:url";
import { dirname, join, relative, resolve } from "node:path";
import { mkdir, readFile, rm, writeFile } from "node:fs/promises";

const HERE = dirname(fileURLToPath(import.meta.url));

const SAMPLE_PROMPTS = [
  { name: "planner.md", body: "# planner\nBreak work into explicit steps.\n" },
  { name: "team-executor.md", body: "# team-executor\nFinish your assigned slice and report verification.\n" },
];

const SAMPLE_SKILLS = [
  {
    name: "team",
    body: [
      "---",
      "name: team",
      "description: Coordinate durable multi-worker execution.",
      "---",
      "",
      "# Team",
      "Use durable coordination when one session is not enough.",
      "",
    ].join("\n"),
  },
  {
    name: "ralph",
    body: [
      "---",
      "name: ralph",
      "description: Persist until the work is done.",
      "---",
      "",
      "# Ralph",
      "Keep pushing through verification loops.",
      "",
    ].join("\n"),
  },
];

const SAMPLE_TEMPLATE_AGENTS = `# AGENTS.md

Use $deep-interview for ambiguity, $ralplan for approval, and $team for durable parallel execution.
`;

function readTomlString(content, key) {
  const match = content.match(new RegExp(`^\\s*${key}\\s*=\\s*"([^"]+)"`, "m"));
  return match?.[1];
}

export function buildManagedConfig({
  existingConfig = "",
  modelOverride,
  notifyScript = ".omx/hooks/notify-hook.js",
} = {}) {
  const model = modelOverride ?? readTomlString(existingConfig, "model") ?? "gpt-5.4";
  const lines = [
    "# oh-my-codex managed config",
    `notify = ["node", "${notifyScript}"]`,
    'model_reasoning_effort = "high"',
    `model = "${model}"`,
    "",
    "[features]",
    "multi_agent = true",
    "child_agents_md = true",
    "codex_hooks = true",
    "",
    "[env]",
    'USE_OMX_EXPLORE_CMD = "1"',
    "",
  ];

  // LEARN: The real project carefully edits only the keys it owns.
  // This simplified version keeps the same idea: preserve the user's chosen model unless OMX must override it.
  return lines.join("\n");
}

export function planSetupInstall({ workspaceRoot, scope = "project" }) {
  const codexRoot =
    scope === "project" ? join(workspaceRoot, ".codex") : join(workspaceRoot, "user-codex-home");

  return {
    scope,
    workspaceRoot,
    codexRoot,
    promptsDir: join(codexRoot, "prompts"),
    skillsDir: join(codexRoot, "skills"),
    configFile: join(codexRoot, "config.toml"),
    hooksDir: join(workspaceRoot, ".omx", "hooks"),
    agentsFile: join(workspaceRoot, "AGENTS.md"),
    summaryFile: join(workspaceRoot, ".omx", "setup-summary.json"),
  };
}

async function ensureTextFile(path, content) {
  await mkdir(dirname(path), { recursive: true });
  await writeFile(path, content, "utf8");
}

export async function applySetup({ workspaceRoot, scope = "project" }) {
  const plan = planSetupInstall({ workspaceRoot, scope });
  const existingConfig = await readFile(plan.configFile, "utf8").catch(() => "");
  const config = buildManagedConfig({ existingConfig });
  const written = [];

  await ensureTextFile(plan.configFile, config);
  written.push(relative(workspaceRoot, plan.configFile));

  for (const prompt of SAMPLE_PROMPTS) {
    const target = join(plan.promptsDir, prompt.name);
    await ensureTextFile(target, prompt.body);
    written.push(relative(workspaceRoot, target));
  }

  for (const skill of SAMPLE_SKILLS) {
    const target = join(plan.skillsDir, skill.name, "SKILL.md");
    await ensureTextFile(target, skill.body);
    written.push(relative(workspaceRoot, target));
  }

  await ensureTextFile(join(plan.hooksDir, "notify-hook.js"), "console.log('notify hook placeholder');\n");
  written.push(relative(workspaceRoot, join(plan.hooksDir, "notify-hook.js")));

  // LEARN: Setup is not just "write config.toml".
  // OMX becomes useful only after the prompts, skills, templates, and hook locations all agree on the same filesystem shape.
  await ensureTextFile(plan.agentsFile, SAMPLE_TEMPLATE_AGENTS);
  written.push(relative(workspaceRoot, plan.agentsFile));

  const summary = {
    scope,
    model: readTomlString(config, "model"),
    written,
  };
  await ensureTextFile(plan.summaryFile, JSON.stringify(summary, null, 2));

  return {
    ...plan,
    config,
    written,
  };
}

export async function main() {
  const workspaceRoot = join(HERE, "demo-workspace");
  await rm(workspaceRoot, { recursive: true, force: true });
  const summary = await applySetup({ workspaceRoot, scope: "project" });
  console.log(
    JSON.stringify(
      {
        workspaceRoot,
        configPreview: summary.config.split("\n").slice(0, 8),
        written: summary.written,
      },
      null,
      2,
    ),
  );
}

const isDirectRun =
  process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1]);

if (isDirectRun) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
