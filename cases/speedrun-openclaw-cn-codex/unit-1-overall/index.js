import "dotenv/config";

import {
  createGatewayControlPlane,
  createTelegramChannel,
  createWebChatEnvelope,
  resolveGatewayPlan
} from "../unit-2-gateway-entry/entry.js";
import { prepareRunContext } from "../unit-3-session-context/session-context.js";
import { createAgentRuntime, createLLMFromEnv } from "../unit-4-agent-loop/agent-loop.js";
import { createGuardedTool, createHookRunner, loadEligibleSkills } from "../unit-5-tools-safety/tools-safety.js";
import { createInboundDedupe, createReplyDelivery, deliverRunResult } from "../unit-6-reply-delivery/reply-delivery.js";

// LEARN: Unit 1 keeps all infrastructure in memory so the whole assistant turn
// is easy to inspect. The shape still mirrors OpenClaw: gateway config chooses
// the control plane, and agent config chooses the workspace/session scope.
const config = {
  gateway: {
    port: 18789,
    allowRemote: false
  },
  agents: {
    defaultAgent: "main",
    list: {
      main: {
        workspace: "~/.openclaw/workspace"
      }
    }
  }
};

const workspaceFiles = {
  "AGENTS.md": "默认用中文简洁回复。重要操作先说明风险。",
  "SOUL.md": "你是一个单用户、长期运行的个人助理。",
  "USER.md": "用户负责一个 Node.js 服务，经常在早上检查部署。",
  "MEMORY.md": "偏好：状态类回复先给结论，再给细节。"
};

// LEARN: Memory entries are already "retrieved" records here. Unit 3 will rank
// and insert matching memories into the prompt before Unit 4 calls the model.
const memoryEntries = [
  {
    title: "部署检查",
    body: "用户通常在上午 9 点检查生产部署和错误率。"
  }
];

// LEARN: Skills are not tools yet. A skill says "this capability exists"; Unit 5
// turns an eligible capability into a guarded callable tool.
const skills = loadEligibleSkills({
  enabledSkills: ["calendar", "deploy"],
  availableBinaries: ["node", "git"],
  skills: [
    { name: "calendar", description: "创建提醒", requires: [] },
    { name: "deploy", description: "读取部署状态", requires: ["git"] }
  ]
});

const gateway = createGatewayControlPlane({
  config,
  channels: [createTelegramChannel({ agentId: "main" })]
});

gateway.connect({
  clientId: "local-cli",
  role: "operator",
  local: true
});

function createDelivery() {
  const deliveries = [];
  // LEARN: Delivery is intentionally separate from the agent loop. The model
  // decides what to say, but transport-specific formatting, chunking, and
  // dedupe belong at the reply boundary.
  const delivery = createReplyDelivery({
    transports: {
      telegram: {
        async send(reply) {
          deliveries.push({ provider: "telegram", ...reply });
          return { status: "sent", provider: "telegram", messageId: `${reply.runId}-tg-out` };
        }
      },
      webchat: {
        async send(reply) {
          deliveries.push({ provider: "webchat", ...reply });
          return { status: "sent", provider: "webchat", messageId: `${reply.runId}-web-out` };
        }
      }
    }
  });
  return { delivery, deliveries };
}

function createRuntime({ denyCalendar = false } = {}) {
  // LEARN: Hooks sit between model intent and tool execution. Here the hook adds
  // audit metadata so you can see that even model-requested calls still pass
  // through local policy and extension points.
  const hookRunner = createHookRunner({
    before_tool_call: [
      async (payload) => ({
        ...payload,
        args: {
          ...payload.args,
          auditedBy: "openclaw-speedrun"
        }
      })
    ]
  });

  const calendarTool = createGuardedTool({
    tool: {
      name: "calendar.create",
      description: "创建提醒",
      // LEARN: This JSON Schema is shown to the LLM in real mode. It is also
      // kept on the guarded local tool so the model-facing schema and the
      // executable capability cannot drift apart.
      parameters: {
        type: "object",
        properties: {
          title: { type: "string", description: "提醒标题" },
          when: { type: "string", description: "提醒时间" },
          sessionKey: { type: "string", description: "OpenClaw session key" }
        },
        required: ["title", "when"]
      },
      async call(args) {
        return { id: "evt-1", ...args };
      }
    },
    hookRunner,
    channelPolicy: { ask: [], deny: denyCalendar ? ["calendar.create"] : [] },
    sandboxMode: "all"
  });

  return createAgentRuntime({
    // LEARN: createLLMFromEnv returns undefined by default, so the offline rule
    // backend runs. Setting OPENCLAW_USE_REAL_LLM=true only swaps the generation
    // backend; the same context, guarded tools, session lane, and delivery run.
    llm: createLLMFromEnv(),
    tools: [calendarTool]
  });
}

async function runScenario(name, request, options = {}) {
  // LEARN: Every scenario creates a fresh runtime and delivery sink so the logs
  // show a self-contained assistant turn from gateway request to final send.
  const runtime = createRuntime(options);
  const dedupe = createInboundDedupe();
  const { delivery, deliveries } = createDelivery();

  console.log(`\n=== Scenario: ${name} ===`);
  console.log("[Gateway] normalized request");
  console.log({
    runId: request.runId,
    sessionKey: request.sessionKey,
    idempotencyKey: request.idempotencyKey,
    source: request.source
  });

  const context = prepareRunContext({
    request,
    config,
    workspaceFiles,
    memoryEntries,
    skills,
    now: "2026-05-07"
  });
  console.log("[Context] agent scope + memory hits");
  console.log({
    agentScope: context.agentScope,
    memoryHits: context.memoryHits.map((hit) => hit.title),
    skills: context.skills.map((skill) => skill.name),
    promptBudget: context.promptBudget
  });

  // LEARN: `runtime.agent()` submits and awaits the result promise in this demo.
  // A real gateway can call `submit()` first, then use `agent.wait` from another
  // client to observe the same lifecycle stream.
  const runResult = await runtime.agent(context);
  const waitResult = await runtime.wait(request.runId);
  console.log("[Loop] lifecycle/tool/assistant events");
  console.log({
    waitResult,
    events: runtime.events(),
    payloads: runResult.payloads
  });

  const deliveryResult = await deliverRunResult({
    request,
    runResult,
    dedupe,
    delivery
  });
  console.log("[Delivery] transport result");
  console.log({ deliveryResult, deliveries });
}

console.log("Gateway boot plan:");
console.log(resolveGatewayPlan(["node", "openclaw", "gateway", "--port", "18789"]));

await runScenario(
  "Telegram direct message",
  gateway.receiveChannelMessage({
    channel: "telegram",
    account: "personal",
    messageId: "42",
    sender: "@teal-user",
    chatId: "@teal-user",
    chatType: "direct",
    text: "明早提醒我看部署状态"
  })
);

await runScenario(
  "WebChat control-plane request",
  createWebChatEnvelope({
    sessionKey: "agent:main:main",
    text: "帮我整理今天的发布检查清单",
    clientId: "dashboard",
    requestId: "checklist-1"
  })
);

await runScenario(
  "tool denied failure",
  gateway.receiveChannelMessage({
    channel: "telegram",
    account: "personal",
    messageId: "43",
    sender: "@teal-user",
    chatId: "@teal-user",
    chatType: "direct",
    text: "明早提醒我看部署状态"
  }),
  { denyCalendar: true }
);
