import "dotenv/config";

import { prepareRunContext } from "../unit-3-session-context/session-context.js";
import { createAgentRuntime, createLLMFromEnv } from "./agent-loop.js";

const context = prepareRunContext({
  request: {
    runId: "run-loop-1",
    sessionKey: "agent:main:telegram:@teal-user",
    text: "明早提醒我看部署状态"
  },
  config: {
    agents: {
      defaultAgent: "main",
      list: {
        main: { workspace: "~/.openclaw/workspace" }
      }
    }
  },
  workspaceFiles: {
    "AGENTS.md": "默认用中文简洁回复。",
    "SOUL.md": "你是长期运行的个人助理。",
    "USER.md": "用户经常检查部署状态。",
    "MEMORY.md": "提醒类请求默认给出确认。"
  },
  memoryEntries: [{ title: "部署检查", body: "用户通常上午 9 点检查部署。" }],
  skills: [{ name: "calendar", description: "创建提醒", path: "skills/calendar/SKILL.md" }],
  now: "2026-05-06"
});

const runtime = createAgentRuntime({
  llm: createLLMFromEnv(),
  tools: [
    {
      name: "calendar.create",
      description: "创建提醒",
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
    }
  ]
});

const run = await runtime.agent(context);
const waited = await runtime.wait(context.request.runId);

console.log("Agent loop result:");
console.log(run);
console.log("\nagent.wait result:");
console.log(waited);
console.log("\nLifecycle stream:");
console.log(runtime.events());
