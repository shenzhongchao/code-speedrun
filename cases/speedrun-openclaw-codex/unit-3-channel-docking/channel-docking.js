function sortPlugins(plugins) {
  return [...plugins].sort((left, right) => {
    const leftOrder = left.order ?? 999;
    const rightOrder = right.order ?? 999;
    if (leftOrder !== rightOrder) {
      return leftOrder - rightOrder;
    }
    return left.id.localeCompare(right.id);
  });
}

export function createChannelRegistry(plugins) {
  const sorted = sortPlugins(plugins);
  const byId = new Map(sorted.map((plugin) => [plugin.id, plugin]));

  return {
    list() {
      return sorted.slice();
    },
    get(channelId) {
      return byId.get(channelId);
    }
  };
}

export function createChannelManager({ registry }) {
  const runtimes = new Map();

  function runtimeKey(channelId, accountId) {
    return `${channelId}:${accountId}`;
  }

  async function startChannel(channelId, config) {
    const plugin = registry.get(channelId);
    if (!plugin) {
      throw new Error(`Unknown channel plugin: ${channelId}`);
    }

    const accountIds = plugin.listAccountIds(config);
    for (const accountId of accountIds) {
      const nextRuntime = {
        channelId,
        accountId,
        running: true,
        configured: true,
        lastStartReason: "speedrun-start"
      };

      // LEARN: The gateway treats each channel account like a little appliance:
      // plug it in, mark it healthy, and keep a status card nearby.
      // Why: the control plane needs one uniform view across very different providers.
      runtimes.set(runtimeKey(channelId, accountId), nextRuntime);

      if (typeof plugin.startAccount === "function") {
        await plugin.startAccount({ accountId, config, runtime: nextRuntime });
      }
    }
  }

  return {
    async startAll(config) {
      for (const plugin of registry.list()) {
        await startChannel(plugin.id, config);
      }
    },
    snapshot() {
      return Array.from(runtimes.values());
    },
    receive({ channelId, accountId, rawEvent }) {
      const plugin = registry.get(channelId);
      if (!plugin) {
        throw new Error(`Unknown channel plugin: ${channelId}`);
      }

      const normalized = plugin.normalizeInbound({ accountId, rawEvent });
      return {
        ...normalized,
        channelId,
        accountId,
        provider: channelId,
        surface: channelId,
        originatingChannel: channelId,
        originatingTo: normalized.from
      };
    }
  };
}

export function createTelegramPlugin() {
  return {
    id: "telegram",
    order: 20,
    listAccountIds(config) {
      return config.channels.telegram.accounts;
    },
    async startAccount({ accountId }) {
      return {
        accountId,
        mode: "polling"
      };
    },
    normalizeInbound({ accountId, rawEvent }) {
      return {
        messageId: rawEvent.messageId,
        text: rawEvent.text,
        from: rawEvent.sender,
        to: rawEvent.chatId,
        chatType: rawEvent.chatType ?? "direct",
        senderName: rawEvent.senderName ?? rawEvent.sender,
        threadId: rawEvent.threadId,
        accountId
      };
    }
  };
}
