import { createGuardedTool, createHookRunner, loadEligibleSkills } from "./tools-safety.js";

const skills = loadEligibleSkills({
  enabledSkills: ["calendar", "deploy"],
  availableBinaries: ["node", "git"],
  skills: [
    { name: "calendar", description: "创建提醒", requires: [] },
    { name: "deploy", description: "读取部署状态", requires: ["git"] },
    { name: "music", description: "控制播放器", requires: ["spotify"] }
  ]
});

const hookRunner = createHookRunner({
  before_tool_call: [
    async (payload) => ({
      ...payload,
      args: {
        ...payload.args,
        auditedBy: "before_tool_call"
      }
    })
  ],
  after_tool_call: [
    async (payload) => ({
      ...payload.result,
      audit: `${payload.toolName} completed under ${payload.policy.decision}`
    })
  ]
});

const calendarTool = createGuardedTool({
  tool: {
    name: "calendar.create",
    async call(args) {
      return { id: "evt-1", ...args };
    }
  },
  hookRunner,
  channelPolicy: { ask: ["calendar.create"], deny: [] },
  sandboxMode: "all"
});

const result = await calendarTool.call(
  { title: "检查部署状态", when: "tomorrow 09:00" },
  { sessionKey: "agent:main:telegram:@teal-user" }
);

console.log("Eligible skills:");
console.log(skills);
console.log("\nGuarded tool result:");
console.log(result);
