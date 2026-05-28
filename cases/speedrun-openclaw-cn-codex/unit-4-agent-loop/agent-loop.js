import OpenAI from "openai";
import { Agent } from "@mariozechner/pi-agent-core";
import { completeSimple } from "@mariozechner/pi-ai";

export function createSessionLane() {
  const chains = new Map();

  return {
    enqueue(sessionKey, job) {
      // LEARN: A session lane is a promise chain keyed by sessionKey.
      // Runs in the same conversation append to the same chain, so history writes
      // and tool side effects cannot interleave. Different session keys get
      // different chains and may still run at the same time.
      const previous = chains.get(sessionKey) ?? Promise.resolve();
      const next = previous.then(job, job);
      chains.set(sessionKey, next.catch(() => undefined));
      return next;
    }
  };
}

export function createLifecycleBus() {
  const events = [];
  const waiters = new Map();
  const listeners = new Set();

  return {
    emit(event) {
      // LEARN: The bus is the observable spine of an agent run. UI, logs, tests,
      // and `agent.wait` all consume the same event stream instead of guessing
      // from the final text payload.
      events.push(event);
      for (const listener of listeners) {
        listener(event);
      }
      if (
        event.stream === "lifecycle"
        && (event.phase === "end" || event.phase === "error")
        && waiters.has(event.runId)
      ) {
        for (const resolve of waiters.get(event.runId)) {
          resolve(event);
        }
        waiters.delete(event.runId);
      }
    },

    waitForEnd(runId, { timeoutMs } = {}) {
      // LEARN: `agent.wait` waits for terminal lifecycle events only. A tool end
      // event is not enough, because a model may need another turn after the
      // tool result before there is a final answer.
      const existing = events.find(
        (event) => event.stream === "lifecycle"
          && event.runId === runId
          && (event.phase === "end" || event.phase === "error")
      );
      if (existing) {
        return Promise.resolve(existing);
      }
      return new Promise((resolve) => {
        const resolves = waiters.get(runId) ?? [];
        resolves.push(resolve);
        waiters.set(runId, resolves);

        if (timeoutMs !== undefined) {
          setTimeout(() => {
            const current = waiters.get(runId) ?? [];
            waiters.set(runId, current.filter((candidate) => candidate !== resolve));
            resolve({ stream: "lifecycle", phase: "timeout", runId });
          }, timeoutMs);
        }
      });
    },

    subscribe(listener) {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },

    snapshot() {
      return events;
    }
  };
}

export function createOpenAICompatibleLLM({
  apiKey = process.env.OPENAI_API_KEY,
  baseURL = process.env.OPENAI_BASE_URL ?? "https://api.openai.com/v1",
  model = process.env.OPENAI_MODEL ?? "gpt-4.1-mini",
  client,
  temperature = 0.2,
  maxTokens = 600
} = {}) {
  // LEARN: This adapter is deliberately small. The rest of OpenClaw should not
  // know which provider is behind the model; it should only hand over messages
  // and tool schemas, then receive text or tool-call requests back.
  const openai = client ?? new OpenAI({ apiKey, baseURL });

  return {
    provider: "openai-compatible",
    model,
    baseURL,

    async complete({ messages, tools = [] }) {
      // LEARN: OpenAI-compatible APIs expect tools in "function" wrappers.
      // Internally this speedrun uses the simpler `{ name, description,
      // parameters }` shape so tools can remain provider-independent.
      const response = await openai.chat.completions.create({
        model,
        messages,
        tools: tools.length > 0 ? tools.map(toOpenAITool) : undefined,
        tool_choice: tools.length > 0 ? "auto" : undefined,
        temperature,
        max_tokens: maxTokens
      });
      const message = response.choices?.[0]?.message ?? {};
      // LEARN: The model never executes tools. It only returns structured
      // intent: tool name + JSON arguments. Unit 4 validates the tool name,
      // emits local events, and calls the guarded tool itself.
      return {
        content: message.content ?? "",
        toolCalls: (message.tool_calls ?? []).map((toolCall) => ({
          id: toolCall.id,
          name: toolCall.function.name,
          arguments: parseToolArguments(toolCall.function.arguments)
        })),
        raw: response
      };
    }
  };
}

