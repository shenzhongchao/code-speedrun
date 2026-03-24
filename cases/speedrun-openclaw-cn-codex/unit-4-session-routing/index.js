import {
  buildAgentPeerSessionKey,
  resolveSendPolicy,
  resolveTurnRoute
} from "./session-routing.js";

const config = {
  agents: { default: "main" },
  session: {
    sendPolicy: {
      default: "allow",
      rules: [{ action: "deny", match: { channel: "slack", chatType: "group" } }]
    }
  }
};

const sessionKey = buildAgentPeerSessionKey({
  agentId: "main",
  channel: "telegram",
  chatType: "direct",
  peerId: "@teal-user"
});

console.log("Session key:", sessionKey);
console.log(
  "Resolved route:",
  resolveTurnRoute({
    config,
    inbound: {
      provider: "telegram",
      chatType: "direct",
      from: "@teal-user",
      accountId: "personal"
    }
  })
);
console.log(
  "Slack group send policy:",
  resolveSendPolicy({ config, channel: "slack", chatType: "group" })
);
