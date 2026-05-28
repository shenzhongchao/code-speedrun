import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

export function createRuntimeBridgeState() {
  return {
    authority: null,
    dispatches: [],
    mailbox: [],
  };
}

export function captureSnapshot(state) {
  return {
    authority: state.authority,
    backlog: {
      pending: state.dispatches.filter((item) => item.status === "pending").length,
      notified: state.dispatches.filter((item) => item.status === "notified").length,
      delivered: state.dispatches.filter((item) => item.status === "delivered").length,
      failed: state.dispatches.filter((item) => item.status === "failed").length,
    },
    replay: {
      cursor: null,
      pending_events: state.dispatches.filter((item) => item.status === "pending").length,
    },
    readiness: {
      ready: state.authority !== null,
      reasons: state.authority ? [] : ["authority not acquired"],
    },
  };
}

export function execRuntimeCommand(state, command) {
  // LEARN: The TypeScript side of OMX talks to Rust through a tiny contract:
  // JSON in, JSON out, and stable command names. That keeps the native seam narrow.
  switch (command.command) {
    case "AcquireAuthority": {
      state.authority = {
        owner: command.owner,
        lease_id: command.lease_id,
        leased_until: command.leased_until,
      };
      return {
        event: "AuthorityAcquired",
        owner: command.owner,
        lease_id: command.lease_id,
      };
    }
    case "QueueDispatch": {
      state.dispatches.push({
        request_id: command.request_id,
        target: command.target,
        status: "pending",
        metadata: command.metadata ?? null,
      });
      return {
        event: "DispatchQueued",
        request_id: command.request_id,
        target: command.target,
      };
    }
    case "MarkNotified": {
      const record = state.dispatches.find((item) => item.request_id === command.request_id);
      if (record) record.status = "notified";
      return {
        event: "DispatchNotified",
        request_id: command.request_id,
        channel: command.channel,
      };
    }
    case "MarkDelivered": {
      const record = state.dispatches.find((item) => item.request_id === command.request_id);
      if (record) record.status = "delivered";
      return {
        event: "DispatchDelivered",
        request_id: command.request_id,
      };
    }
    case "CaptureSnapshot":
      return {
        event: "SnapshotCaptured",
        snapshot: captureSnapshot(state),
      };
    default:
      throw new Error(`Unsupported runtime command: ${command.command}`);
  }
}

function tokenizePrompt(prompt) {
  return prompt.match(/"[^"]*"|'[^']*'|\S+/g)?.map((token) => {
    if (
      (token.startsWith('"') && token.endsWith('"')) ||
      (token.startsWith("'") && token.endsWith("'"))
    ) {
      return token.slice(1, -1);
    }
    return token;
  }) ?? [];
}

export function chooseSparkShellRoute(prompt) {
  const normalized = prompt.trim().replace(/^run\s+/i, "");
  const argv = tokenizePrompt(normalized);
  const [command = "", subcommand = ""] = argv;
  const longOutput =
    (command === "git" && ["status", "diff", "log", "show"].includes(subcommand)) ||
    ["find", "rg", "grep", "ls"].includes(command);

  return {
    argv,
    reason: longOutput ? "long-output" : "shell-native",
  };
}

export function summarizeLongOutput(argv, output, threshold = 6) {
  const lines = output.trim().split(/\r?\n/).filter(Boolean);
  if (lines.length <= threshold) {
    return {
      mode: "raw",
      text: output.trim(),
    };
  }

  return {
    mode: "summary",
    text: [
      `command: ${argv.join(" ")}`,
      `line_count: ${lines.length}`,
      `head: ${lines.slice(0, 2).join(" | ")}`,
      `tail: ${lines.slice(-2).join(" | ")}`,
    ].join("\n"),
  };
}

export async function main() {
  const state = createRuntimeBridgeState();
  const events = [
    execRuntimeCommand(state, {
      command: "AcquireAuthority",
      owner: "leader-fixed",
      lease_id: "lease-001",
      leased_until: "2026-04-07T12:00:00.000Z",
    }),
    execRuntimeCommand(state, {
      command: "QueueDispatch",
      request_id: "dispatch-001",
      target: "worker-1",
      metadata: { task_id: "2" },
    }),
    execRuntimeCommand(state, {
      command: "MarkNotified",
      request_id: "dispatch-001",
      channel: "tmux",
    }),
    execRuntimeCommand(state, {
      command: "CaptureSnapshot",
    }),
  ];

  const sparkRoute = chooseSparkShellRoute("run git status --short");
  const sparkResult = summarizeLongOutput(
    sparkRoute.argv,
    [
      "M src/cli/index.ts",
      "M src/team/runtime.ts",
      "M src/hooks/agents-overlay.ts",
      "?? docs/runtime-contract.md",
      "?? docs/team-phase-audit.md",
      "?? tmp/repro.txt",
      "?? tmp/snapshot.json",
    ].join("\n"),
  );

  console.log(
    JSON.stringify(
      {
        events,
        sparkRoute,
        sparkResult,
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
