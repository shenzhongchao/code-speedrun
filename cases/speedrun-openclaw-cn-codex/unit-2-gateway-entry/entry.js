import { createServer } from "node:http";
import { readFile, writeFile } from "node:fs/promises";

export function resolveGatewayPlan(argv) {
  const command = argv[2] ?? "gateway";
  const portIndex = argv.indexOf("--port");
  const port = portIndex >= 0 ? Number(argv[portIndex + 1]) : 18789;

  return {
    command,
    bind: "127.0.0.1",
    port,
    controlPlaneUrl: `ws://127.0.0.1:${port}`,
    methods: ["connect", "agent", "agent.wait", "send", "node.invoke"]
  };
}

export function createGatewayControlPlane({ config, channels = [] }) {
  let nextRun = 1;
  const events = [];

  return {
    connect(client) {
      const connection = validateConnection({ client, config });
      events.push({ stream: "gateway", phase: "connect", connection });
      return connection;
    },

    submitAgentTurn({ text, sessionKey = "agent:main:main", channel = "webchat", to = "dashboard" }) {
      const runId = `run-${nextRun++}`;
      const envelope = {
        runId,
        idempotencyKey: `${sessionKey}:${runId}`,
        method: "agent",
        text,
        sessionKey,
        source: {
          kind: "control-plane",
          channel,
          to
        }
      };

      // LEARN: Gateway 的核心价值不是“生成回复”，而是把不同入口统一成
      // 一个 agent run 请求，然后把生命周期和流式事件再广播出去。
      events.push({ stream: "agent", phase: "accepted", runId, sessionKey });
      return envelope;
    },

    receiveChannelMessage(raw) {
      const channel = channels.find((candidate) => candidate.id === raw.channel);
      if (!channel) {
        throw new Error(`unknown channel: ${raw.channel}`);
      }
      const envelope = channel.normalize(raw);
      events.push({ stream: "chat", phase: "received", runId: envelope.runId, sessionKey: envelope.sessionKey });
      return envelope;
    },

    publish(event) {
      events.push(event);
    },

    snapshot() {
      return {
        gateway: resolveGatewayPlan(["node", "openclaw", "gateway", "--port", String(config.gateway.port)]),
        events
      };
    }
  };
}

export function validateConnection({ client, config }) {
  const role = client.role ?? "operator";

  // LEARN: Gateway 先建立本地信任边界。真实 OpenClaw 还会校验 pairing、
  // device token、challenge signature 和 gateway auth。
  if (client.local === true) {
    return { clientId: client.clientId, role, accepted: true, reason: "local client auto accepted" };
  }

  if (role === "node" && !client.deviceId) {
    return { clientId: client.clientId, role, accepted: false, reason: "node client requires deviceId" };
  }

  if (config.gateway?.remoteToken && client.token !== config.gateway.remoteToken) {
    return { clientId: client.clientId, role, accepted: false, reason: "remote token required" };
  }

  if (config.gateway?.allowRemote === true) {
    return { clientId: client.clientId, role, accepted: true, reason: "remote client accepted" };
  }

  return { clientId: client.clientId, role, accepted: false, reason: "remote clients disabled" };
}

export function createTelegramChannel({ agentId = "main" } = {}) {
  return {
    id: "telegram",
    normalize(raw) {
      const peer = raw.chatType === "group" ? raw.chatId : raw.sender;
      return {
        runId: `tg-${raw.messageId}`,
        method: "agent",
        text: raw.text,
        sessionKey: `agent:${agentId}:telegram:${peer}`,
        idempotencyKey: `telegram:${raw.account}:${raw.messageId}`,
        source: {
          kind: "channel",
          channel: "telegram",
          account: raw.account,
          from: raw.sender,
          to: raw.chatId,
          chatType: raw.chatType
        }
      };
    }
  };
}

