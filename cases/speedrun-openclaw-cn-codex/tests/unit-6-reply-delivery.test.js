import assert from "node:assert/strict";
import test from "node:test";

import {
  chunkMessage,
  createDeadLetterLog,
  createInboundDedupe,
  createReplyDelivery,
  createRetryingTransport,
  deliverRunResult,
  shapePayloads
} from "../unit-6-reply-delivery/reply-delivery.js";

test("NO_REPLY and silent payloads are suppressed", () => {
  assert.equal(shapePayloads([{ type: "text", text: "NO_REPLY" }]), null);
  assert.equal(shapePayloads([{ type: "silent" }]), null);
});

test("long text is chunked", () => {
  assert.deepEqual(chunkMessage("abcdef", 2), ["ab", "cd", "ef"]);
});

test("same idempotency key does not send twice", async () => {
  const sent = [];
  const delivery = createReplyDelivery({
    transports: { webchat: { send: async (reply) => sent.push(reply) && { status: "sent" } } }
  });
  const dedupe = createInboundDedupe();
  const request = { runId: "r1", idempotencyKey: "same", source: { channel: "webchat", to: "u" } };
  const runResult = { runId: "r1", payloads: [{ type: "text", text: "hello" }] };

  await deliverRunResult({ request, runResult, dedupe, delivery });
  const second = await deliverRunResult({ request, runResult, dedupe, delivery });

  assert.equal(second.status, "duplicate");
  assert.equal(sent.length, 1);
});

test("transport failure retries before succeeding", async () => {
  let attempts = 0;
  const transport = createRetryingTransport({
    async send() {
      attempts += 1;
      if (attempts < 2) {
        throw new Error("temporary");
      }
      return { status: "sent" };
    }
  }, { retries: 2 });

  assert.equal((await transport.send({ text: "hello" })).status, "sent");
  assert.equal(attempts, 2);
});

test("retry failure enters dead-letter log", async () => {
  const deadLetters = createDeadLetterLog();
  const transport = createRetryingTransport({
    async send() {
      throw new Error("down");
    }
  }, { retries: 1, deadLetters });

  await assert.rejects(() => transport.send({ runId: "r1", text: "hello" }), /down/);
  assert.equal(deadLetters.entries()[0].reply.runId, "r1");
});

test("Slack source preserves thread in formatted reply", async () => {
  const sent = [];
  const delivery = createReplyDelivery({
    transports: { slack: { send: async (reply) => sent.push(reply) && { status: "sent" } } }
  });

  await deliverRunResult({
    request: {
      runId: "s1",
      idempotencyKey: "slack:T:C:1",
      source: { channel: "slack", to: "C1", threadId: "1700.42" }
    },
    runResult: { runId: "s1", payloads: [{ type: "text", text: "ok" }] },
    dedupe: createInboundDedupe(),
    delivery
  });

  assert.equal(sent[0].threadId, "1700.42");
});
