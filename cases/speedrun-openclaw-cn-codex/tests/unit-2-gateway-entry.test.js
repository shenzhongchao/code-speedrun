import assert from "node:assert/strict";
import test from "node:test";

import {
  createFeishuChannel,
  createFeishuGatewayServer,
  createFeishuWebSocketGateway,
  createFeishuRestClient,
  runFeishuQrRegistration,
  createSlackChannel,
  createTelegramChannel,
  createWebChatEnvelope,
  validateConnection,
  writeFeishuEnvFile
} from "../unit-2-gateway-entry/entry.js";

test("Telegram event normalize generates a stable session key and idempotency key", () => {
  const channel = createTelegramChannel({ agentId: "main" });
  const envelope = channel.normalize({
    channel: "telegram",
    account: "personal",
    messageId: "42",
    sender: "@teal-user",
    chatId: "@teal-user",
    chatType: "direct",
    text: "hello"
  });

  assert.equal(envelope.sessionKey, "agent:main:telegram:@teal-user");
  assert.equal(envelope.idempotencyKey, "telegram:personal:42");
});

test("Slack thread event preserves thread id in source and session key", () => {
  const channel = createSlackChannel({ agentId: "main" });
  const envelope = channel.normalize({
    channel: "slack",
    teamId: "T1",
    channelId: "C1",
    threadId: "1700.42",
    userId: "U1",
    text: "ship status?"
  });

  assert.equal(envelope.sessionKey, "agent:main:slack:C1:1700.42");
  assert.equal(envelope.source.threadId, "1700.42");
});

test("WebChat request creates a control-plane source", () => {
  const envelope = createWebChatEnvelope({
    sessionKey: "agent:main:main",
    text: "整理发布检查清单",
    clientId: "web-1"
  });

  assert.equal(envelope.method, "agent");
  assert.equal(envelope.source.kind, "control-plane");
  assert.equal(envelope.source.clientId, "web-1");
});

test("remote client without token is rejected", () => {
  const connection = validateConnection({
    client: { clientId: "browser-remote", role: "operator", local: false },
    config: { gateway: { allowRemote: true, remoteToken: "secret" } }
  });

  assert.equal(connection.accepted, false);
  assert.match(connection.reason, /token/i);
});

test("Feishu URL verification returns challenge after token check", () => {
  const channel = createFeishuChannel({
    agentId: "main",
    verificationToken: "verify-token"
  });

  const response = channel.handleEvent({
    type: "url_verification",
    token: "verify-token",
    challenge: "challenge-123"
  });

  assert.deepEqual(response, { type: "challenge", body: { challenge: "challenge-123" } });
});

test("Feishu receive message event normalizes to agent envelope", () => {
  const channel = createFeishuChannel({
    agentId: "main",
    verificationToken: "verify-token"
  });

  const response = channel.handleEvent({
    schema: "2.0",
    header: {
      event_id: "evt-1",
      event_type: "im.message.receive_v1",
      token: "verify-token",
      tenant_key: "tenant-1"
    },
    event: {
      sender: {
        sender_id: { open_id: "ou_user_1" },
        sender_type: "user"
      },
      message: {
        message_id: "om_msg_1",
        chat_id: "oc_chat_1",
        chat_type: "p2p",
        message_type: "text",
        content: JSON.stringify({ text: "你好 OpenClaw" })
      }
    }
  });

  assert.equal(response.type, "agent");
  assert.equal(response.envelope.runId, "feishu-om_msg_1");
  assert.equal(response.envelope.text, "你好 OpenClaw");
  assert.equal(response.envelope.sessionKey, "agent:main:feishu:ou_user_1");
  assert.equal(response.envelope.idempotencyKey, "feishu:tenant-1:om_msg_1");
  assert.equal(response.envelope.source.channel, "feishu");
});

test("Feishu REST client gets tenant token and sends text reply", async () => {
  const requests = [];
  const client = createFeishuRestClient({
    appId: "cli_test",
    appSecret: "secret",
    fetch: async (url, options) => {
      requests.push({ url, options });
      if (url.endsWith("/auth/v3/tenant_access_token/internal")) {
        return jsonResponse({ code: 0, tenant_access_token: "tenant-token", expire: 7200 });
      }
      return jsonResponse({ code: 0, data: { message_id: "om_reply_1" } });
    }
  });

  const result = await client.sendText({
    receiveIdType: "open_id",
    receiveId: "ou_user_1",
    text: "已收到"
  });

  assert.equal(result.data.message_id, "om_reply_1");
  assert.equal(requests[0].url, "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal");
  assert.equal(requests[1].url, "https://open.feishu.cn/open-apis/im/v1/messages?receive_id_type=open_id");
  assert.equal(requests[1].options.headers.Authorization, "Bearer tenant-token");
  assert.deepEqual(JSON.parse(requests[1].options.body), {
    receive_id: "ou_user_1",
    msg_type: "text",
    content: JSON.stringify({ text: "已收到" })
  });
});

test("Feishu gateway server accepts webhook event and publishes envelope", async () => {
  const published = [];
  const server = createFeishuGatewayServer({
    port: 0,
    channel: createFeishuChannel({ verificationToken: "verify-token" }),
    onAgentEnvelope(envelope) {
      published.push(envelope);
    }
  });
  await server.start();

  try {
    const response = await fetch(`${server.url}/feishu/events`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        schema: "2.0",
        header: {
          event_id: "evt-2",
          event_type: "im.message.receive_v1",
          token: "verify-token",
          tenant_key: "tenant-1"
        },
        event: {
          sender: { sender_id: { open_id: "ou_user_2" }, sender_type: "user" },
          message: {
            message_id: "om_msg_2",
            chat_id: "oc_chat_2",
            chat_type: "p2p",
            message_type: "text",
            content: JSON.stringify({ text: "连接测试" })
          }
        }
      })
    });

    assert.equal(response.status, 200);
    assert.deepEqual(await response.json(), { code: 0 });
    assert.equal(published[0].text, "连接测试");
  } finally {
    await server.stop();
  }
});

