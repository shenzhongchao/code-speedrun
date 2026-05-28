import "dotenv/config";

import { runFeishuQrRegistration, writeFeishuEnvFile } from "./entry.js";

const domain = process.env.FEISHU_DOMAIN ?? "feishu";

console.log("Feishu scan-to-create setup");
console.log("This only obtains App ID/App Secret and writes .env.");
console.log("The real event connection still uses WebSocket in feishu-gateway.js.");

const credentials = await runFeishuQrRegistration({ domain });
if (!credentials) {
  console.log("Feishu QR setup did not complete.");
  process.exitCode = 1;
} else {
  const { envPath } = await writeFeishuEnvFile({ credentials });
  console.log(`Saved Feishu credentials to ${envPath}`);
  console.log(`Bot: ${credentials.botName ?? "unknown"}`);
  console.log("Next: npm run unit:2:feishu");
}
