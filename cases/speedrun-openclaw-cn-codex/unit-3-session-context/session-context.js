const BOOTSTRAP_ORDER = ["AGENTS.md", "SOUL.md", "USER.md", "MEMORY.md"];
const DEFAULT_BOOTSTRAP_MAX_CHARS = 1200;

export function resolveAgentScope({ sessionKey, config }) {
  const [, agentId = config.agents.defaultAgent] = sessionKey.split(":");
  const agent = config.agents.list[agentId] ?? config.agents.list[config.agents.defaultAgent];
  return {
    agentId,
    workspace: agent.workspace,
    sessionStore: `${agent.workspace}/sessions`,
    memoryRoot: `${agent.workspace}/memory`
  };
}

export function createWorkspaceStore(files = {}) {
  const values = new Map(Object.entries(files));

  return {
    read(path) {
      return values.get(path);
    },

    write(path, value) {
      values.set(path, value);
    },

    has(path) {
      return values.has(path);
    },

    entries() {
      return Object.fromEntries(values.entries());
    }
  };
}

function readWorkspaceValue({ store, files, name }) {
  if (store) {
    return store.read(name) ?? store.read(name.replace(/^\//, ""));
  }
  return files?.[name];
}

export function loadBootstrapFiles({ workspace, files, store, maxChars = DEFAULT_BOOTSTRAP_MAX_CHARS }) {
  // LEARN: OpenClaw 会把小而稳定的身份/项目文件注入系统提示词。
  // MEMORY.md 可以注入，但 daily memory 文件通常通过工具按需读取，避免长期记忆把上下文塞满。
  return BOOTSTRAP_ORDER.map((name) => {
    const raw = readWorkspaceValue({ store, files, name });
    const missing = raw === undefined;
    const content = missing ? `[missing ${name}]` : String(raw);
    const budgeted = applyPromptBudget({
      sections: [{ name, content, missing }],
      maxChars
    }).sections[0];
    return {
      name,
      path: `${workspace}/${name}`,
      missing,
      ...budgeted
    };
  });
}

export function rankMemory({ query, entries, limit = 3, now = "2026-05-07" }) {
  const normalizedQuery = query.toLowerCase();
  const terms = normalizedQuery.split(/\s+/).filter(Boolean);
  const nowTime = Date.parse(now);
  return entries
    .map((entry) => {
      const title = String(entry.title ?? "").toLowerCase();
      const body = String(entry.body ?? "").toLowerCase();
      const titleScore = terms.filter((term) => title.includes(term)).length * 5;
      const bodyScore = terms.filter((term) => body.includes(term)).length * 2;
      const cjkTitleScore = [...title].filter((char) => /\p{Script=Han}/u.test(char) && normalizedQuery.includes(char)).length * 2;
      const cjkBodyScore = [...body].filter((char) => /\p{Script=Han}/u.test(char) && normalizedQuery.includes(char)).length;
      const ageDays = entry.updatedAt && Number.isFinite(nowTime)
        ? Math.max(0, (nowTime - Date.parse(entry.updatedAt)) / 86_400_000)
        : 365;
      const recencyScore = Math.max(0, 1 - ageDays / 365);
      const score = titleScore + bodyScore + cjkTitleScore + cjkBodyScore + recencyScore;
      return { ...entry, score };
    })
    .filter((entry) => entry.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, limit);
}

export function searchMemory({ query, memoryEntries, limit = 3 }) {
  return rankMemory({ query, entries: memoryEntries, limit });
}

export function applyPromptBudget({ sections, maxChars }) {
  let remaining = maxChars;
  const budgeted = sections.map((section) => {
    const content = String(section.content ?? "");
    const truncated = content.length > remaining;
    const nextContent = truncated ? `${content.slice(0, Math.max(0, remaining - 15))}\n[truncated]` : content;
    remaining = Math.max(0, remaining - nextContent.length);
    return { ...section, content: nextContent, truncated };
  });

  return {
    sections: budgeted,
    usedChars: budgeted.reduce((total, section) => total + section.content.length, 0),
    maxChars,
    remainingChars: remaining
  };
}

function sessionPath(sessionKey) {
  return `sessions/${sessionKey.replaceAll(":", "_").replaceAll("@", "_")}.json`;
}

export function resolveSessionHistory({ sessionKey, store }) {
  return store.read(sessionPath(sessionKey)) ?? [];
}

export function discoverSkills({ workspace, enabledSkills = [], binaries = [], registry = [] }) {
  return registry
    .filter((skill) => enabledSkills.includes(skill.name))
    .filter((skill) => (skill.requires ?? []).every((binary) => binaries.includes(binary)))
    .map((skill) => ({
      ...skill,
      path: skill.path ?? `${workspace}/skills/${skill.name}/SKILL.md`
    }));
}

export function buildContextReport(context) {
  return {
    sessionKey: context.request.sessionKey,
    agentId: context.agentScope.agentId,
    workspace: context.agentScope.workspace,
    bootstrapFiles: context.bootstrapFiles.map((file) => ({
      name: file.name,
      missing: file.missing,
      truncated: file.truncated,
      chars: file.content.length
    })),
    memoryHits: context.memoryHits.map((hit) => ({ title: hit.title, score: hit.score })),
    skills: context.skills.map((skill) => skill.name),
    promptBudget: context.promptBudget
  };
}

export function buildSystemPrompt({ agentScope, bootstrapFiles, skills, memoryHits, now }) {
  const bootstrap = bootstrapFiles
    .map((file) => `### ${file.name}\n${file.content}`)
    .join("\n\n");

  const skillList = skills
    .map((skill) => `- ${skill.name}: ${skill.description} (${skill.path})`)
    .join("\n");

  const memories = memoryHits
    .map((hit) => `- ${hit.title}: ${hit.body}`)
    .join("\n");

  // LEARN: 真实 system prompt 由 OpenClaw 拥有，不直接使用底层 agent runtime 的默认提示词。
  // 这里保留关键成分：工具/技能、工作区、bootstrap、按需召回的记忆和运行时信息。
  return [
    "You are OpenClaw, a local-first personal AI assistant.",
    `Workspace: ${agentScope.workspace}`,
    `Current date: ${now}`,
    "",
    "Available skills:",
    skillList || "- none",
    "",
    "Memory recall:",
    memories || "- no relevant memory",
    "",
    "Workspace files:",
    bootstrap
  ].join("\n");
}

export function prepareRunContext({
  request,
  config,
  workspaceFiles,
  workspaceStore,
  memoryEntries,
  skills,
  skillRegistry,
  enabledSkills,
  binaries,
  now,
  maxPromptChars = 6000
}) {
  const agentScope = resolveAgentScope({ sessionKey: request.sessionKey, config });
  const store = workspaceStore ?? createWorkspaceStore(workspaceFiles);
  const bootstrapFiles = loadBootstrapFiles({
    workspace: agentScope.workspace,
    store
  });
  const memoryHits = searchMemory({
    query: request.text,
    memoryEntries: memoryEntries ?? []
  });
  const discoveredSkills = skillRegistry
    ? discoverSkills({ workspace: agentScope.workspace, enabledSkills, binaries, registry: skillRegistry })
    : (skills ?? []);
  const systemPrompt = buildSystemPrompt({
    agentScope,
    bootstrapFiles,
    skills: discoveredSkills,
    memoryHits,
    now
  });
  const promptBudget = applyPromptBudget({
    sections: [{ name: "system", content: systemPrompt }],
    maxChars: maxPromptChars
  });
  const sessionHistory = resolveSessionHistory({ sessionKey: request.sessionKey, store });

  const context = {
    request,
    agentScope,
    bootstrapFiles,
    memoryHits,
    skills: discoveredSkills,
    sessionHistory,
    promptBudget: {
      maxChars: maxPromptChars,
      usedChars: promptBudget.usedChars,
      remainingChars: promptBudget.remainingChars
    },
    systemPrompt: promptBudget.sections[0].content,
    transcript: [
      { role: "system", content: promptBudget.sections[0].content },
      ...sessionHistory,
      { role: "user", content: request.text }
    ]
  };
  return { ...context, report: buildContextReport(context) };
}