export function createPiOpenAICompatibleLLM({
  apiKey = process.env.OPENAI_API_KEY,
  baseURL = process.env.OPENAI_BASE_URL ?? "https://api.openai.com/v1",
  model = process.env.OPENAI_MODEL ?? "gpt-4.1-mini",
  temperature = 0.2,
  maxTokens = 600
} = {}) {
  // LEARN: Pi AI needs a rich model descriptor instead of just a model string.
  // The cost/context fields are realistic placeholders so the speedrun can
  // focus on the boundary without importing OpenClaw's production model catalog.
  const piModel = {
    id: model,
    name: model,
    api: "openai-completions",
    provider: "openai",
    baseUrl: baseURL,
    reasoning: false,
    input: ["text"],
    cost: { input: 0, output: 0, cacheRead: 0, cacheWrite: 0 },
    contextWindow: 128000,
    maxTokens
  };

  return {
    provider: "pi-agent-core",
    model,
    baseURL,

    async complete({ messages, tools = [] }) {
      // LEARN: The Pi Agent SDK is still present at the boundary, but this
      // speedrun keeps tool execution in Unit 4 so lifecycle/tool events remain visible.
      new Agent({
        initialState: {
          systemPrompt: extractSystemPrompt(messages),
          model: piModel,
          tools: tools.map(toPiTool)
        },
        sessionId: "openclaw-speedrun",
        toolExecution: "sequential"
      });
      // LEARN: completeSimple performs the actual provider call through Pi AI.
      // We pass schemas to the model, but we do not let this SDK instance run
      // tools directly; otherwise Unit 4 would lose its visible tool stream.
      const response = await completeSimple(
        piModel,
        {
          systemPrompt: extractSystemPrompt(messages),
          messages: messages
            .filter((message) => message.role !== "system")
            .map(toPiMessage),
          tools: tools.map(toPiSchemaTool)
        },
        {
          apiKey,
          temperature,
          maxTokens,
          sessionId: "openclaw-speedrun",
          toolChoice: tools.length > 0 ? "auto" : "none"
        }
      );
      return fromPiAssistantMessage(response);
    }
  };
}

export function createLLMFromEnv(env = process.env) {
  // LEARN: The env switch keeps the learning units runnable without a network
  // or API key. Setting OPENCLAW_USE_REAL_LLM=true replaces only the generation
  // backend; gateway, context, tools, session lane, and delivery stay the same.
  if (env.OPENCLAW_USE_REAL_LLM !== "true") {
    return undefined;
  }
  if (!env.OPENAI_API_KEY) {
    throw new Error("OPENCLAW_USE_REAL_LLM=true requires OPENAI_API_KEY in .env or environment");
  }
  const options = {
    apiKey: env.OPENAI_API_KEY,
    baseURL: env.OPENAI_BASE_URL ?? "https://api.openai.com/v1",
    model: env.OPENAI_MODEL ?? "gpt-4.1-mini"
  };
  return env.OPENCLAW_LLM_SDK === "pi"
    ? createPiOpenAICompatibleLLM(options)
    : createOpenAICompatibleLLM(options);
}

export async function runEmbeddedAgent({ context, tools, bus, llm }) {
  const toolEvents = [];
  const assistantEvents = [];

  // LEARN: `start` is emitted when the run begins executing, not when the
  // gateway accepted it. Accepted/queued are emitted by createAgentRuntime.
  bus.emit({ stream: "lifecycle", phase: "start", runId: context.request.runId });

  try {
    const finalText = llm
      ? await runModelBackedTurn({ context, tools, bus, llm, toolEvents })
      : await runRuleBackedTurn({ context, tools, bus, toolEvents });

    // LEARN: 真实 runEmbeddedPiAgent 会桥接模型 token、tool start/end、
    // compaction、usage 和错误事件。speedrun 用离散事件表现同一个生命周期。
    for (const text of splitAssistantText(finalText)) {
      const delta = { stream: "assistant", phase: "delta", runId: context.request.runId, text };
      assistantEvents.push(delta);
      bus.emit(delta);
    }
    return {
      runId: context.request.runId,
      payloads: [{ type: "text", text: finalText }],
      events: [...toolEvents, ...assistantEvents]
    };
  } catch (error) {
    bus.emit({
      stream: "lifecycle",
      phase: "error",
      runId: context.request.runId,
      error: error.message
    });
    return {
      runId: context.request.runId,
      payloads: [{ type: "error", text: error.message }],
      events: toolEvents
    };
  }
}

