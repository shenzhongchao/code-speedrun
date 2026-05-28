import { spawnSync } from "node:child_process";

const unitPrograms = [
  "unit-2-gateway-entry/index.js",
  "unit-3-session-context/index.js",
  "unit-4-agent-loop/index.js",
  "unit-5-tools-safety/index.js",
  "unit-6-reply-delivery/index.js",
  "unit-1-overall/index.js"
];

for (const program of unitPrograms) {
  console.log(`\n=== Running ${program} ===`);
  const result = spawnSync(process.execPath, [program], {
    cwd: new URL("..", import.meta.url),
    stdio: "inherit"
  });

  if (result.status !== 0) {
    process.exit(result.status ?? 1);
  }
}

console.log("\nAll speedrun units completed.");
