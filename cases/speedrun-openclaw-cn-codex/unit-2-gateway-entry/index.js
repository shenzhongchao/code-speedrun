import {
  createFeishuChannel,
  createGatewayControlPlane,
  createSlackChannel,
  createTelegramChannel,
  createWebChatEnvelope,
  resolveGatewayPlan,
  validateConnection
} from "./entry.js";

const config = {
  gateway: {
    port: 18789,
    allowRemote: false
  }
};

const gateway = createGatewayControlPlane({
  config,
  channels: [
    createTelegramChannel({ agentId: "main" }),
    createSlackChannel({ agentId: "main" }),
    createFeishuChannel({ agentId: "main", verificationToken: "verify-token" })
  ]
});

const connection = gateway.connect({
  clientId: "local-cli",
  role: "operator",
  local: true
});

const webTurn = gateway.submitAgentTurn({
  text: "帮我整理今天的发布检查清单",
  sessionKey: "agent:main:main"
});

const telegramTurn = gateway.receiveChannelMessage({
  channel: "telegram",
  account: "personal",
  messageId: "42",
  sender: "@teal-user",
  chatId: "@teal-user",
  chatType: "direct",
  text: "明早提醒我看部署状态"
});

const slackTurn = gateway.receiveChannelMessage({
  channel: "slack",
  teamId: "T1",
  channelId: "C1",
  threadId: "1700.42",
  userId: "U1",
  text: "ship status?"
});

const feishuChannel = createFeishuChannel({ agentId: "main", verificationToken: "verify-token" });
const feishuChallenge = feishuChannel.handleEvent({
  type: "url_verification",
  token: "verify-token",
  challenge: "challenge-from-feishu"
});
const feishuEvent = feishuChannel.handleEvent({
  schema: "2.0",
  header: {
    event_id: "evt-demo-1",
    event_type: "im.message.receive_v1",
    token: "verify-token",
    tenant_key: "tenant-demo"
  },
  event: {
    sender: {
      sender_id: { open_id: "ou_demo_user" },
      sender_type: "user"
    },
    message: {
      message_id: "om_demo_msg",
      chat_id: "oc_demo_chat",
      chat_type: "p2p",
      message_type: "text",
      content: JSON.stringify({ text: "飞书连接测试" })
    }
  }
});

const webChatTurn = createWebChatEnvelope({
  sessionKey: "agent:main:main",
  text: "帮我整理今天的发布检查清单",
  clientId: "dashboard"
});

const rejectedRemote = validateConnection({
  client: { clientId: "remote-browser", role: "operator", local: false },
  config: { gateway: { allowRemote: true, remoteToken: "secret" } }
});

console.log("Gateway boot plan:");
console.log(resolveGatewayPlan(["node", "openclaw", "gateway", "--port", "18789"]));
console.log("\nAccepted connection:");
console.log(connection);
console.log("\nControl-plane agent request:");
console.log(webTurn);
console.log("\nChannel-normalized agent request:");
console.log(telegramTurn);
console.log("\nSlack thread-normalized agent request:");
console.log(slackTurn);
console.log("\nFeishu URL verification response:");
console.log(feishuChallenge.body);
console.log("\nFeishu event-normalized agent request:");
console.log(feishuEvent.envelope);
console.log("\nWebChat control-plane envelope:");
console.log(webChatTurn);
console.log("\nRejected remote connection:");
console.log(rejectedRemote);
console.log("\nGateway event snapshot:");
console.log(gateway.snapshot());
