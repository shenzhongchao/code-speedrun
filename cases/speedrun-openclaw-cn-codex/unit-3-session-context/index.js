import { prepareRunContext } from "./session-context.js";

const context = prepareRunContext({
  request: {
    runId: "run-1",
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
    "AGENTS.md": "默认用中文简洁回复。重要操作先说明风险。",
    "SOUL.md": "你是一个单用户、长期运行的个人助理。",
    "USER.md": "用户负责一个 Node.js 服务，经常在早上检查部署。",
    "MEMORY.md": "偏好：状态类回复先给结论，再给细节。"
  },
  memoryEntries: [
    {
      title: "部署检查",
      body: "用户通常在上午 9 点检查生产部署和错误率。"
    },
    {
      title: "购物清单",
      body: "牛奶、咖啡豆、洗衣液。"
    }
  ],
  skills: [
    {
      name: "calendar",
      description: "创建和查询日程提醒",
      path: "~/.openclaw/workspace/skills/calendar/SKILL.md"
    }
  ],
  now: "2026-05-06"
});

console.log("Agent scope:");
console.log(context.agentScope);
console.log("\nMemory hits:");
console.log(context.memoryHits);
console.log("\nTranscript sent to the agent loop:");
console.log(context.transcript);
