import "dotenv/config";

import {
  createFeishuChannel,
  createFeishuGatewayServer,
  createFeishuWebSocketGateway,
  createFeishuRestClient
} from "./entry.js";

const connectionMode = process.env.FEISHU_CONNECTION_MODE ?? "websocket";
const agentId = process.env.OPENCLAW_AGENT_ID ?? "main";
const verificationToken = process.env.FEISHU_VERIFICATION_TOKEN;

const channel = createFeishuChannel({ agentId, verificationToken });

const feishu = createFeishuRestClient({
  appId: process.env.FEISHU_APP_ID,
  appSecret: process.env.FEISHU_APP_SECRET
});

async function onAgentEnvelope(envelope) {
  // LEARN: This is where Unit 2 hands work to the rest of OpenClaw. In this
  // standalone teaching entrypoint we only print the normalized agent request.
  console.log("[Feishu -> agent envelope]");
  console.log(envelope);

  // LEARN: Optional auto-reply proves the gateway can call Feishu's real REST
  // API. It is off by default so you can connect the event stream without
  // sending messages during setup tests.
  if (process.env.FEISHU_AUTO_REPLY === "true") {
    const receiveId = envelope.source.chatType === "p2p"
      ? envelope.source.from
      : envelope.source.to;
    const receiveIdType = envelope.source.chatType === "p2p" ? "open_id" : "chat_id";
    const result = await feishu.sendText({
      receiveId,
      receiveIdType,
      text: `OpenClaw gateway 收到：${envelope.text}`
    });
    console.log("[Feishu reply sent]");
    console.log(result);
  }
}

if (connectionMode === "webhook") {
  const server = createFeishuGatewayServer({
    port: Number(process.env.FEISHU_GATEWAY_PORT ?? 18790),
    host: process.env.FEISHU_GATEWAY_HOST ?? "127.0.0.1",
    channel,
    onAgentEnvelope
  });

  const { url, path } = await server.start();
  console.log(`Feishu webhook gateway listening at ${url}${path}`);
  console.log("Webhook mode needs a public HTTPS URL or a tunnel configured as the Feishu event request URL.");
} else {
  const gateway = createFeishuWebSocketGateway({
    appId: process.env.FEISHU_APP_ID,
    appSecret: process.env.FEISHU_APP_SECRET,
    verificationToken,
    encryptKey: process.env.FEISHU_ENCRYPT_KEY,
    domain: process.env.FEISHU_DOMAIN ?? "feishu",
    channel: createFeishuChannel({ agentId, verificationToken, validateToken: false }),
    onAgentEnvelope
  });

  await gateway.start();
  console.log("Feishu WebSocket gateway is running. Configure Feishu event subscription to use long connection.");
  console.log("No public HTTPS callback URL is required in this mode.");
}
