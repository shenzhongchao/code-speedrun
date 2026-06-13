# Unit 9: MCP Deferred Tools

> **Motto**: *Do not show every tool until the agent asks*

## In Plain Language

MCP server 可能一下子带来很多外部工具。如果把所有工具 schema 都塞进 prompt，模型上下文会很快被工具说明淹没。DeerFlow 的做法是：先把 MCP 工具放进 deferred registry，只暴露 `tool_search`，等模型真的需要某类工具时再搜索并取回详细 schema。

## Background Knowledge

- **MCP server 像外部工具仓库**：GitHub、filesystem、Slack 这类能力可以从外部 server 来。
- **配置文件像跨进程公告板**：Gateway 更新 MCP config，LangGraph 进程靠文件 mtime 发现变化。
- **cache 像工具清单快照**：不必每轮都重新连 MCP server，但配置变了要刷新。
- **deferred registry 像仓库索引**：先存 tool name 和 description，完整 schema 延迟加载。
- **tool_search 像检索入口**：模型先问“有没有 GitHub 相关工具”，再拿匹配工具的完整定义。

## Key Terminology

- **MCP**：Model Context Protocol，用来接外部工具 server
- **MCPToolCache**：按 config mtime 缓存 MCP tools
- **DeferredToolRegistry**：保存暂不直接暴露给模型的工具
- **tool_search**：让模型检索 deferred tools 的内置工具
- **mtime**：配置文件最后修改时间，用来判断 cache 是否 stale

## What This Unit Does

这个单元保留了 MCP deferred tools 里五个关键动作：

1. 模拟 Gateway 写入 MCP server config
2. MCP cache 记录 `extensions_config.json` 的 mtime
3. 配置变化后 cache 能判断 stale
4. fake MCP loader 返回一批工具
5. `tool_search_enabled=True` 时只暴露 `tool_search`，把 MCP tools 放进 deferred registry

学完这个单元，你应该能理解：为什么 Unit 5 只说 MCP 是工具来源，而 Unit 9 才展开 config/cache/deferred/search 的完整流程。

## Key Code Walkthrough

- `mcp_deferred_tools_demo.py:28`：`MCPToolCache` 在加载工具时记录 config mtime。
- `mcp_deferred_tools_demo.py:41`：`is_stale()` 用 mtime 判断 cache 是否过期。
- `mcp_deferred_tools_demo.py:58`：`DeferredToolRegistry` 保存暂不直接暴露的工具。
- `mcp_deferred_tools_demo.py:87`：`write_gateway_mcp_config()` 模拟 Gateway 写配置文件。
- `mcp_deferred_tools_demo.py:115`：`build_tools_with_deferred_mcp()` 决定 visible tools 和 deferred tools。

## How to Run

```bash
cd cases/speedrun-deer-flow
python unit-9-mcp-deferred-tools/main.py
```

## Expected Output

你应该看到：

- `visible_tools` 里包含 `tool_search`
- `visible_tools` 里不直接包含 `github.search_issues`
- `deferred_tools` 里包含 GitHub 和 filesystem MCP tools
- `search_query` 是 `github`
- `search_results` 返回 GitHub 相关工具 schema

## Exercises

### Explain It Back

为什么 DeerFlow 用 config file mtime 判断 MCP cache 是否 stale，而不是假设一个 Python singleton 能跨进程同步？

为什么 `tool_search` 比直接暴露所有 MCP tool schema 更节省上下文？

### Modify It

- 把 `tool_search_enabled` 改成 `False`，观察 MCP tools 是否直接进入 `visible_tools`。
- 给 `fake_mcp_loader()` 加一个 Slack 工具，再用 `registry.search("slack")` 查它。

## Debug Guide

### Observation Points

File: `mcp_deferred_tools_demo.py:28`
What to observe: cache 什么时候记录 config mtime
Breakpoint or log: 查看 `_config_mtime`

File: `mcp_deferred_tools_demo.py:41`
What to observe: 文件 mtime 变化怎样让 cache stale
Breakpoint or log: 查看 `current_mtime`

File: `mcp_deferred_tools_demo.py:58`
What to observe: deferred registry 存了哪些工具
Breakpoint or log: 查看 `self._tools`

File: `mcp_deferred_tools_demo.py:115`
What to observe: deferred 模式下 visible tools 为什么只有 `tool_search`
Breakpoint or log: 查看 `visible_tools`

### Common Failures

Symptom: cache 永远不 stale
Cause: 配置文件没有真的被重写，或者文件系统 mtime 没推进
Fix: 等待很短时间后重写 config
Verify: `cache.is_stale()` 返回 `true`

Symptom: search 没有结果
Cause: query 没匹配 tool name 或 description
Fix: 查看 `registry.tools`
Verify: 用已知关键词重新搜索

### State Inspection

- 用 `python -m pdb unit-9-mcp-deferred-tools/main.py`
- 在 `mcp_deferred_tools_demo.py:132` 后检查 `mcp_tools`
- 在 `mcp_deferred_tools_demo.py:137` 后检查 `registry.tools`
- 在 `mcp_deferred_tools_demo.py:142` 后检查 `matches`

### Isolation Testing

- 只测 cache：手工写 config，new `MCPToolCache`，再改 config mtime
- 只测 deferred search：new `DeferredToolRegistry` 后 register 两个 `DemoTool`
- 只测 visible tools：直接调用 `build_tools_with_deferred_mcp(...)`
