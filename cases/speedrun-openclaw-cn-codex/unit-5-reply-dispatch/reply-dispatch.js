export function createInboundDedupe() {
  const seen = new Set();

  return {
    has(messageId) {
      return seen.has(messageId);
    },
    remember(messageId) {
      seen.add(messageId);
    }
  };
}

export function createReplyDispatcher({ deliver }) {
  const deliveries = [];

  return {
    async sendFinalReply(payload) {
      const text = String(payload.text ?? "").trim();
      if (!text) {
        return false;
      }

      const record = {
        kind: "final",
        text,
        channel: payload.channel,
        to: payload.to,
        accountId: payload.accountId,
        threadId: payload.threadId
      };
      deliveries.push(record);
      await deliver(record);
      return true;
    },
    getDeliveries() {
      return deliveries.slice();
    }
  };
}

export function makeRuleBasedReply(inboundContext, route) {
  const lowered = inboundContext.text.toLowerCase();

  if (lowered.includes("status")) {
    return {
      text: `Session ${route.sessionKey} is healthy. Next stop: reply on ${route.deliverRoute.channel}.`
    };
  }

  if (lowered.includes("build")) {
    return {
      text: "Build failures usually split into compile, test, and deploy buckets. Start with the first red job."
    };
  }

  return {
    text: `OpenClaw would route "${inboundContext.text}" into ${route.sessionKey} for agent ${route.agentId}.`
  };
}

export async function dispatchInboundTurn({
  inboundContext,
  route,
  dispatcher,
  dedupe,
  generateReply = makeRuleBasedReply
}) {
  if (dedupe.has(inboundContext.messageId)) {
    return { skipped: true, reason: "duplicate" };
  }

  dedupe.remember(inboundContext.messageId);

  if (route.sendPolicy === "deny") {
    return { skipped: true, reason: "send_policy_denied" };
  }

  // LEARN: The dispatcher is the loading dock.
  // The reply engine can keep producing payloads while one place owns delivery order.
  const reply = generateReply(inboundContext, route);
  await dispatcher.sendFinalReply({
    ...reply,
    channel: route.deliverRoute.channel,
    to: route.deliverRoute.to,
    accountId: route.deliverRoute.accountId,
    threadId: route.deliverRoute.threadId
  });

  return {
    skipped: false,
    reply,
    deliveries: dispatcher.getDeliveries()
  };
}