export function createSlackChannel({ agentId = "main" } = {}) {
  return {
    id: "slack",
    normalize(raw) {
      const conversation = raw.threadId ? `${raw.channelId}:${raw.threadId}` : raw.channelId;
      return {
        runId: `slack-${raw.teamId}-${raw.channelId}-${raw.threadId ?? raw.ts ?? "latest"}`,
        method: "agent",
        text: raw.text,
        sessionKey: `agent:${agentId}:slack:${conversation}`,
        idempotencyKey: `slack:${raw.teamId}:${raw.channelId}:${raw.threadId ?? raw.ts}`,
        source: {
          kind: "channel",
          channel: "slack",
          teamId: raw.teamId,
          from: raw.userId,
          to: raw.channelId,
          threadId: raw.threadId
        }
      };
    }
  };
}

export function createFeishuChannel({
  agentId = "main",
  verificationToken = process.env.FEISHU_VERIFICATION_TOKEN,
  validateToken = true
} = {}) {
  return {
    id: "feishu",

    normalize(raw) {
      const event = raw.event ?? raw;
      const header = raw.header ?? {};
      const message = event.message ?? {};
      const sender = event.sender ?? {};
      const senderOpenId = sender.sender_id?.open_id ?? raw.senderOpenId;
      const tenantKey = header.tenant_key ?? raw.tenantKey ?? "default";
      const messageId = message.message_id ?? raw.messageId;
      const chatId = message.chat_id ?? raw.chatId;
      const chatType = message.chat_type ?? raw.chatType ?? "p2p";
      const text = extractFeishuText(message);
      const peer = chatType === "p2p" ? senderOpenId : chatId;

      // LEARN: Feishu's event body is provider-specific: sender ids are nested,
      // message content is a JSON string, and group chats use chat_id. The
      // gateway converts that into the same envelope shape as Telegram/Slack.
      return {
        runId: `feishu-${messageId}`,
        method: "agent",
        text,
        sessionKey: `agent:${agentId}:feishu:${peer}`,
        idempotencyKey: `feishu:${tenantKey}:${messageId}`,
        source: {
          kind: "channel",
          channel: "feishu",
          tenantKey,
          from: senderOpenId,
          to: chatId,
          chatType,
          messageType: message.message_type ?? raw.messageType
        }
      };
    },

    handleEvent(body) {
      if (validateToken) {
        assertFeishuToken(body, verificationToken);
      }
      if (body.type === "url_verification") {
        // LEARN: Feishu calls the webhook once during setup and expects the
        // challenge to be echoed. No agent run should be created for this event.
        return { type: "challenge", body: { challenge: body.challenge } };
      }
      const eventType = body.header?.event_type;
      if (eventType !== "im.message.receive_v1") {
        return { type: "ignored", body: { code: 0, msg: `ignored ${eventType ?? "unknown event"}` } };
      }
      return { type: "agent", envelope: this.normalize(body) };
    }
  };
}

