import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { parseInvocation, routeInvocation } from "../unit-2-command-router/index.js";
import { applySetup } from "../unit-3-setup-config/index.js";
import {
  applyOverlay,
  buildRuntimeOverlay,
  detectSkillActivation,
  writeSkillActivationState,
} from "../unit-4-overlay-routing/index.js";
import {
  advancePhase,
  snapshotTeam,
  startTeamRuntime,
} from "../unit-5-team-runtime/index.js";
import {
  captureSnapshot,
  chooseSparkShellRoute,
  createRuntimeBridgeState,
  execRuntimeCommand,
  summarizeLongOutput,
} from "../unit-6-native-boundaries/index.js";

const HERE = dirname(fileURLToPath(import.meta.url));

async function applyLaunchOverlay({ workspaceRoot, userPrompt }) {
  const agentsPath = join(workspaceRoot, "AGENTS.md");
  const activation = detectSkillActivation(userPrompt);
  await writeSkillActivationState({
    stateDir: join(workspaceRoot, ".omx", "state"),
    inputText: userPrompt,
    sessionId: "unit-1-session",
  });

  const overlay = buildRuntimeOverlay({
    activation,
    activeModes: activation.skill === "team" ? ["team"] : [],
    projectMemory: ["Codex stays the execution engine", ".omx stores durable state"],
    codebaseMap: [
      "unit-2-command-router -> argv parsing",
      "unit-3-setup-config -> install prompts/skills/config",
      "unit-4-overlay-routing -> AGENTS runtime overlay",
      "unit-5-team-runtime -> durable team state",
      "unit-6-native-boundaries -> JSON contract to native helpers",
    ],
  });

  const baseAgents = await readFile(agentsPath, "utf8");
  const mergedAgents = applyOverlay(baseAgents, overlay);
  await writeFile(agentsPath, mergedAgents, "utf8");

  return {
    activation,
    overlayPreview: overlay.split("\n").slice(0, 7),
    agentsPath,
  };
}

export async function main() {
  const workspaceRoot = join(HERE, "demo-workspace");
  await rm(workspaceRoot, { recursive: true, force: true });
  await mkdir(workspaceRoot, { recursive: true });

  const setupInvocation = parseInvocation(["setup", "--scope", "project"]);
  const setupSummary = await routeInvocation(setupInvocation, {
    setup: () => applySetup({ workspaceRoot, scope: "project" }),
  });

  const userPrompt =
    "$team stabilize the failing worker handoff and verify the tmux inbox path";
  const launchInvocation = parseInvocation(["--madmax", "--high"]);
  const launchSummary = await routeInvocation(launchInvocation, {
    launch: async (invocation) => ({
      launchArgs: invocation.launchArgs,
      overlay: await applyLaunchOverlay({ workspaceRoot, userPrompt }),
    }),
  });

  const teamInvocation = parseInvocation([
    "team",
    "3:executor",
    "stabilize the failing worker handoff",
  ]);
  const teamRuntime = await routeInvocation(teamInvocation, {
    team: (invocation) =>
      startTeamRuntime({
        workspaceRoot,
        task: invocation.teamArgs.task,
        workerCount: invocation.teamArgs.workerCount,
        agentType: invocation.teamArgs.agentType,
      }),
  });
  teamRuntime.state = advancePhase(teamRuntime.state, "team-prd", "launch approved");
  teamRuntime.state = advancePhase(teamRuntime.state, "team-exec", "workers received tasks");
  teamRuntime.tasks[0].status = "completed";
  teamRuntime.tasks[1].status = "in_progress";
  await writeFile(join(teamRuntime.stateRoot, "phase.json"), JSON.stringify(teamRuntime.state, null, 2));
  await writeFile(join(teamRuntime.stateRoot, "tasks.json"), JSON.stringify(teamRuntime.tasks, null, 2));

  const runtimeBridge = createRuntimeBridgeState();
  const bridgeEvents = [
    execRuntimeCommand(runtimeBridge, {
      command: "AcquireAuthority",
      owner: "leader-fixed",
      lease_id: "lease-unit-1",
      leased_until: "2026-04-07T12:00:00.000Z",
    }),
    execRuntimeCommand(runtimeBridge, {
      command: "QueueDispatch",
      request_id: "dispatch-unit-1",
      target: teamRuntime.workers[0].name,
      metadata: { task_id: teamRuntime.tasks[1].id },
    }),
    execRuntimeCommand(runtimeBridge, {
      command: "MarkNotified",
      request_id: "dispatch-unit-1",
      channel: "tmux",
    }),
  ];

  const sparkRoute = chooseSparkShellRoute("run git status --short");
  const sparkSummary = summarizeLongOutput(
    sparkRoute.argv,
    [
      "M src/cli/index.ts",
      "M src/team/runtime.ts",
      "M src/hooks/agents-overlay.ts",
      "M src/runtime/bridge.ts",
      "?? docs/runtime-team-notes.md",
      "?? docs/queue-contract.md",
      "?? tmp/worker-log.txt",
    ].join("\n"),
  );

  // LEARN: Unit 1 is intentionally thin. Its job is to prove that the subsystems
  // can pass real-looking data across boundaries, not to re-implement every detail.
  console.log(
    JSON.stringify(
      {
        project: "oh-my-codex",
        setup: {
          scope: setupSummary.scope,
          writtenCount: setupSummary.written.length,
          configFile: setupSummary.configFile,
        },
        launch: {
          args: launchSummary.launchArgs,
          skill: launchSummary.overlay.activation.skill,
          overlayPreview: launchSummary.overlay.overlayPreview,
        },
        team: snapshotTeam(teamRuntime),
        nativeBoundary: {
          events: bridgeEvents,
          snapshot: captureSnapshot(runtimeBridge),
          sparkRoute,
          sparkSummary,
        },
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
