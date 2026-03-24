export const DEFAULT_AGENT_ID = "main";
export const DEFAULT_MAIN_KEY = "main";

function normalizeToken(value, fallback = "") {
  const normalized = String(value ?? "").trim().toLowerCase();
  return normalized || fallback;
}

export function buildAgentPeerSessionKey(params) {
  const agentId = normalizeToken(params.agentId, DEFAULT_AGENT_ID);
  const channel = normalizeToken(params.channel, "unknown");
  const chatType = normalizeToken(params.chatType, "direct");
  const peerId = normalizeToken(params.peerId, "unknown");

  if (chatType === "direct") {
    return `agent:${agentId}:${channel}:direct:${peerId}`;
  }

  return `agent:${agentId}:${channel}:${chatType}:${peerId}`;
}

export function resolveSessionAgentId({ config, sessionKey, preferredAgentId }) {
  const explicit = normalizeToken(preferredAgentId);
  if (explicit) {
    return explicit;
  }

  const defaultAgent = normalizeToken(config.agents?.default, DEFAULT_AGENT_ID);
  const parts = String(sessionKey ?? "").split(":").filter(Boolean);
  return parts[0] === "agent" && parts[1] ? normalizeToken(parts[1], defaultAgent) : defaultAgent;
}

export function resolveSendPolicy({ config, channel, chatType }) {
  const rules = config.session?.sendPolicy?.rules ?? [];

  for (const rule of rules) {
    const matchChannel = normalizeToken(rule.match?.channel);
    const matchChatType = normalizeToken(rule.match?.chatType);

    if (matchChannel && matchChannel !== normalizeToken(channel)) {
      continue;
    }
    if (matchChatType && matchChatType !== normalizeToken(chatType)) {
      continue;
    }
    return rule.action;
  }

  return config.session?.sendPolicy?.default ?? "allow";
}

export function resolveTurnRoute({ config, inbound, preferredAgentId }) {
  const peerId = inbound.chatType === "direct" ? inbound.from : inbound.to;
  const agentId = resolveSessionAgentId({
    config,
    sessionKey: inbound.sessionKey,
    preferredAgentId
  });
  const sessionKey =
    inbound.sessionKey ??
    buildAgentPeerSessionKey({
      agentId,
      channel: inbound.provider ?? inbound.channelId,
      chatType: inbound.chatType,
      peerId
    });

  // LEARN: A session key is the mailbox label for the conversation.
  // It tells OpenClaw which agent memory and policy bucket this turn belongs to.
  const sendPolicy = resolveSendPolicy({
    config,
    channel: inbound.provider ?? inbound.channelId,
    chatType: inbound.chatType
  });

  return {
    agentId,
    sessionKey,
    sendPolicy,
    deliverRoute: {
      channel: inbound.originatingChannel ?? inbound.provider ?? "internal",
      to: inbound.originatingTo ?? inbound.from,
      accountId: inbound.accountId,
      threadId: inbound.threadId
    }
  };
}
