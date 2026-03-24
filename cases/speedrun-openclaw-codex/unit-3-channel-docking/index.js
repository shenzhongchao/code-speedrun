import {
  createChannelManager,
  createChannelRegistry,
  createTelegramPlugin
} from "./channel-docking.js";

const registry = createChannelRegistry([createTelegramPlugin()]);
const manager = createChannelManager({ registry });

await manager.startAll({
  channels: {
    telegram: {
      accounts: ["personal"]
    }
  }
});

console.log("Running channel runtimes:");
console.log(manager.snapshot());

console.log("\nNormalized inbound event:");
console.log(
  manager.receive({
    channelId: "telegram",
    accountId: "personal",
    rawEvent: {
      messageId: "tg-42",
      sender: "@teal-user",
      chatId: "@teal-user",
      senderName: "Teal User",
      text: "Can you triage the build failures?",
      chatType: "direct"
    }
  })
);
