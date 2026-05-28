import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

const KNOWN_COMMANDS = new Set([
  "launch",
  "resume",
  "setup",
  "team",
  "sparkshell",
  "help",
]);

export function normalizeTeamArgs(args) {
  const [first = "", ...rest] = args;
  const match = first.match(/^(\d+):([a-z-]+)$/i);

  if (!match) {
    return {
      workerCount: 3,
      agentType: "executor",
      explicitWorkerCount: false,
      explicitAgentType: false,
      task: args.join(" ").trim(),
    };
  }

  return {
    workerCount: Number(match[1]),
    agentType: match[2],
    explicitWorkerCount: true,
    explicitAgentType: true,
    task: rest.join(" ").trim(),
  };
}

export function parseInvocation(argv) {
  const args = [...argv];
  const first = args[0];

  // LEARN: OMX treats a bare flag like `--high` as "launch Codex with flags".
  // That keeps the happy path short: `omx --madmax --high` is still a valid session start.
  if (!first || first.startsWith("--")) {
    return {
      command: "launch",
      rawArgs: args,
      launchArgs: args,
    };
  }

  if (first === "launch" || first === "resume") {
    return {
      command: first,
      rawArgs: args,
      launchArgs: args.slice(1),
    };
  }

  if (first === "team") {
    return {
      command: "team",
      rawArgs: args,
      teamArgs: normalizeTeamArgs(args.slice(1)),
    };
  }

  if (KNOWN_COMMANDS.has(first)) {
    return {
      command: first,
      rawArgs: args,
      commandArgs: args.slice(1),
    };
  }

  return {
    command: "unknown",
    rawArgs: args,
    attemptedCommand: first,
    commandArgs: args.slice(1),
  };
}

export function routeInvocation(invocation, handlers) {
  const handler =
    handlers[invocation.command] ??
    handlers.default ??
    (() => {
      throw new Error(`No handler registered for "${invocation.command}"`);
    });

  // LEARN: The router only chooses "who should handle this".
  // The real work stays inside narrow handlers, which is why OMX can keep adding subcommands.
  return handler(invocation);
}

export function describeInvocation(invocation) {
  if (invocation.command === "launch" || invocation.command === "resume") {
    return `${invocation.command}: ${JSON.stringify(invocation.launchArgs)}`;
  }
  if (invocation.command === "team") {
    return `team: ${invocation.teamArgs.workerCount}x${invocation.teamArgs.agentType} -> ${invocation.teamArgs.task}`;
  }
  if (invocation.command === "unknown") {
    return `unknown: ${invocation.attemptedCommand}`;
  }
  return `${invocation.command}: ${JSON.stringify(invocation.commandArgs ?? [])}`;
}

export function demoSamples() {
  return [
    ["--madmax", "--high"],
    ["setup", "--scope", "project"],
    ["team", "3:executor", "stabilize", "worker", "handoff"],
    ["sparkshell", "git", "status"],
    ["mystery-command"],
  ];
}

export async function main() {
  const results = [];
  for (const sample of demoSamples()) {
    const invocation = parseInvocation(sample);
    const routed = await routeInvocation(invocation, {
      launch: (value) => ({
        target: "launchWithHud",
        args: value.launchArgs,
      }),
      setup: () => ({
        target: "setup",
        scope: "project",
      }),
      team: (value) => ({
        target: "teamCommand",
        workerCount: value.teamArgs.workerCount,
        agentType: value.teamArgs.agentType,
        task: value.teamArgs.task,
      }),
      sparkshell: (value) => ({
        target: "sparkshellCommand",
        args: value.commandArgs,
      }),
      default: (value) => ({
        target: "help",
        reason:
          value.command === "unknown"
            ? `Unknown command ${value.attemptedCommand}`
            : `Unhandled command ${value.command}`,
      }),
    });

    results.push({
      sample,
      parsed: describeInvocation(invocation),
      routed,
    });
  }

  console.log(JSON.stringify(results, null, 2));
}

const isDirectRun =
  process.argv[1] && fileURLToPath(import.meta.url) === resolve(process.argv[1]);

if (isDirectRun) {
  main().catch((error) => {
    console.error(error);
    process.exitCode = 1;
  });
}