export function createFeishuRestClient({
  appId = process.env.FEISHU_APP_ID,
  appSecret = process.env.FEISHU_APP_SECRET,
  baseUrl = "https://open.feishu.cn/open-apis",
  fetch: fetchImpl = globalThis.fetch
} = {}) {
  let cachedToken;
  let expiresAt = 0;

  async function tenantAccessToken() {
    const now = Date.now();
    if (cachedToken && now < expiresAt) {
      return cachedToken;
    }
    if (!appId || !appSecret) {
      throw new Error("FEISHU_APP_ID and FEISHU_APP_SECRET are required");
    }

    // LEARN: Feishu REST APIs use a tenant access token for bot operations.
    // The token is cached until shortly before expiry so every reply does not
    // need a separate auth request.
    const response = await fetchJson(fetchImpl, `${baseUrl}/auth/v3/tenant_access_token/internal`, {
      method: "POST",
      headers: { "Content-Type": "application/json; charset=utf-8" },
      body: JSON.stringify({
        app_id: appId,
        app_secret: appSecret
      })
    });
    if (response.code !== 0) {
      throw new Error(`Feishu token error ${response.code}: ${response.msg ?? "unknown"}`);
    }
    cachedToken = response.tenant_access_token;
    expiresAt = now + Math.max((response.expire ?? 7200) - 60, 1) * 1000;
    return cachedToken;
  }

  return {
    tenantAccessToken,

    async sendText({ receiveId, text, receiveIdType = "open_id" }) {
      const token = await tenantAccessToken();
      // LEARN: Feishu message content is itself a JSON string. The outer JSON
      // describes the message envelope; the inner JSON describes text content.
      return fetchJson(fetchImpl, `${baseUrl}/im/v1/messages?receive_id_type=${encodeURIComponent(receiveIdType)}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json; charset=utf-8",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          receive_id: receiveId,
          msg_type: "text",
          content: JSON.stringify({ text })
        })
      });
    }
  };
}

export function createFeishuGatewayServer({
  port = Number(process.env.FEISHU_GATEWAY_PORT ?? 18790),
  host = "127.0.0.1",
  path = "/feishu/events",
  channel = createFeishuChannel(),
  onAgentEnvelope = () => {}
} = {}) {
  let server;
  let url;

  return {
    get url() {
      return url;
    },

    async start() {
      server = createServer(async (request, response) => {
        if (request.method !== "POST" || new URL(request.url, `http://${request.headers.host}`).pathname !== path) {
          sendJson(response, 404, { code: 404, msg: "not found" });
          return;
        }

        try {
          const body = await readJsonBody(request);
          const handled = channel.handleEvent(body);
          if (handled.type === "challenge") {
            sendJson(response, 200, handled.body);
            return;
          }
          if (handled.type === "agent") {
            await onAgentEnvelope(handled.envelope, body);
            sendJson(response, 200, { code: 0 });
            return;
          }
          sendJson(response, 200, handled.body ?? { code: 0 });
        } catch (error) {
          sendJson(response, 400, { code: 400, msg: error.message });
        }
      });

      await new Promise((resolve) => server.listen(port, host, resolve));
      const address = server.address();
      const actualPort = typeof address === "object" ? address.port : port;
      url = `http://${host}:${actualPort}`;
      return { url, path };
    },

    async stop() {
      if (!server) {
        return;
      }
      await new Promise((resolve, reject) => {
        server.close((error) => (error ? reject(error) : resolve()));
      });
      server = undefined;
    }
  };
}

export function createFeishuWebSocketGateway({
  appId = process.env.FEISHU_APP_ID,
  appSecret = process.env.FEISHU_APP_SECRET,
  verificationToken = process.env.FEISHU_VERIFICATION_TOKEN,
  encryptKey = process.env.FEISHU_ENCRYPT_KEY,
  domain = process.env.FEISHU_DOMAIN ?? "feishu",
  channel = createFeishuChannel({ verificationToken, validateToken: false }),
  sdk,
  onAgentEnvelope = () => {},
  log = console.log
} = {}) {
  let wsClient;
  let eventDispatcher;

  return {
    get client() {
      return wsClient;
    },

    async start() {
      if (!appId || !appSecret) {
        throw new Error("FEISHU_APP_ID and FEISHU_APP_SECRET are required for Feishu WebSocket mode");
      }

      const Lark = sdk ?? await loadFeishuSdk();
      const resolvedDomain = resolveFeishuSdkDomain(Lark, domain);

      // LEARN: Webhook 是“飞书请求你的 HTTP 地址”；WebSocket 长连接则相反：
      // gateway 主动连到飞书。只要本机能访问外网，就不需要公网 HTTPS。
      eventDispatcher = new Lark.EventDispatcher({
        encryptKey,
        verificationToken
      });

      // LEARN: SDK 会把 WebSocket 收到的 provider event 分发给这里注册的
      // handler。Gateway 仍然只做规范化：把飞书事件变成统一 agent envelope。
      eventDispatcher.register({
        "im.message.receive_v1": async (data) => {
          const handled = channel.handleEvent(wrapFeishuSdkEvent(data));
          if (handled.type === "agent") {
            await onAgentEnvelope(handled.envelope, data);
          }
        }
      });

      wsClient = new Lark.WSClient({
        appId,
        appSecret,
        appType: Lark.AppType?.SelfBuild,
        domain: resolvedDomain,
        loggerLevel: Lark.LoggerLevel?.info
      });
      wsClient.start({ eventDispatcher });
      log(`Feishu WebSocket gateway connected to ${domain}`);
      return { mode: "websocket", domain: resolvedDomain };
    },

    async stop() {
      if (!wsClient) {
        return;
      }
      // LEARN: 不同 SDK 版本可能叫 close 或 shutdown。教学代码兼容两种，
      // 这样重点仍然放在长连接生命周期，而不是某个版本的细节。
      if (typeof wsClient.close === "function") {
        await wsClient.close();
      } else if (typeof wsClient.shutdown === "function") {
        await wsClient.shutdown();
      }
      wsClient = undefined;
      eventDispatcher = undefined;
    }
  };
}

