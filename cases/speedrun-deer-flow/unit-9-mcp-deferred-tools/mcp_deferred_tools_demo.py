from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
DEFAULT_CONFIG_PATH = CURRENT_DIR / "_demo_data" / "extensions_config.json"


@dataclass
class DemoTool:
    name: str
    description: str

    def schema(self) -> dict[str, object]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {"type": "object", "properties": {}},
        }


class MCPToolCache:
    def __init__(self, *, config_path: Path, loader):
        self.config_path = config_path
        self.loader = loader
        self._tools: list[DemoTool] | None = None
        self._config_mtime: float | None = None

    def _mtime(self) -> float | None:
        if not self.config_path.exists():
            return None
        return self.config_path.stat().st_mtime

    def is_stale(self) -> bool:
        current_mtime = self._mtime()
        if self._tools is None or self._config_mtime is None or current_mtime is None:
            return False
        # LEARN: Gateway and LangGraph do not share memory, so config file mtime
        # is enough to decide whether cached MCP tools must be refreshed.
        return current_mtime > self._config_mtime

    def get_tools(self) -> list[DemoTool]:
        if self._tools is None or self.is_stale():
            self._tools = list(self.loader())
            self._config_mtime = self._mtime()
        return self._tools


class DeferredToolRegistry:
    def __init__(self):
        self._tools: list[DemoTool] = []

    def register(self, tool: DemoTool) -> None:
        # LEARN: Deferred registry keeps full schemas out of the prompt until the
        # model searches for a tool it actually needs.
        self._tools.append(tool)

    @property
    def tools(self) -> list[DemoTool]:
        return list(self._tools)

    def search(self, query: str) -> list[DemoTool]:
        if query.startswith("select:"):
            names = {name.strip() for name in query[7:].split(",")}
            return [tool for tool in self._tools if tool.name in names]
        try:
            pattern = re.compile(query, re.IGNORECASE)
        except re.error:
            pattern = re.compile(re.escape(query), re.IGNORECASE)
        # LEARN: The model first discovers candidate tools by name/description,
        # then receives the detailed schema only for matching results.
        return [
            tool
            for tool in self._tools
            if pattern.search(f"{tool.name} {tool.description}")
        ]


def write_gateway_mcp_config(config_path: Path, servers: dict[str, object]) -> dict[str, object]:
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = {"mcpServers": servers}
    # LEARN: The gateway-style update writes file state that another process can
    # observe without relying on an in-memory singleton.
    config_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return data


def fake_mcp_loader() -> list[DemoTool]:
    return [
        DemoTool("github.search_issues", "Search GitHub issues"),
        DemoTool("github.create_issue", "Create a GitHub issue"),
        DemoTool("filesystem.read_dir", "Read a directory"),
    ]


def build_tools_with_deferred_mcp(
    *,
    base_tools: list[str],
    mcp_tools: list[DemoTool],
    tool_search_enabled: bool,
) -> tuple[list[str], DeferredToolRegistry]:
    registry = DeferredToolRegistry()
    visible_tools = list(base_tools)
    if tool_search_enabled:
        visible_tools.append("tool_search")
        for tool in mcp_tools:
            registry.register(tool)
    else:
        visible_tools.extend(tool.name for tool in mcp_tools)
    return visible_tools, registry


def run_mcp_deferred_tools_demo(*, config_path: Path | None = None) -> dict[str, object]:
    config_path = config_path or DEFAULT_CONFIG_PATH
    write_gateway_mcp_config(config_path, {"github": {"enabled": True}})
    cache = MCPToolCache(config_path=config_path, loader=fake_mcp_loader)
    mcp_tools = cache.get_tools()
    visible_tools, registry = build_tools_with_deferred_mcp(
        base_tools=["present_file", "ask_clarification"],
        mcp_tools=mcp_tools,
        tool_search_enabled=True,
    )
    matches = registry.search("github")
    return {
        "config_path": str(config_path),
        "cache_stale": cache.is_stale(),
        "visible_tools": visible_tools,
        "deferred_tools": [tool.name for tool in registry.tools],
        "search_query": "github",
        "search_results": [asdict(tool) | {"schema": tool.schema()} for tool in matches],
    }


def run_demo() -> dict[str, object]:
    return run_mcp_deferred_tools_demo()
