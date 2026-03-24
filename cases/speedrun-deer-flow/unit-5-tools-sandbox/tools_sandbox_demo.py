from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class ResolvedTool:
    name: str
    source: str


class LocalSandbox:
    """A tiny local sandbox matching DeerFlow's main teaching shape."""

    def __init__(self, sandbox_id: str):
        self.id = sandbox_id

    @staticmethod
    def _get_shell() -> str:
        # LEARN: The sandbox chooses the first usable shell instead of assuming one exists.
        # That fallback chain makes command execution more portable across environments.
        for shell in ("/bin/zsh", "/bin/bash", "/bin/sh"):
            if os.path.isfile(shell) and os.access(shell, os.X_OK):
                return shell
        shell_from_path = shutil.which("sh")
        if shell_from_path is None:
            raise RuntimeError("No suitable shell executable found.")
        return shell_from_path

    def execute_command(self, command: str) -> str:
        result = subprocess.run(
            command,
            executable=self._get_shell(),
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        # LEARN: Turn raw process results into one text payload.
        # This mirrors the real sandbox boundary: the agent receives stdout/stderr/exit status
        # in a single readable result instead of juggling subprocess objects.
        output = result.stdout.strip()
        if result.stderr:
            output = f"{output}\nSTDERR:\n{result.stderr.strip()}".strip()
        if result.returncode != 0:
            output = f"{output}\nExit Code: {result.returncode}".strip()
        return output or "(no output)"

    def read_file(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    def write_file(self, path: str, content: str, append: bool = False) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with target.open(mode, encoding="utf-8") as handle:
            handle.write(content)


class ToolRegistry:
    def __init__(self, config_tools: list[object]):
        self.config_tools = config_tools
        self.builtin_tools = ["present_file", "ask_clarification"]
        self.subagent_tools = ["task"]
        self.mcp_tools = ["github.search_issues", "filesystem.read_dir"]

    def resolve_tools(
        self,
        *,
        model_supports_vision: bool,
        subagent_enabled: bool,
        include_mcp: bool = True,
        tool_search_enabled: bool = True,
    ) -> list[ResolvedTool]:
        # LEARN: The visible tool list is assembled from several sources.
        # Think of this as packing a toolbox for one job: config tools are the base kit,
        # runtime flags add special attachments such as subagents, vision, and MCP search.
        resolved = [ResolvedTool(name=self._tool_name(tool), source="config") for tool in self.config_tools]
        resolved.extend(ResolvedTool(name=name, source="builtin") for name in self.builtin_tools)
        if subagent_enabled:
            resolved.extend(ResolvedTool(name=name, source="builtin") for name in self.subagent_tools)
        if model_supports_vision:
            resolved.append(ResolvedTool(name="view_image", source="builtin"))
        if include_mcp:
            resolved.extend(ResolvedTool(name=name, source="mcp") for name in self.mcp_tools)
            if tool_search_enabled:
                resolved.append(ResolvedTool(name="tool_search", source="builtin"))
        return resolved

    @staticmethod
    def _tool_name(tool: object) -> str:
        return getattr(tool, "name", str(tool))


def build_tool_registry(config_tools: list[object]) -> ToolRegistry:
    return ToolRegistry(config_tools=config_tools)


def run_demo() -> dict[str, object]:
    sandbox = LocalSandbox("local")
    base_dir = Path(__file__).resolve().parent / "_demo_data"
    note_path = base_dir / "workspace" / "hello.txt"
    # LEARN: Write before read so the learner can see the whole sandbox loop:
    # create a file, inspect it, then ask the shell what is actually in the workspace.
    sandbox.write_file(str(note_path), "sandbox writes a file before the agent reads it")

    registry = build_tool_registry(
        config_tools=[
            type("Tool", (), {"name": "bash"})(),
            type("Tool", (), {"name": "read_file"})(),
            type("Tool", (), {"name": "write_file"})(),
            type("Tool", (), {"name": "web_search"})(),
        ]
    )

    return {
        "tools": [asdict(tool) for tool in registry.resolve_tools(model_supports_vision=True, subagent_enabled=True)],
        "sandbox_read": sandbox.read_file(str(note_path)),
        "sandbox_command": sandbox.execute_command(f"ls -1 {base_dir / 'workspace'}"),
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
