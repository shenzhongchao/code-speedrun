import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { mkdir, readFile, rm, writeFile } from "node:fs/promises";

const HERE = dirname(fileURLToPath(import.meta.url));
const OVERLAY_START = "<!-- OMX:RUNTIME:START -->";
const OVERLAY_END = "<!-- OMX:RUNTIME:END -->";

const KEYWORD_TRIGGER_DEFINITIONS = [
  { keyword: "$ralph", skill: "ralph", priority: 11, guidance: "Activate the persistence loop." },
  { keyword: "$team", skill: "team", priority: 10, guidance: "Activate durable team orchestration." },
  { keyword: "$deep-interview", skill: "deep-interview", priority: 10, guidance: "Ask clarifying questions first." },
  { keyword: "plan this", skill: "plan", priority: 7, guidance: "Activate planning before coding." },
  { keyword: "keep going", skill: "ralph", priority: 6, guidance: "Stay in execution mode until verification is done." },
  { keyword: "parallel", skill: "team", priority: 5, guidance: "Coordinate multiple workers." },
];

export function detectSkillActivation(text) {
  const trimmed = text.trim();
  const explicit = trimmed.match(/\$([a-z][a-z0-9-]*)/i);
  if (explicit) {
    const skill = explicit[1].toLowerCase();
    return {
      skill: skill === "swarm" ? "team" : skill,
      keyword: explicit[0],
      priority: 100,
      guidance: "Explicit skill invocation wins over fuzzy keyword matches.",
    };
  }

  const match = [...KEYWORD_TRIGGER_DEFINITIONS]
    .sort((a, b) => b.priority - a.priority || b.keyword.length - a.keyword.length)
    .find((entry) => trimmed.toLowerCase().includes(entry.keyword.toLowerCase()));

  return (
    match ?? {
      skill: "default",
      keyword: "(none)",
      priority: 0,
      guidance: "No keyword matched; OMX stays in its default mode.",
    }
  );
}

export async function writeSkillActivationState({ stateDir, inputText, sessionId = "demo-session" }) {
  const activation = detectSkillActivation(inputText);
  const now = new Date().toISOString();
  const payload = {
    version: 1,
    active: activation.skill !== "default",
    skill: activation.skill,
    keyword: activation.keyword,
    phase: activation.skill === "deep-interview" ? "planning" : "executing",
    activated_at: now,
    updated_at: now,
    session_id: sessionId,
  };

  await mkdir(stateDir, { recursive: true });
  await writeFile(join(stateDir, "skill-active-state.json"), JSON.stringify(payload, null, 2));
  return payload;
}

export function buildRuntimeOverlay({
  codebaseMap,
  activeModes = [],
  projectMemory = [],
  activation,
}) {
  const sections = [
    "## OMX Runtime Overlay",
    activation
      ? `- Active skill: ${activation.skill} from "${activation.keyword}"`
      : "- Active skill: none",
    activeModes.length > 0 ? `- Active modes: ${activeModes.join(", ")}` : "- Active modes: default",
    projectMemory.length > 0 ? `- Project memory: ${projectMemory.join(" | ")}` : "- Project memory: none",
    "- Codebase map:",
    ...codebaseMap.map((line) => `  - ${line}`),
  ];

  return [OVERLAY_START, sections.join("\n"), OVERLAY_END].join("\n");
}

export function applyOverlay(agentsText, overlayText) {
  const withoutExisting = agentsText.replace(
    new RegExp(`${OVERLAY_START}[\\s\\S]*?${OVERLAY_END}\\n?`, "g"),
    "",
  ).trimEnd();

  // LEARN: Marker-bounded overlays are cheap to regenerate.
  // OMX can safely re-apply them per session without permanently hand-editing the learner's AGENTS.md.
  return `${withoutExisting}\n\n${overlayText}\n`;
}

export async function main() {
  const workspaceRoot = join(HERE, "demo-workspace");
  const agentsPath = join(workspaceRoot, "AGENTS.md");
  await rm(workspaceRoot, { recursive: true, force: true });
  await mkdir(join(workspaceRoot, ".omx", "state"), { recursive: true });
  await writeFile(
    agentsPath,
    "# AGENTS.md\n\nStart with clarification when intent is vague.\n",
    "utf8",
  );

  const inputText = "$team stabilize the worker handoff and keep verification tight";
  const activation = await writeSkillActivationState({
    stateDir: join(workspaceRoot, ".omx", "state"),
    inputText,
  });
  const overlay = buildRuntimeOverlay({
    codebaseMap: ["src/cli -> command router", "src/hooks -> overlay + keyword logic", "src/team -> durable runtime"],
    activeModes: ["team"],
    projectMemory: ["Node.js CLI", "tmux-backed workers", "skills live under .codex/skills"],
    activation,
  });
  const merged = applyOverlay(await readFile(agentsPath, "utf8"), overlay);
  await writeFile(agentsPath, merged, "utf8");

  console.log(
    JSON.stringify(
      {
        activation,
        overlayPreview: overlay.split("\n").slice(0, 8),
        agentsPath,
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
