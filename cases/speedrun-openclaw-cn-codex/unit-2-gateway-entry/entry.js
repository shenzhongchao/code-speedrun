const DEFAULT_PORT = 18789;

function readFlag(argv, name) {
  const index = argv.indexOf(name);
  if (index === -1) {
    return undefined;
  }
  return argv[index + 1];
}

function parsePort(rawPort) {
  const parsed = Number(rawPort);
  return Number.isInteger(parsed) && parsed > 0 ? parsed : DEFAULT_PORT;
}

export function resolveGatewayPlan(argv = process.argv) {
  const tokens = argv.slice(2);
  const command = tokens.find((token) => !token.startsWith("-")) ?? "gateway";
  const port = parsePort(readFlag(tokens, "--port"));

  // LEARN: Think of this as the airport arrivals board.
  // We turn noisy CLI tokens into one clean startup decision.
  // Why: later layers should not keep reparsing argv by hand.
  return {
    command,
    port,
    startMode: command === "gateway" ? "server" : "request",
    needsGateway: command === "gateway" || command === "agent" || command === "message",
    deliverReplies: command !== "gateway"
  };
}

export function buildGatewayChatContext(params) {
  const {
    sessionKey = "agent:main:main",
    text,
    runId = "run-web-1",
    clientId = "control-ui",
    clientName = "Control UI",
    originatingChannel = "internal",
    originatingTo = "webchat",
    explicitDeliverRoute = false
  } = params;

  const trimmedText = String(text ?? "").trim();
  if (!trimmedText) {
    throw new Error("text is required");
  }

  // LEARN: This is the same move OpenClaw makes in gateway chat methods:
  // convert a UI request into a channel-shaped message envelope.
  // Why: once everything looks like a message, routing and reply code can stay shared.
  return {
    sessionKey,
    text: trimmedText,
    rawText: trimmedText,
    provider: "internal",
    surface: "internal",
    chatType: "direct",
    accountId: "control-plane",
    from: clientId,
    to: originatingTo,
    senderName: clientName,
    messageId: runId,
    originatingChannel,
    originatingTo,
    explicitDeliverRoute
  };
}
