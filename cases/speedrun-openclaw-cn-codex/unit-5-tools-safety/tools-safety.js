export function createHookRunner(hooks = {}) {
  return {
    async run(name, payload) {
      // LEARN: Hooks are ordered transforms. Each hook receives the previous
      // hook's output, so plugins can layer audit fields, argument rewrites, or
      // block decisions without owning the final execution logic.
      let current = payload;
      for (const hook of hooks[name] ?? []) {
        current = (await hook(current)) ?? current;
      }
      return current;
    },

    has(name) {
      return (hooks[name] ?? []).length > 0;
    }
  };
}

export function resolveToolPolicy({ toolName, channelPolicy, sandboxMode }) {
  // LEARN: Policy is evaluated before hooks and before the tool body. This keeps
  // hard safety rules outside the LLM and outside plugin code.
  if (channelPolicy?.deny?.includes(toolName)) {
    return { decision: "deny", reason: "channel policy denied this tool" };
  }
  if (sandboxMode === "all" && toolName === "exec.host") {
    return { decision: "deny", reason: "sandboxed sessions cannot use host exec" };
  }
  if (channelPolicy?.ask?.includes(toolName)) {
    return { decision: "ask", reason: "approval required" };
  }
  return { decision: "allow", reason: "default allow" };
}

export function resolvePolicyMatrix({ toolName, channel, chatType, model, sandboxMode, matrix = [] }) {
  const match = matrix.find((row) => {
    return row.toolName === toolName
      && (!row.channel || row.channel === channel)
      && (!row.chatType || row.chatType === chatType)
      && (!row.model || row.model === model)
      && (!row.sandboxMode || row.sandboxMode === sandboxMode);
  });
  if (match) {
    return { decision: match.decision, reason: match.reason ?? "matched policy matrix" };
  }
  return resolveToolPolicy({ toolName, channelPolicy: {}, sandboxMode });
}

export function createGuardedTool({ tool, hookRunner, channelPolicy, sandboxMode }) {
  return {
    name: tool.name,
    // LEARN: description/parameters are preserved on the guarded wrapper so Unit
    // 4 can expose the same safe tool to the model as a JSON Schema function.
    description: tool.description,
    parameters: tool.parameters,
    async call(args, context) {
      // LEARN: The model may generate args, but the local runtime still decides
      // whether the call is allowed. This is the core "LLM proposes, runtime
      // disposes" boundary.
      const policy = resolveToolPolicy({
        toolName: tool.name,
        channelPolicy,
        sandboxMode
      });

      if (policy.decision === "deny") {
        throw new Error(`${tool.name} blocked: ${policy.reason}`);
      }

      // LEARN: before_tool_call 是 OpenClaw 的关键扩展点之一。插件可以审计、
      // 改写参数或阻止危险调用；硬约束仍由 tool policy/sandbox 执行。
      const adjusted = hookRunner.has("before_tool_call")
        ? await hookRunner.run("before_tool_call", { toolName: tool.name, args, context, policy })
        : { toolName: tool.name, args, context, policy };

      if (adjusted.block === true) {
        throw new Error(`${tool.name} blocked by hook`);
      }

      const result = await tool.call(adjusted.args, context);

      return hookRunner.has("after_tool_call")
        ? hookRunner.run("after_tool_call", { toolName: tool.name, args: adjusted.args, result, context, policy })
        : result;
    }
  };
}

export function loadEligibleSkills({ skills, availableBinaries, enabledSkills }) {
  return skills.filter((skill) => {
    if (!enabledSkills.includes(skill.name)) {
      return false;
    }
    return (skill.requires ?? []).every((binary) => availableBinaries.includes(binary));
  });
}

export function loadSkillFromMarkdown(markdown, { enabledSkills = [], availableBinaries = [] } = {}) {
  const frontmatter = markdown.match(/^---\n([\s\S]*?)\n---/);
  const body = frontmatter ? markdown.slice(frontmatter[0].length).trim() : markdown.trim();
  const metadata = {};

  for (const line of (frontmatter?.[1] ?? "").split("\n")) {
    const [key, ...rest] = line.split(":");
    if (!key || rest.length === 0) {
      continue;
    }
    metadata[key.trim()] = rest.join(":").trim();
  }

  const name = metadata.name ?? body.match(/^#\s+(.+)$/m)?.[1]?.toLowerCase().replace(/\s+/g, "-");
  const requires = metadata.requires
    ? metadata.requires.split(",").map((item) => item.trim()).filter(Boolean)
    : [];

  if (!name || !enabledSkills.includes(name)) {
    return null;
  }
  if (!requires.every((binary) => availableBinaries.includes(binary))) {
    return null;
  }

  return {
    name,
    description: body.split("\n").find((line) => line.trim() && !line.startsWith("#")) ?? "",
    requires,
    body
  };
}

export function createApprovalQueue() {
  let nextId = 1;
  const requests = new Map();

  return {
    request({ toolName, args, reason }) {
      const approvalId = `approval-${nextId++}`;
      requests.set(approvalId, { approvalId, toolName, args, reason, status: "pending" });
      return requests.get(approvalId);
    },

    approve(approvalId) {
      const request = requests.get(approvalId);
      if (request) {
        request.status = "approved";
      }
    },

    reject(approvalId, reason = "rejected") {
      const request = requests.get(approvalId);
      if (request) {
        request.status = "rejected";
        request.reason = reason;
      }
    },

    get(approvalId) {
      return requests.get(approvalId);
    }
  };
}

export async function runToolWithApproval({ tool, args, policy, approvals, context = {} }) {
  if (policy.decision === "deny") {
    throw new Error(`${tool.name} blocked: ${policy.reason}`);
  }

  if (policy.decision !== "ask") {
    return { status: "ok", result: await tool.call(args, context) };
  }

  const request = approvals.request({ toolName: tool.name, args, reason: policy.reason });
  return {
    status: "approval_required",
    approvalId: request.approvalId,
    async resume() {
      const latest = approvals.get(request.approvalId);
      if (latest.status === "approved") {
        return { status: "ok", result: await tool.call(args, context) };
      }
      if (latest.status === "rejected") {
        throw new Error(latest.reason);
      }
      throw new Error("approval still pending");
    }
  };
}

export function assertWithinWorkspace(path, workspaceRoot) {
  const normalizedRoot = normalizePath(workspaceRoot);
  const normalizedPath = normalizePath(path);
  if (normalizedPath === normalizedRoot || normalizedPath.startsWith(`${normalizedRoot}/`)) {
    return normalizedPath;
  }
  throw new Error(`path outside workspace: ${path}`);
}

function normalizePath(path) {
  const parts = [];
  const absolute = path.startsWith("/");
  for (const part of path.split("/")) {
    if (!part || part === ".") {
      continue;
    }
    if (part === "..") {
      parts.pop();
    } else {
      parts.push(part);
    }
  }
  return `${absolute ? "/" : ""}${parts.join("/")}`;
}

export function createWorkspaceFileTool({ workspaceRoot, files = {} }) {
  const data = new Map(Object.entries(files));
  const resolve = (path) => assertWithinWorkspace(
    path.startsWith("/") ? path : `${workspaceRoot}/${path}`,
    workspaceRoot
  );

  return {
    async read({ path }) {
      return data.get(resolve(path)) ?? "";
    },

    async write({ path, content }) {
      data.set(resolve(path), content);
      return { ok: true };
    }
  };
}