async function runModelBackedTurn({ context, tools, bus, llm, toolEvents }) {
  // LEARN: The context from Unit 3 is translated into Chat Completions messages
  // only at the LLM boundary. Keeping the rest of the runtime on OpenClaw-shaped
  // objects avoids coupling gateway/session code to one provider's API.
  const messages = buildChatMessages(context);
  const first = await llm.complete({
    messages,
    tools: tools.map(toLLMTool)
  });
  const toolCalls = first.toolCalls ?? [];
  if (toolCalls.length === 0) {
    // LEARN: A normal assistant text response ends the agent turn immediately.
    // There is no tool stream because the model did not ask for local action.
    return first.content || "模型没有返回文本。";
  }

  // LEARN: When the model requests tools, the second model call must include
  // the assistant's original tool_calls message. OpenAI-compatible providers
  // use this to match each following `tool` message to its requested call id.
  const assistantToolMessage = {
    role: "assistant",
    content: first.content || null,
    tool_calls: toolCalls.map((toolCall) => ({
      id: toolCall.id,
      type: "function",
      function: {
        name: toolCall.name,
        arguments: JSON.stringify(toolCall.arguments ?? {})
      }
    }))
  };
  const toolResultMessages = [];
  for (const toolCall of toolCalls) {
    // LEARN: Tool lookup happens by name. Unknown tool names are treated as
    // runtime errors instead of being silently ignored, because silent ignore
    // would make the model believe an action happened when it did not.
    const tool = tools.find((candidate) => candidate.name === toolCall.name);
    if (!tool) {
      throw new Error(`Unknown tool requested by model: ${toolCall.name}`);
    }
    const args = {
      ...(toolCall.arguments ?? {}),
      sessionKey: context.request.sessionKey
    };
    // LEARN: Tool events are emitted around the guarded local call. This is the
    // point where policy, hooks, sandbox rules, and audit metadata can act on
    // model-generated intent before any side effect occurs.
    const start = { stream: "tool", phase: "start", runId: context.request.runId, tool: tool.name, args };
    toolEvents.push(start);
    bus.emit(start);
    const result = await tool.call(args, context);
    const end = { stream: "tool", phase: "end", runId: context.request.runId, tool: tool.name, result };
    toolEvents.push(end);
    bus.emit(end);
    toolResultMessages.push({
      role: "tool",
      tool_call_id: toolCall.id,
      name: tool.name,
      content: JSON.stringify(result)
    });
  }

  // LEARN: The final model call sees the original request plus tool results.
  // That lets the model convert structured side effects into a human-facing
  // answer while reply delivery remains a separate Unit 6 concern.
  const final = await llm.complete({
    messages: [...messages, assistantToolMessage, ...toolResultMessages],
    tools: tools.map(toLLMTool)
  });
  return final.content || "工具已执行，但模型没有返回最终文本。";
}

async function runRuleBackedTurn({ context, tools, bus, toolEvents }) {
  // LEARN: The rule backend mirrors the same event shape as the model backend.
  // That is why the rest of the speedrun can run offline and still teach the
  // queue/tool/delivery lifecycle correctly.
  const reminder = tools.find((tool) => tool.name === "calendar.create");
  if (reminder && /提醒|remind/i.test(context.request.text)) {
    const args = {
      title: "检查部署状态",
      when: "tomorrow 09:00",
      sessionKey: context.request.sessionKey
    };
    const start = { stream: "tool", phase: "start", runId: context.request.runId, tool: reminder.name, args };
    toolEvents.push(start);
    bus.emit(start);
    const result = await reminder.call(args, context);
    const end = { stream: "tool", phase: "end", runId: context.request.runId, tool: reminder.name, result };
    toolEvents.push(end);
    bus.emit(end);
  }

  return toolEvents.length > 0
    ? "已为明早 9 点创建部署状态检查提醒。"
    : `收到：${context.request.text}`;
}