test("Feishu WebSocket gateway starts long connection and publishes SDK events", async () => {
  const published = [];
  const started = [];
  let registeredHandler;
  const fakeSdk = {
    Domain: { Feishu: "https://open.feishu.cn", Lark: "https://open.larksuite.com" },
    AppType: { SelfBuild: "self_build" },
    LoggerLevel: { info: "info" },
    EventDispatcher: class FakeEventDispatcher {
      register(handlers) {
        registeredHandler = handlers["im.message.receive_v1"];
        return this;
      }
    },
    WSClient: class FakeWSClient {
      constructor(options) {
        this.options = options;
      }

      start({ eventDispatcher }) {
        started.push({ options: this.options, eventDispatcher });
      }

      close() {
        started.push({ closed: true });
      }
    }
  };
  const gateway = createFeishuWebSocketGateway({
    appId: "cli_test",
    appSecret: "secret",
    verificationToken: "verify-token",
    channel: createFeishuChannel({ verificationToken: "verify-token" }),
    sdk: fakeSdk,
    onAgentEnvelope(envelope) {
      published.push(envelope);
    }
  });

  const startResult = await gateway.start();
  assert.equal(startResult.mode, "websocket");
  assert.equal(started[0].options.appId, "cli_test");
  assert.equal(started[0].options.appSecret, "secret");
  assert.equal(started[0].options.domain, "https://open.feishu.cn");

  await registeredHandler({
    schema: "2.0",
    header: {
      event_id: "evt-ws-1",
      event_type: "im.message.receive_v1",
      token: "verify-token",
      tenant_key: "tenant-1"
    },
    event: {
      sender: { sender_id: { open_id: "ou_ws_user" }, sender_type: "user" },
      message: {
        message_id: "om_ws_msg",
        chat_id: "oc_ws_chat",
        chat_type: "p2p",
        message_type: "text",
        content: JSON.stringify({ text: "长连接测试" })
      }
    }
  });

  assert.equal(published[0].sessionKey, "agent:main:feishu:ou_ws_user");
  assert.equal(published[0].text, "长连接测试");

  await gateway.stop();
  assert.deepEqual(started[1], { closed: true });
});

test("Feishu QR registration begins device flow and polls credentials", async () => {
  const requests = [];
  const rendered = [];
  const slept = [];
  const result = await runFeishuQrRegistration({
    fetch: async (url, options) => {
      const body = Object.fromEntries(new URLSearchParams(options.body));
      requests.push({ url, body });
      if (body.action === "init") {
        return jsonResponse({ supported_auth_methods: ["client_secret"] });
      }
      if (body.action === "begin") {
        return jsonResponse({
          device_code: "device-1",
          verification_uri_complete: "https://open.feishu.cn/qr",
          interval: 1,
          expire_in: 60
        });
      }
      return jsonResponse({
        client_id: "cli_qr",
        client_secret: "secret_qr",
        user_info: { open_id: "ou_owner", tenant_brand: "feishu" }
      });
    },
    renderQr(url) {
      rendered.push(url);
      return true;
    },
    sleep(ms) {
      slept.push(ms);
      return Promise.resolve();
    },
    probeBot: async () => ({ bot_name: "QrBot", bot_open_id: "ou_bot" }),
    log: () => {}
  });

  assert.equal(requests[0].url, "https://accounts.feishu.cn/oauth/v1/app/registration");
  assert.deepEqual(requests.map((request) => request.body.action), ["init", "begin", "poll"]);
  assert.equal(requests[1].body.archetype, "PersonalAgent");
  assert.equal(requests[2].body.device_code, "device-1");
  assert.equal(rendered[0], "https://open.feishu.cn/qr?from=openclaw-speedrun&tp=openclaw-speedrun");
  assert.deepEqual(slept, []);
  assert.deepEqual(result, {
    appId: "cli_qr",
    appSecret: "secret_qr",
    domain: "feishu",
    ownerOpenId: "ou_owner",
    botName: "QrBot",
    botOpenId: "ou_bot"
  });
});

test("Feishu QR env writer preserves unrelated values and defaults to websocket", async () => {
  let written = "";
  await writeFeishuEnvFile({
    envPath: "/tmp/teaching.env",
    credentials: {
      appId: "cli_qr",
      appSecret: "secret_qr",
      domain: "feishu",
      ownerOpenId: "ou_owner"
    },
    readText: async () => "OPENAI_API_KEY=keep\nFEISHU_CONNECTION_MODE=webhook\n",
    writeText: async (_path, text) => {
      written = text;
    }
  });

  assert.match(written, /OPENAI_API_KEY=keep/);
  assert.match(written, /FEISHU_APP_ID=cli_qr/);
  assert.match(written, /FEISHU_APP_SECRET=secret_qr/);
  assert.match(written, /FEISHU_DOMAIN=feishu/);
  assert.match(written, /FEISHU_CONNECTION_MODE=websocket/);
  assert.match(written, /FEISHU_ALLOWED_USERS=ou_owner/);
});

function jsonResponse(body, status = 200) {
  return {
    ok: status >= 200 && status < 300,
    status,
    async json() {
      return body;
    },
    async text() {
      return JSON.stringify(body);
    }
  };
}
