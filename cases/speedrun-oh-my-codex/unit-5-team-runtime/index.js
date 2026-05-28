import { fileURLToPath } from "node:url";
import { dirname, join, resolve } from "node:path";
import { mkdir, rm, writeFile } from "node:fs/promises";

const HERE = dirname(fileURLToPath(import.meta.url));
const TERMINAL_PHASES = new Set(["complete", "failed", "cancelled"]);

export function sanitizeTeamName(value) {
  return value
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
}

export function createTeamState(taskDescription, maxFixAttempts = 2) {
  return {
    active: true,
    phase: "team-plan",
    task_description: taskDescription,
    created_at: new Date().toISOString(),
    phase_transitions: [],
    max_fix_attempts: maxFixAttempts,
    current_fix_attempt: 0,
  };
}

export function advancePhase(state, target, reason = "manual-demo") {
  if (TERMINAL_PHASES.has(state.phase)) {
    throw new Error(`Cannot transition from terminal phase ${state.phase}`);
  }

  const allowed = {
    "team-plan": ["team-prd"],
    "team-prd": ["team-exec"],
    "team-exec": ["team-verify"],
    "team-verify": ["team-fix", "complete", "failed"],
    "team-fix": ["team-exec", "complete", "failed"],
  };

  if (!allowed[state.phase].includes(target)) {
    throw new Error(`Invalid transition: ${state.phase} -> ${target}`);
  }

  const nextFixAttempt =
    target === "team-fix" ? state.current_fix_attempt + 1 : state.current_fix_attempt;
  const phase = target === "team-fix" && nextFixAttempt > state.max_fix_attempts ? "failed" : target;

  return {
    ...state,
    phase,
    active: !TERMINAL_PHASES.has(phase),
    current_fix_attempt: nextFixAttempt,
    phase_transitions: [
      ...state.phase_transitions,
      {
        from: state.phase,
        to: phase,
        at: new Date().toISOString(),
        reason,
      },
    ],
  };
}

function buildTasks(task, agentType) {
  return [
    {
      id: "1",
      subject: "Clarify the task and break it into chunks",
      ownerRole: "planner",
      status: "pending",
    },
    {
      id: "2",
      subject: task,
      ownerRole: agentType,
      status: "pending",
    },
    {
      id: "3",
      subject: "Verify the change and collect evidence",
      ownerRole: "verifier",
      status: "pending",
    },
  ];
}

function buildWorkers(workerCount, stateRoot, teamName) {
  return Array.from({ length: workerCount }, (_, index) => {
    const workerName = `worker-${index + 1}`;
    return {
      name: workerName,
      worktreePath: join(stateRoot, "worktrees", workerName),
      inboxPath: join(stateRoot, "inbox", `${workerName}.md`),
      assignedTasks: [],
      teamName,
    };
  });
}

async function persistRuntime(runtime) {
  await mkdir(runtime.stateRoot, { recursive: true });
  await mkdir(join(runtime.stateRoot, "worktrees"), { recursive: true });
  await mkdir(join(runtime.stateRoot, "inbox"), { recursive: true });
  await writeFile(join(runtime.stateRoot, "manifest.json"), JSON.stringify(runtime.manifest, null, 2));
  await writeFile(join(runtime.stateRoot, "tasks.json"), JSON.stringify(runtime.tasks, null, 2));
  await writeFile(join(runtime.stateRoot, "workers.json"), JSON.stringify(runtime.workers, null, 2));
  await writeFile(join(runtime.stateRoot, "phase.json"), JSON.stringify(runtime.state, null, 2));
}

export function snapshotTeam(runtime) {
  const counts = {
    pending: 0,
    in_progress: 0,
    completed: 0,
    failed: 0,
  };

  for (const task of runtime.tasks) {
    counts[task.status] = (counts[task.status] ?? 0) + 1;
  }

  return {
    teamName: runtime.teamName,
    phase: runtime.state.phase,
    workerCount: runtime.workers.length,
    tasks: counts,
    worktrees: runtime.workers.map((worker) => worker.worktreePath),
  };
}

export async function startTeamRuntime({
  workspaceRoot,
  task,
  workerCount = 3,
  agentType = "executor",
}) {
  const teamName = sanitizeTeamName(task).slice(0, 32) || "demo-team";
  const stateRoot = join(workspaceRoot, ".omx", "team", teamName);
  const tasks = buildTasks(task, agentType);
  const workers = buildWorkers(workerCount, stateRoot, teamName);

  for (let index = 0; index < tasks.length; index += 1) {
    const worker = workers[index % workers.length];
    worker.assignedTasks.push(tasks[index].id);
  }

  const manifest = {
    team_name: teamName,
    requested_task: task,
    requested_workers: workerCount,
    agent_type: agentType,
    state_root: stateRoot,
  };

  const runtime = {
    teamName,
    stateRoot,
    manifest,
    state: createTeamState(task),
    tasks,
    workers,
  };

  // LEARN: Team mode needs a durable state root because the leader, workers,
  // tmux panes, and later verification steps must all agree on the same files.
  await persistRuntime(runtime);
  return runtime;
}

export async function main() {
  const workspaceRoot = join(HERE, "demo-workspace");
  await rm(workspaceRoot, { recursive: true, force: true });

  const runtime = await startTeamRuntime({
    workspaceRoot,
    task: "stabilize the failing worker handoff",
    workerCount: 3,
    agentType: "executor",
  });

  runtime.state = advancePhase(runtime.state, "team-prd", "scope approved");
  runtime.state = advancePhase(runtime.state, "team-exec", "plan converted to tasks");
  runtime.tasks[0].status = "completed";
  runtime.tasks[1].status = "in_progress";
  await writeFile(join(runtime.stateRoot, "phase.json"), JSON.stringify(runtime.state, null, 2));
  await writeFile(join(runtime.stateRoot, "tasks.json"), JSON.stringify(runtime.tasks, null, 2));

  console.log(JSON.stringify(snapshotTeam(runtime), null, 2));
}

const isDirectRun =
  process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1]);

if (isDirectRun) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