export async function runFeishuQrRegistration({
  domain = "feishu",
  fetch: fetchImpl = globalThis.fetch,
  renderQr = renderQrInTerminal,
  sleep = sleepMs,
  probeBot = probeFeishuBot,
  log = console.log,
  timeoutMs = 600_000
} = {}) {
  const accountsBaseUrl = resolveFeishuAccountsBaseUrl(domain);

  // LEARN: 扫码不是事件入口。它只是 Feishu/Lark 的 device-code
  // onboarding：先申请一个 device_code，再让用户用移动端确认创建应用。
  const init = await postFeishuRegistration(fetchImpl, accountsBaseUrl, { action: "init" });
  const supported = init.supported_auth_methods ?? [];
  if (!supported.includes("client_secret")) {
    throw new Error(`Feishu QR registration does not support client_secret auth: ${supported.join(", ")}`);
  }

  const begin = await postFeishuRegistration(fetchImpl, accountsBaseUrl, {
    action: "begin",
    archetype: "PersonalAgent",
    auth_method: "client_secret",
    request_user_info: "open_id"
  });
  if (!begin.device_code) {
    throw new Error("Feishu QR registration did not return a device_code");
  }

  const qrUrl = appendFeishuQrTracking(begin.verification_uri_complete ?? "");
  if (!renderQr(qrUrl)) {
    log("Open this URL in Feishu/Lark to authorize the teaching bot:");
    log(qrUrl);
  }

  const startedAt = Date.now();
  const expireMs = Math.min((begin.expire_in ?? 600) * 1000, timeoutMs);
  const intervalMs = Math.max(begin.interval ?? 5, 1) * 1000;

  while (Date.now() - startedAt < expireMs) {
    const polled = await postFeishuRegistration(fetchImpl, accountsBaseUrl, {
      action: "poll",
      device_code: begin.device_code,
      tp: "ob_app"
    });

    const userInfo = polled.user_info ?? {};
    const resolvedDomain = userInfo.tenant_brand === "lark" ? "lark" : domain;
    if (polled.client_id && polled.client_secret) {
      const botInfo = await probeBot({
        appId: polled.client_id,
        appSecret: polled.client_secret,
        domain: resolvedDomain,
        fetch: fetchImpl
      });
      return {
        appId: polled.client_id,
        appSecret: polled.client_secret,
        domain: resolvedDomain,
        ownerOpenId: userInfo.open_id,
        botName: botInfo?.bot_name,
        botOpenId: botInfo?.bot_open_id
      };
    }

    if (polled.error === "access_denied" || polled.error === "expired_token") {
      return undefined;
    }

    // LEARN: authorization_pending 是正常状态，表示用户还没扫码确认。
    await sleep(intervalMs);
  }

  return undefined;
}

