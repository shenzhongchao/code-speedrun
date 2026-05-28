import assert from "node:assert/strict";
import test from "node:test";

import {
  applyPromptBudget,
  createWorkspaceStore,
  discoverSkills,
  loadBootstrapFiles,
  prepareRunContext,
  rankMemory,
  resolveSessionHistory
} from "../unit-3-session-context/session-context.js";

const config = {
  agents: {
    defaultAgent: "main",
    list: {
      main: { workspace: "/workspace/main" }
    }
  }
};

test("session key resolves to the configured agent workspace", () => {
  const context = prepareRunContext({
    request: { runId: "r1", sessionKey: "agent:main:telegram:@u", text: "部署检查" },
    config,
    workspaceFiles: { "AGENTS.md": "中文回复" },
    memoryEntries: [],
    skills: [],
    now: "2026-05-07"
  });

  assert.equal(context.agentScope.agentId, "main");
  assert.equal(context.agentScope.workspace, "/workspace/main");
});

test("missing bootstrap files are represented by markers", () => {
  const files = loadBootstrapFiles({
    workspace: "/workspace/main",
    store: createWorkspaceStore({ "AGENTS.md": "rules" })
  });

  assert.equal(files.find((file) => file.name === "SOUL.md").missing, true);
  assert.match(files.find((file) => file.name === "SOUL.md").content, /\[missing SOUL\.md\]/);
});

test("long bootstrap files are truncated by prompt budget", () => {
  const budgeted = applyPromptBudget({
    sections: [{ name: "AGENTS.md", content: "a".repeat(40) }],
    maxChars: 20
  });

  assert.equal(budgeted.sections[0].truncated, true);
  assert.ok(budgeted.sections[0].content.length <= 20);
});

test("title memory match ranks before body-only match", () => {
  const hits = rankMemory({
    query: "部署",
    entries: [
      { title: "购物", body: "部署相关笔记", updatedAt: "2026-05-01" },
      { title: "部署检查", body: "错误率", updatedAt: "2026-04-01" }
    ]
  });

  assert.equal(hits[0].title, "部署检查");
});

test("disabled skills and missing binaries do not enter prompt", () => {
  const skills = discoverSkills({
    workspace: "/workspace/main",
    enabledSkills: ["calendar", "deploy"],
    binaries: ["node"],
    registry: [
      { name: "calendar", description: "提醒", requires: [] },
      { name: "deploy", description: "部署", requires: ["git"] },
      { name: "music", description: "播放", requires: [] }
    ]
  });

  assert.deepEqual(skills.map((skill) => skill.name), ["calendar"]);
});

test("session history loads per session key from workspace store", () => {
  const history = resolveSessionHistory({
    sessionKey: "agent:main:telegram:@u",
    store: createWorkspaceStore({
      "sessions/agent_main_telegram__u.json": [
        { role: "user", content: "hello" }
      ]
    })
  });

  assert.equal(history[0].content, "hello");
});