function splitAssistantText(text) {
  if (text.length <= 12) {
    return [text];
  }
  return text.match(/.{1,12}/gu) ?? [text];
}

function buildChatMessages(context) {
  const messages = [];
  if (context.systemPrompt) {
    messages.push({ role: "system", content: context.systemPrompt });
  }
  for (const entry of context.transcript ?? []) {
    if (entry.role === "user" || entry.role === "assistant" || entry.role === "system") {
      messages.push({ role: entry.role, content: entry.content });
    }
  }
  // LEARN: Some prepared contexts already include the latest user turn in
  // transcript. This guard prevents sending the same user message twice.
  if (!messages.some((message) => message.role === "user" && message.content === context.request.text)) {
    messages.push({ role: "user", content: context.request.text });
  }
  return messages;
}

function toLLMTool(tool) {
  // LEARN: This is the provider-neutral schema shape used inside Unit 4.
  // Individual SDK adapters can wrap or rename fields later.
  return {
    name: tool.name,
    description: tool.description ?? tool.name,
    parameters: tool.parameters ?? {
      type: "object",
      properties: {},
      additionalProperties: true
    }
  };
}

function toOpenAITool(tool) {
  // LEARN: OpenAI-compatible Chat Completions expects tools under
  // `{ type: "function", function: ... }`, even when the provider is a local
  // or third-party service that only mimics the OpenAI API.
  return {
    type: "function",
    function: {
      name: tool.name,
      description: tool.description ?? tool.name,
      parameters: tool.parameters ?? {
        type: "object",
        properties: {},
        additionalProperties: true
      }
    }
  };
}

function parseToolArguments(raw) {
  if (!raw) {
    return {};
  }
  try {
    return JSON.parse(raw);
  } catch {
    // LEARN: Bad JSON from a model is recoverable in this teaching unit. A
    // production runtime would surface a structured model/tool-call error and
    // may ask the model to repair the arguments.
    return {};
  }
}

function extractSystemPrompt(messages) {
  return messages.find((message) => message.role === "system")?.content ?? "";
}

function toPiMessage(message) {
  const timestamp = Date.now();
  if (message.role === "tool") {
    // LEARN: Pi AI calls tool-result messages `toolResult`, while OpenAI calls
    // the same concept `tool`. This adapter is the only place that difference
    // should leak into the speedrun.
    return {
      role: "toolResult",
      toolCallId: message.tool_call_id,
      toolName: message.name,
      content: [{ type: "text", text: message.content }],
      isError: false,
      timestamp
    };
  }
  if (message.role === "assistant") {
    // LEARN: Pi represents assistant output as typed content blocks. Text and
    // tool calls live in one array, so replaying a prior OpenAI assistant
    // message requires splitting it into those blocks.
    const content = [];
    if (message.content) {
      content.push({ type: "text", text: message.content });
    }
    for (const toolCall of message.tool_calls ?? []) {
      content.push({
        type: "toolCall",
        id: toolCall.id,
        name: toolCall.function.name,
        arguments: parseToolArguments(toolCall.function.arguments)
      });
    }
    return {
      role: "assistant",
      content,
      api: "openai-completions",
      provider: "openai",
      model: process.env.OPENAI_MODEL ?? "gpt-4.1-mini",
      usage: emptyUsage(),
      stopReason: content.some((part) => part.type === "toolCall") ? "toolUse" : "stop",
      timestamp
    };
  }
  return {
    role: "user",
    content: message.content,
    timestamp
  };
}

function toPiTool(tool) {
  // LEARN: This shape is what pi-agent-core uses when it owns tool execution.
  // We instantiate it to show the SDK boundary, but real execution in this
  // speedrun still goes through `tool.call()` in runModelBackedTurn.
  return {
    name: tool.name,
    label: tool.name,
    description: tool.description ?? tool.name,
    parameters: tool.parameters ?? {
      type: "object",
      properties: {},
      additionalProperties: true
    },
    async execute(toolCallId, params) {
      const result = await tool.call(params, { request: { runId: toolCallId, sessionKey: "" } });
      return {
        content: [{ type: "text", text: JSON.stringify(result) }],
        details: result
      };
    }
  };
}

