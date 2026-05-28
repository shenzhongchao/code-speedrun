# Unit 2: Gateway Entry

> **Motto**: *Gateway 收信，不替 agent 思考*

## In Plain Language

Gateway 像本地总机：CLI、Web UI、Telegram、Slack、飞书都先打到这里。它把不同来源的消息整理成统一 `agent` 请求，但不负责真正推理。

## Background Knowledge

- **总机**: 不同电话线进来，先变成同一种工单；技术上是 channel/control-plane 请求规范化。
- **本地门禁**: 同机连接更容易信任，远程连接要校验；技术上是 pairing、token、signature 和 gateway auth。
- **幂等票据**: 同一条消息重试不能执行两次；技术上用 idempotency key 标记 side effect。

## Key Terminology

- **Control plane**: 管理请求、连接、事件和设备能力的平面。
- **Channel**: Telegram/Slack/WebChat 等消息来源。
- **Envelope**: 规范化后的请求信封，包含 `runId`、`sessionKey`、`source` 和 `text`。

## What This Unit Does

`entry.js` 提供一个小 Gateway：接受本地 client，提交 WebChat/CLI 风格请求，也能把 Telegram/Slack/Feishu raw event 规范化成 agent envelope。飞书部分是可连接真实开放平台的教学版：默认使用 WebSocket 长连接，不需要公网 HTTPS；也保留 webhook 模式用于理解飞书回调。扫码 setup 只负责创建应用和保存凭证，不负责收消息。

## Key Code Walkthrough

- `resolveGatewayPlan()` 解析端口并列出 Gateway 方法。
- `createGatewayControlPlane().connect()` 模拟本地连接被接受。
- `submitAgentTurn()` 把控制平面输入变成 `agent` 请求。
- `createTelegramChannel().normalize()` 把 provider-specific event 变成同一请求形状。
- `createFeishuChannel().handleEvent()` 处理飞书事件订阅的 challenge 和消息事件。
- `createFeishuRestClient().sendText()` 使用飞书 tenant access token 调用 `im/v1/messages`。
- `createFeishuGatewayServer()` 启动一个真实 HTTP webhook server，路径是 `/feishu/events`。
- `createFeishuWebSocketGateway()` 使用飞书/Lark SDK 启动长连接，把 SDK 事件转成同一个 agent envelope。
- `runFeishuQrRegistration()` 演示 Feishu/Lark device-code 扫码创建应用流程。
- `writeFeishuEnvFile()` 把扫码得到的 App ID/App Secret 写入 `.env`，并默认设置 WebSocket 模式。

## How to Run

```bash
node unit-2-gateway-entry/index.js
```

如果还没有飞书应用，可以先用扫码创建教学机器人：

```bash
npm run unit:2:feishu:setup
```

这一步会打开/打印飞书扫码授权 URL，成功后写入 `.env`。它解决的是“拿到 App ID/App Secret”的问题，不是事件传输本身。

启动真实飞书教学网关。默认是 WebSocket 长连接模式：

```bash
npm run unit:2:feishu
```

需要在 `.env` 中配置：

```bash
FEISHU_CONNECTION_MODE=websocket
FEISHU_DOMAIN=feishu
FEISHU_GATEWAY_PORT=18790
FEISHU_GATEWAY_HOST=127.0.0.1
FEISHU_VERIFICATION_TOKEN=你的事件订阅 Verification Token
FEISHU_ENCRYPT_KEY=你的事件订阅 Encrypt Key，没有开启加密可留空
FEISHU_APP_ID=cli_xxx
FEISHU_APP_SECRET=xxx
FEISHU_AUTO_REPLY=false
```

WebSocket 模式下，gateway 主动连接飞书开放平台。你需要在飞书开放平台的事件订阅里选择“使用长连接接收事件”，然后本地运行 `npm run unit:2:feishu` 即可；因为没有飞书访问本机 HTTP 地址，所以不需要公网 HTTPS、ngrok 或 frp。

如果想观察 webhook 回调流程，可以显式改成：

```bash
FEISHU_CONNECTION_MODE=webhook npm run unit:2:feishu
```

webhook 模式下，飞书会请求你的 `/feishu/events`，所以 Request URL 必须是公网可达 HTTPS。开发时可以把 `http://127.0.0.1:18790/feishu/events` 通过 ngrok、cloudflared 或内网穿透暴露出去，再填入飞书后台。

打开 `FEISHU_AUTO_REPLY=true` 后，收到消息会调用飞书发送接口回一条教学回复；默认关闭，避免配置验证阶段误发消息。

## Expected Output

输出会包含 Gateway boot plan、accepted connection、control-plane request、Telegram/Slack/Feishu channel-normalized request、飞书 challenge response 和事件快照。

## Exercises

### Explain It Back

解释 `source.kind` 为什么要区分 `control-plane` 和 `channel`。

### Modify It

- 增加一个新的 channel normalize 函数。
- 把 `allowRemote` 改成 `true`，再传入 `local: false` 的 client。
- 在飞书开放平台创建机器人应用，使用长连接订阅 `im.message.receive_v1`，观察控制台打印的 agent envelope。
- 把 `FEISHU_CONNECTION_MODE` 改成 `webhook`，比较 webhook 为什么需要公网 HTTPS。

## Debug Guide

在 `createFeishuChannel().handleEvent()` 上打断点，看飞书 raw event 如何通过 token 校验、challenge 分支和消息规范化，最后变成 `sessionKey` 和 `idempotencyKey`。

在 `runFeishuQrRegistration()` 上打断点，看扫码 setup 的三段式流程：`init` 检查支持的认证方式、`begin` 获取 device code 和二维码 URL、`poll` 等待手机端确认并返回凭证。
