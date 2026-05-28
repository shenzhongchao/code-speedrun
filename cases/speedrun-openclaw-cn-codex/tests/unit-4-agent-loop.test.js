import assert from "node:assert/strict";
import test from "node:test";

import {
  compactHistory,
  createAgentRuntime,
  createSessionStore,
  createOpenAICompatibleLLM
} from "../unit-4-agent-loop/agent-loop.js";

function context(runId, sessionKey, text = "hello") {
  return {
    request: { runId, sessionKey, text },
    transcript: [{ role: "user", content: text }]
  };
}

test("same session runs are serialized while different sessions can overlap", async () => {
  const order = [];
  const runtime = createAgentRuntime({
    tools: [
      {
        name: "calendar.create",
        async call(args) {
          order.push(`start:${args.sessionKey}`);
          await new Promise((resolve) => setTimeout(resolve, 20));
          order.push(`end:${args.sessionKey}`);
          return { ok: true };
        }
      }
    ]
  });

  runtime.submit(context("r1", "agent:main:a", "提醒我"));
  runtime.submit(context("r2", "agent:main:a", "提醒我"));
  runtime.submit(context("r3", "agent:main:b", "提醒我"));

  await Promise.all([
    runtime.wait("r1"),
    runtime.wait("r2"),
    runtime.wait("r3")
  ]);

  assert.ok(order.indexOf("end:agent:main:a") < order.lastIndexOf("start:agent:main:a"));
  assert.ok(order.indexOf("start:agent:main:b") < order.indexOf("end:agent:main:a"));
});

test("wait timeout does not cancel a run", async () => {
  const runtime = createAgentRuntime({
    tools: [
      {
        name: "calendar.create",
        async call() {
          await new Promise((resolve) => setTimeout(resolve, 30));
          return { ok: true };
        }
      }
    ]
  });

  runtime.submit(context("slow", "agent:main:a", "提醒我"));
  const timedOut = await runtime.wait("slow", { timeoutMs: 1 });
  const finished = await runtime.wait("slow", { timeoutMs: 100 });

  assert.equal(timedOut.phase, "timeout");
  assert.equal(finished.stream, "lifecycle");
  assert.equal(finished.phase, "end");
});

test("tool error emits lifecycle error", async () => {
  const runtime = createAgentRuntime({
    tools: [
      {
        name: "calendar.create",
        async call() {
          throw new Error("boom");
        }
      }
    ]
  });

  runtime.submit(context("err", "agent:main:a", "提醒我"));
  const result = await runtime.wait("err");

  assert.equal(result.phase, "error");
  assert.match(result.error, /boom/);
});

test("run end writes session history", async () => {
  const sessionStore = createSessionStore();
  const runtime = createAgentRuntime({ tools: [], sessionStore });

  runtime.submit(context("done", "agent:main:a", "plain question"));
  await runtime.wait("done");

  assert.ok(sessionStore.read("agent:main:a").some((entry) => entry.role === "assistant"));
});

test("long history compaction keeps a summary and recent turns", () => {
  const history = Array.from({ length: 8 }, (_, index) => ({
    role: index % 2 === 0 ? "user" : "assistant",
    content: `message ${index}`
  }));

  const compacted = compactHistory(history, { maxEntries: 4 });

  assert.equal(compacted[0].role, "system");
  assert.match(compacted[0].content, /Compacted/);
  assert.equal(compacted.length, 4);
});

test("OpenAI-compatible LLM adapter sends context as chat completions", async () => {
  const calls = [];
  const llm = createOpenAICompatibleLLM({
    apiKey: "test-key",
    baseURL: "https://llm.example/v1",
    model: "test-model",
    client: {
      chat: {
        completions: {
          async create(request) {
            calls.push(request);
            return {
              choices: [
                {
                  message: {
                    content: "模型回复"
                  }
                }
              ]
            };
          }
        }
      }
    }
  });

  const response = await llm.complete({
    messages: [
      { role: "system", content: "默认用中文简洁回复。" },
      { role: "user", content: "你好" }
    ],
    tools: [
      {
        name: "calendar.create",
        description: "创建提醒",
        parameters: {
          type: "object",
          properties: {
            title: { type: "string" }
          },
          required: ["title"]
        }
      }
    ]
  });

  assert.equal(response.content, "模型回复");
  assert.equal(calls[0].model, "test-model");
  assert.deepEqual(calls[0].messages.at(-1), { role: "user", content: "你好" });
  assert.equal(calls[0].tools[0].type, "function");
  assert.equal(calls[0].tools[0].function.name, "calendar.create");
});

test("agent loop executes LLM tool calls and asks the model for final text", async () => {
  const seenMessages = [];
  const llm = {
    async complete({ messages }) {
      seenMessages.push(messages);
      if (seenMessages.length === 1) {
        return {
          content: "",
          toolCalls: [
            {
              id: "call-1",
              name: "calendar.create",
              arguments: {
                title: "检查部署状态",
                when: "tomorrow 09:00"
              }
            }
          ]
        };
      }
      return { content: "已为明早 9 点创建部署状态检查提醒。" };
    }
  };
  const runtime = createAgentRuntime({
    llm,
    tools: [
      {
        name: "calendar.create",
        description: "创建提醒",
        parameters: {
          type: "object",
          properties: {
            title: { type: "string" },
            when: { type: "string" },
            sessionKey: { type: "string" }
          },
          required: ["title", "when", "sessionKey"]
        },
        async call(args) {
          return { id: "evt-1", ...args };
        }
      }
    ]
  });

  const result = await runtime.agent(context("llm-tools", "agent:main:a", "明早提醒我看部署状态"));

  assert.equal(result.payloads[0].text, "已为明早 9 点创建部署状态检查提醒。");
  assert.ok(runtime.events().some((event) => event.stream === "tool" && event.phase === "end"));
  assert.equal(seenMessages.length, 2);
  assert.equal(seenMessages[1].at(-1).role, "tool");
  assert.match(seenMessages[1].at(-1).content, /evt-1/);
});