function toPiSchemaTool(tool) {
  // LEARN: completeSimple only needs the schema visible to the model. It does
  // not need an execute function because Unit 4 handles execution after the
  // model returns tool calls.
  return {
    name: tool.name,
    description: tool.description ?? tool.name,
    parameters: tool.parameters ?? {
      type: "object",
      properties: {},
      additionalProperties: true
    }
  };
}

function fromPiAssistantMessage(message) {
  if (!message) {
    return { content: "", toolCalls: [] };
  }
  // LEARN: Convert Pi's typed content blocks back into the small adapter result
  // used by runModelBackedTurn: final text plus optional tool-call intents.
  const content = message.content
    .filter((part) => part.type === "text")
    .map((part) => part.text)
    .join("");
  const toolCalls = message.content
    .filter((part) => part.type === "toolCall")
    .map((part) => ({
      id: part.id,
      name: part.name,
      arguments: part.arguments
    }));
  return { content, toolCalls };
}

function emptyUsage() {
  return {
    input: 0,
    output: 0,
    cacheRead: 0,
    cacheWrite: 0,
    totalTokens: 0,
    cost: {
      input: 0,
      output: 0,
      cacheRead: 0,
      cacheWrite: 0,
      total: 0
    }
  };
}

export function createSessionStore(initial = {}) {
  const sessions = new Map(Object.entries(initial));

  return {
    append(sessionKey, entries) {
      // LEARN: The store writes compacted history immediately after each
      // successful run. Keeping compaction here makes the agent loop independent
      // from the storage backend.
      const current = sessions.get(sessionKey) ?? [];
      sessions.set(sessionKey, compactHistory([...current, ...entries]));
    },

    read(sessionKey) {
      return sessions.get(sessionKey) ?? [];
    },

    snapshot() {
      return Object.fromEntries(sessions.entries());
    }
  };
}

export function compactHistory(history, { maxEntries = 6 } = {}) {
  if (history.length <= maxEntries) {
    return history;
  }
  // LEARN: Real systems summarize old turns with a model. This tiny version
  // preserves the shape: one synthetic system summary plus recent messages.
  const keep = history.slice(-(maxEntries - 1));
  return [
    {
      role: "system",
      content: `Compacted ${history.length - keep.length} earlier transcript entries.`
    },
    ...keep
  ];
}

export function createAgentRuntime({ tools, sessionStore = createSessionStore(), llm } = {}) {
  const lane = createSessionLane();
  const bus = createLifecycleBus();
  const results = new Map();

  function submit(context) {
    // LEARN: `agent` returns accepted before execution finishes. The caller can
    // later call `wait(runId)` or read the result promise. This mirrors OpenClaw's
    // control-plane split between submitting a run and waiting for lifecycle end.
    bus.emit({ stream: "lifecycle", phase: "accepted", runId: context.request.runId });
    const promise = lane.enqueue(context.request.sessionKey, async () => {
      bus.emit({ stream: "lifecycle", phase: "queued", runId: context.request.runId });
      const result = await runEmbeddedAgent({ context, tools, bus, llm });
      if (!result.payloads.some((payload) => payload.type === "error")) {
        sessionStore.append(context.request.sessionKey, [
          { role: "user", content: context.request.text },
          { role: "assistant", content: result.payloads.map((payload) => payload.text).filter(Boolean).join("\n") }
        ]);
        bus.emit({ stream: "lifecycle", phase: "end", runId: context.request.runId });
      }
      results.set(context.request.runId, result);
      return result;
    });
    results.set(context.request.runId, promise);
    return {
      runId: context.request.runId,
      sessionKey: context.request.sessionKey,
      status: "accepted"
    };
  }

  return {
    submit,

    async agent(context) {
      submit(context);
      return results.get(context.request.runId);
    },

    wait(runId, options) {
      return bus.waitForEnd(runId, options);
    },

    subscribe(listener) {
      return bus.subscribe(listener);
    },

    events() {
      return bus.snapshot();
    },

    result(runId) {
      return results.get(runId);
    }
  };
}
