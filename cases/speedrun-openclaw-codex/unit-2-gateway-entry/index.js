import { buildGatewayChatContext, resolveGatewayPlan } from "./entry.js";

const plan = resolveGatewayPlan(["node", "openclaw", "agent", "--port", "19090"]);
const ctx = buildGatewayChatContext({
  sessionKey: "agent:main:main",
  text: "Summarize today's channel backlog.",
  runId: "run-demo-1",
  clientId: "dashboard",
  clientName: "Gateway Dashboard"
});

console.log("Gateway plan:");
console.log(plan);
console.log("\nNormalized gateway chat context:");
console.log(ctx);