export async function writeFeishuEnvFile({
  envPath = new URL("../.env", import.meta.url).pathname,
  credentials,
  readText = (path) => readFile(path, "utf8"),
  writeText = (path, text) => writeFile(path, text, "utf8")
} = {}) {
  if (!credentials?.appId || !credentials?.appSecret) {
    throw new Error("Feishu credentials with appId and appSecret are required");
  }

  let current = "";
  try {
    current = await readText(envPath);
  } catch (error) {
    if (error.code !== "ENOENT") {
      throw error;
    }
  }

  const next = mergeEnvText(current, {
    FEISHU_APP_ID: credentials.appId,
    FEISHU_APP_SECRET: credentials.appSecret,
    FEISHU_DOMAIN: credentials.domain ?? "feishu",
    FEISHU_CONNECTION_MODE: "websocket",
    FEISHU_ALLOWED_USERS: credentials.ownerOpenId ?? "",
    FEISHU_AUTO_REPLY: process.env.FEISHU_AUTO_REPLY ?? "false"
  });
  await writeText(envPath, next);
  return { envPath, text: next };
}

export function createWebChatEnvelope({ sessionKey, text, clientId, requestId = "web-1" }) {
  return {
    runId: `webchat-${requestId}`,
    method: "agent",
    text,
    sessionKey,
    idempotencyKey: `webchat:${clientId}:${requestId}`,
    source: {
      kind: "control-plane",
      channel: "webchat",
      clientId,
      to: clientId
    }
  };
}

export function createNodeInvokeEnvelope({ nodeId, command, params = {}, requestId = "node-1" }) {
  return {
    runId: `node-${requestId}`,
    method: "node.invoke",
    idempotencyKey: `node:${nodeId}:${requestId}`,
    nodeId,
    command,
    params,
    source: {
      kind: "node",
      channel: "node",
      nodeId
    }
  };
}

export function createWebChatClient({ clientId = "web-local", local = true, token } = {}) {
  return { clientId, role: "operator", local, token };
}

export function createNodeClient({ clientId, deviceId, token } = {}) {
  return { clientId: clientId ?? deviceId, role: "node", local: false, deviceId, token };
}

async function postFeishuRegistration(fetchImpl, baseUrl, body) {
  if (!fetchImpl) {
    throw new Error("fetch is not available in this runtime");
  }
  const response = await fetchImpl(`${baseUrl}/oauth/v1/app/registration`, {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: new URLSearchParams(body).toString()
  });
  const data = await response.json();
  // LEARN: Feishu 的 poll 在 pending 时可能返回非 2xx，但 body 仍然是
  // 有意义的 JSON。这里和 Hermes 一样以 JSON payload 为准。
  if (!response.ok && !data.error) {
    throw new Error(`Feishu registration HTTP ${response.status}: ${JSON.stringify(data)}`);
  }
  return data;
}

async function probeFeishuBot({ appId, appSecret, domain, fetch: fetchImpl }) {
  const baseUrl = resolveFeishuOpenBaseUrl(domain);
  const token = await fetchJson(fetchImpl, `${baseUrl}/open-apis/auth/v3/tenant_access_token/internal`, {
    method: "POST",
    headers: { "Content-Type": "application/json; charset=utf-8" },
    body: JSON.stringify({ app_id: appId, app_secret: appSecret })
  });
  if (!token.tenant_access_token) {
    return undefined;
  }
  const bot = await fetchJson(fetchImpl, `${baseUrl}/open-apis/bot/v3/info`, {
    method: "GET",
    headers: { Authorization: `Bearer ${token.tenant_access_token}` }
  });
  const info = bot.bot ?? bot.data?.bot ?? {};
  return {
    bot_name: info.app_name ?? info.bot_name,
    bot_open_id: info.open_id
  };
}

function resolveFeishuAccountsBaseUrl(domain) {
  return domain === "lark" ? "https://accounts.larksuite.com" : "https://accounts.feishu.cn";
}

