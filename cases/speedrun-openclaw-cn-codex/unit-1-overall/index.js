import { buildGatewayChatContext, resolveGatewayPlan } from "../unit-2-gateway-entry/entry.js";
import {
  createChannelManager,
  createChannelRegistry,
  createTelegramPlugin
} from "../unit-3-channel-docking/channel-docking.js";
import { resolveTurnRoute } from "../unit-4-session-routing/session-routing.js";
import {
  createInboundDedupe,
  createReplyDispatcher,
  dispatchInboundTurn,
  makeRuleBasedReply
} from "../unit-5-reply-dispatch/reply-dispatch.js";

const config = {
  gateway: { port: 18789 },
  channels: {
    telegram: {
      accounts: ["personal"]
    }
  },
  agents: {
    default: "main"
  },
  session: {
    mainKey: "main",
    sendPolicy: {
      default: "allow",
      rules: [{ action: "deny", match: { channel: "slack", chatType: "group" } }]
    }
  }
};

const plan = resolveGatewayPlan(["node", "openclaw", "gateway", "--port", "18789"]);
const registry = createChannelRegistry([createTelegramPlugin()]);
const manager = createChannelManager({ registry });
const dedupe = createInboundDedupe();
const deliveries = [];

await manager.startAll(config);

const dispatcher = createReplyDispatcher({
  async deliver(payload) {
    deliveries.push(payload);
  }
});

const telegramInbound = manager.receive({
  channelId: "telegram",
  accountId: "personal",
  rawEvent: {
    messageId: "tg-1",
    sender: "@teal-user",
    senderName: "Teal User",
    chatId: "@teal-user",
    text: "Can you give me a shipping status update?",
    chatType: "direct"
  }
});

const telegramRoute = resolveTurnRoute({
  config,
  inbound: telegramInbound
});

await dispatchInboundTurn({
  inboundContext: telegramInbound,
  route: telegramRoute,
  dispatcher,
  dedupe,
  generateReply: makeRuleBasedReply
});

const controlPlaneInbound = buildGatewayChatContext({
  sessionKey: "agent:main:main",
  text: "Summarize the direct-message architecture.",
  runId: "web-1",
  clientId: "dashboard",
  clientName: "Gateway Dashboard",
  originatingChannel: "internal",
  originatingTo: "webchat"
});

const controlPlaneRoute = resolveTurnRoute({
  config,
  inbound: controlPlaneInbound
});

await dispatchInboundTurn({
  inboundContext: controlPlaneInbound,
  route: controlPlaneRoute,
  dispatcher,
  dedupe,
  generateReply: makeRuleBasedReply
});

console.log("Gateway boot plan:");
console.log(plan);
console.log("\nChannel runtime snapshot:");
console.log(manager.snapshot());
console.log("\nTelegram route:");
console.log(telegramRoute);
console.log("\nControl-plane route:");
console.log(controlPlaneRoute);
console.log("\nFinal deliveries:");
console.log(deliveries);
