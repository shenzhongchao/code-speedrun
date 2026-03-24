import {
  createInboundDedupe,
  createReplyDispatcher,
  dispatchInboundTurn
} from "./reply-dispatch.js";

const deliveries = [];
const dispatcher = createReplyDispatcher({
  async deliver(payload) {
    deliveries.push(payload);
  }
});

const result = await dispatchInboundTurn({
  inboundContext: {
    messageId: "msg-1",
    text: "What is the deployment status?"
  },
  route: {
    agentId: "main",
    sessionKey: "agent:main:telegram:direct:@teal-user",
    sendPolicy: "allow",
    deliverRoute: {
      channel: "telegram",
      to: "@teal-user",
      accountId: "personal"
    }
  },
  dispatcher,
  dedupe: createInboundDedupe()
});

console.log("Dispatch result:");
console.log(result);
console.log("\nDeliveries:");
console.log(deliveries);
