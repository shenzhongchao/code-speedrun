import { createInboundDedupe, createReplyDelivery, deliverRunResult } from "./reply-delivery.js";

const sent = [];
const delivery = createReplyDelivery({
  transports: {
    telegram: {
      async send(reply) {
        sent.push({ provider: "telegram", ...reply });
        return { status: "sent", provider: "telegram", messageId: "tg-out-1" };
      }
    },
    webchat: {
      async send(reply) {
        sent.push({ provider: "webchat", ...reply });
        return { status: "sent", provider: "webchat", messageId: "web-out-1" };
      }
    }
  }
});

const request = {
  runId: "tg-42",
  idempotencyKey: "telegram:personal:42",
  source: {
    channel: "telegram",
    to: "@teal-user"
  }
};

const result = await deliverRunResult({
  request,
  runResult: {
    runId: "tg-42",
    payloads: [{ type: "text", text: "已为明早 9 点创建部署状态检查提醒。" }]
  },
  dedupe: createInboundDedupe(),
  delivery
});

console.log("Delivery result:");
console.log(result);
console.log("\nSent messages:");
console.log(sent);
