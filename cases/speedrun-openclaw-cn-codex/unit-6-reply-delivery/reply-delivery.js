export function createInboundDedupe() {
  const seen = new Set();

  return {
    remember(key) {
      if (seen.has(key)) {
        return false;
      }
      seen.add(key);
      return true;
    }
  };
}

export function shapePayloads(payloads, options = {}) {
  const text = payloads
    .filter((payload) => payload.type !== "silent")
    .filter((payload) => ["text", "error", "tool_summary"].includes(payload.type))
    .map((payload) => payload.text)
    .filter(Boolean)
    .join("\n")
    .replace(/\bNO_REPLY\b/g, "")
    .trim();

  if (!text) {
    return null;
  }

  return {
    type: "text",
    text,
    chunks: chunkMessage(text, options.maxLength ?? text.length)
  };
}

export function chunkMessage(text, maxLength) {
  if (text.length <= maxLength) {
    return [text];
  }
  const chunks = [];
  for (let index = 0; index < text.length; index += maxLength) {
    chunks.push(text.slice(index, index + maxLength));
  }
  return chunks;
}

export function shapeReply({ runResult, source, maxLength }) {
  const shaped = shapePayloads(runResult.payloads, { maxLength });

  if (!shaped) {
    return null;
  }

  return {
    channel: source.channel,
    to: source.to,
    threadId: source.threadId,
    text: shaped.text,
    chunks: shaped.chunks,
    runId: runResult.runId
  };
}

export function formatForChannel(reply, channel) {
  if (channel === "slack" && reply.threadId) {
    return { ...reply, thread_ts: reply.threadId };
  }
  return reply;
}

export function emitTypingEvent({ channel, to }) {
  return { stream: "delivery", phase: "typing", channel, to };
}

export function createDeadLetterLog() {
  const values = [];
  return {
    add(entry) {
      values.push(entry);
    },
    entries() {
      return values;
    }
  };
}

export function createRetryingTransport(transport, { retries = 2, deadLetters } = {}) {
  return {
    async send(reply) {
      let lastError;
      for (let attempt = 0; attempt <= retries; attempt += 1) {
        try {
          return await transport.send(reply);
        } catch (error) {
          lastError = error;
        }
      }
      deadLetters?.add({ reply, error: lastError.message });
      throw lastError;
    }
  };
}

export function createReplyDelivery({ transports }) {
  return {
    async deliver(reply) {
      if (!reply) {
        return { status: "suppressed" };
      }
      const transport = transports[reply.channel] ?? transports.webchat;
      if (!transport) {
        throw new Error(`no transport for ${reply.channel}`);
      }
      // LEARN: Reply delivery 是 agent loop 之后的边界。它负责 chunking、
      // 去重、typing/final 状态和不同渠道的格式差异，但不应该重新决定 agent 行为。
      const formatted = formatForChannel(reply, reply.channel);
      const results = [];
      for (const text of formatted.chunks ?? [formatted.text]) {
        results.push(await transport.send({ ...formatted, text }));
      }
      return results.length === 1 ? results[0] : { status: "sent", chunks: results.length, results };
    }
  };
}

export async function deliverRunResult({ request, runResult, dedupe, delivery }) {
  if (!dedupe.remember(request.idempotencyKey)) {
    return { status: "duplicate", runId: request.runId };
  }

  const reply = shapeReply({
    runResult,
    source: request.source
  });
  return delivery.deliver(reply);
}