function resolveFeishuOpenBaseUrl(domain) {
  return domain === "lark" ? "https://open.larksuite.com" : "https://open.feishu.cn";
}

function appendFeishuQrTracking(url) {
  if (!url) {
    return "";
  }
  const separator = url.includes("?") ? "&" : "?";
  return `${url}${separator}from=openclaw-speedrun&tp=openclaw-speedrun`;
}

function renderQrInTerminal(url) {
  if (!url) {
    return false;
  }
  // LEARN: 为了保持教学案例零负担，默认不额外引入二维码渲染库。
  // CLI 会打印 URL；需要真正二维码时再接 qrcode 包即可。
  return false;
}

function sleepMs(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function mergeEnvText(text, values) {
  const lines = text.split(/\r?\n/).filter((line, index, array) => line.length > 0 || index < array.length - 1);
  const seen = new Set();
  const nextLines = lines.map((line) => {
    const match = line.match(/^([A-Za-z_][A-Za-z0-9_]*)=/);
    if (!match || !(match[1] in values)) {
      return line;
    }
    seen.add(match[1]);
    return `${match[1]}=${envValue(values[match[1]])}`;
  });

  for (const [key, value] of Object.entries(values)) {
    if (!seen.has(key)) {
      nextLines.push(`${key}=${envValue(value)}`);
    }
  }

  return `${nextLines.join("\n")}\n`;
}

function envValue(value) {
  const text = String(value ?? "");
  return /[\s#"'\\]/.test(text) ? JSON.stringify(text) : text;
}

async function loadFeishuSdk() {
  try {
    return await import("@larksuiteoapi/node-sdk");
  } catch (error) {
    throw new Error(
      `Feishu WebSocket mode requires @larksuiteoapi/node-sdk. Install it with: npm install @larksuiteoapi/node-sdk. Original error: ${error.message}`
    );
  }
}

function resolveFeishuSdkDomain(Lark, domain) {
  if (domain === "lark") {
    return Lark.Domain?.Lark ?? "https://open.larksuite.com";
  }
  if (domain === "feishu" || !domain) {
    return Lark.Domain?.Feishu ?? "https://open.feishu.cn";
  }
  return domain.replace(/\/+$/, "");
}

function wrapFeishuSdkEvent(data) {
  if (data?.schema && data?.header && data?.event) {
    return data;
  }
  return {
    schema: "2.0",
    header: {
      event_type: "im.message.receive_v1",
      token: data?.token,
      tenant_key: data?.tenant_key
    },
    event: data
  };
}

function assertFeishuToken(body, expected) {
  if (!expected) {
    return;
  }
  const actual = body.token ?? body.header?.token;
  if (actual !== expected) {
    throw new Error("invalid Feishu verification token");
  }
}

function extractFeishuText(message) {
  if (message.text) {
    return message.text;
  }
  if (message.message_type !== "text") {
    return `[unsupported Feishu message type: ${message.message_type ?? "unknown"}]`;
  }
  try {
    return JSON.parse(message.content ?? "{}").text ?? "";
  } catch {
    return "";
  }
}

async function fetchJson(fetchImpl, url, options) {
  if (!fetchImpl) {
    throw new Error("fetch is not available in this runtime");
  }
  const response = await fetchImpl(url, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(`Feishu HTTP ${response.status}: ${JSON.stringify(data)}`);
  }
  return data;
}

function readJsonBody(request) {
  return new Promise((resolve, reject) => {
    let body = "";
    request.setEncoding("utf8");
    request.on("data", (chunk) => {
      body += chunk;
    });
    request.on("error", reject);
    request.on("end", () => {
      try {
        resolve(body ? JSON.parse(body) : {});
      } catch (error) {
        reject(error);
      }
    });
  });
}

function sendJson(response, status, body) {
  response.writeHead(status, { "Content-Type": "application/json; charset=utf-8" });
  response.end(JSON.stringify(body));
}
