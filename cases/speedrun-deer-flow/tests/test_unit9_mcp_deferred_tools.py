from __future__ import annotations

import importlib.util
import sys
import time
from pathlib import Path


SPEEDRUN_ROOT = Path(__file__).resolve().parents[1]


def load_unit9():
    path = SPEEDRUN_ROOT / "unit-9-mcp-deferred-tools" / "mcp_deferred_tools_demo.py"
    spec = importlib.util.spec_from_file_location("unit9_mcp_deferred_tools_demo", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_config_mtime_change_marks_cache_stale(tmp_path):
    unit9 = load_unit9()
    config_path = tmp_path / "extensions_config.json"
    unit9.write_gateway_mcp_config(config_path, {"github": {"enabled": True}})
    cache = unit9.MCPToolCache(config_path=config_path, loader=lambda: [])
    cache.get_tools()

    time.sleep(0.01)
    unit9.write_gateway_mcp_config(config_path, {"github": {"enabled": False}})

    assert cache.is_stale() is True


def test_deferred_mode_exposes_tool_search_not_all_mcp_tools(tmp_path):
    unit9 = load_unit9()
    result = unit9.run_mcp_deferred_tools_demo(config_path=tmp_path / "extensions_config.json")

    assert "tool_search" in result["visible_tools"]
    assert "github.search_issues" not in result["visible_tools"]
    assert "github.search_issues" in result["deferred_tools"]


def test_search_returns_matching_deferred_tool():
    unit9 = load_unit9()
    registry = unit9.DeferredToolRegistry()
    registry.register(unit9.DemoTool("github.search_issues", "Search GitHub issues"))
    registry.register(unit9.DemoTool("filesystem.read_dir", "Read a directory"))

    matches = registry.search("github")

    assert [tool.name for tool in matches] == ["github.search_issues"]
