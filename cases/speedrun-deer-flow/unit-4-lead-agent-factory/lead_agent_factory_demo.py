from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class RuntimeFlags:
    thinking_enabled: bool = True
    reasoning_effort: str | None = None
    model_name: str | None = None
    is_plan_mode: bool = False
    subagent_enabled: bool = False


class DemoLeadAgent:
    def __init__(self, blueprint: dict[str, object]):
        self.blueprint = blueprint

    def run(
        self,
        *,
        prompt: str,
        runtime: object,
        uploaded_files: list[dict[str, str]],
        sandbox: object,
    ) -> dict[str, object]:
        # LEARN: The lead agent does not "discover" its workspace by itself.
        # Orchestration hands it runtime state up front, which keeps tool execution predictable.
        workspace_path = Path(self._runtime_value(runtime, "workspace_path"))
        workspace_path.mkdir(parents=True, exist_ok=True)
        brief_path = workspace_path / "brief.md"

        brief_lines = [
            "# DeerFlow Speedrun Brief",
            "",
            f"Prompt: {prompt}",
            f"Model: {self.blueprint['model_name']}",
            f"Uploads seen: {len(uploaded_files)}",
        ]
        for uploaded in uploaded_files:
            brief_lines.append(f"- {uploaded['filename']} -> {uploaded['virtual_path']}")

        # LEARN: This is the smallest useful tool trace: write something, read it back,
        # then inspect the workspace. It proves the agent has enough prepared context
        # to start real work inside the sandbox.
        sandbox.write_file(str(brief_path), "\n".join(brief_lines))
        brief_preview = sandbox.read_file(str(brief_path))
        directory_listing = sandbox.execute_command(f"ls -1 {workspace_path}")

        return {
            "model_name": self.blueprint["model_name"],
            "middlewares": self.blueprint["middlewares"],
            "prompt_sections": self.blueprint["prompt_sections"],
            "available_tools": self.blueprint["available_tools"],
            "tool_trace": [
                {"tool": "write_file", "target": str(brief_path)},
                {"tool": "read_file", "preview": brief_preview.splitlines()[:4]},
                {"tool": "bash", "command": f"ls -1 {workspace_path}", "output": directory_listing},
            ],
            "final_message": (
                "The lead agent now has the thread paths, uploaded file metadata, and a safe sandbox. "
                "That is the minimum shape you need before real tool calls start."
            ),
        }

    @staticmethod
    def _runtime_value(runtime: object, key: str) -> object:
        # LEARN: Accept either an object-style runtime or a dict-style runtime.
        # The teaching point is the contract ("you must provide workspace_path"), not the container type.
        if hasattr(runtime, key):
            return getattr(runtime, key)
        return runtime[key]


class LeadAgentFactory:
    def __init__(self, models: list[object]):
        self.models = models

    def create(self, flags: RuntimeFlags, available_tools: list[object]) -> DemoLeadAgent:
        model = self._resolve_model(flags.model_name)
        # LEARN: Thinking is negotiated, not assumed.
        # The request may ask for a reasoning-heavy mode, but the final agent can only enable it
        # if the chosen model actually supports that capability.
        thinking_enabled = flags.thinking_enabled and getattr(model, "supports_thinking", False)
        blueprint = {
            "model_name": getattr(model, "name", "missing-model"),
            "thinking_enabled": thinking_enabled,
            "reasoning_effort": flags.reasoning_effort if thinking_enabled else None,
            "middlewares": self._build_middlewares(flags, getattr(model, "supports_vision", False)),
            "available_tools": [getattr(tool, "name", str(tool)) for tool in available_tools],
            "prompt_sections": [
                "base system prompt",
                "skills prompt",
                "memory prompt",
            ],
        }
        return DemoLeadAgent(blueprint)

    def explain_resolution(self, flags: RuntimeFlags) -> dict[str, object]:
        model = self._resolve_model(flags.model_name)
        return {
            "requested_model": flags.model_name,
            "resolved_model": getattr(model, "name", None),
            "middlewares": self._build_middlewares(flags, getattr(model, "supports_vision", False)),
            "flags": asdict(flags),
        }

    def _resolve_model(self, requested_model_name: str | None) -> object:
        # LEARN: A requested model is a preference, not a guarantee.
        # DeerFlow falls back to the default configured model so the run still has a valid engine.
        if requested_model_name is not None:
            for model in self.models:
                if getattr(model, "name", None) == requested_model_name:
                    return model
        if not self.models:
            raise ValueError("No models configured for the demo lead agent.")
        return self.models[0]

    @staticmethod
    def _build_middlewares(flags: RuntimeFlags, supports_vision: bool) -> list[str]:
        # LEARN: Middleware is assembled like a checklist.
        # Some stations are always present, while others only appear when a runtime mode or model
        # capability makes them necessary.
        middlewares = [
            "ThreadDataMiddleware",
            "UploadsMiddleware",
            "SandboxMiddleware",
            "ToolErrorHandlingMiddleware",
            "TitleMiddleware",
            "MemoryMiddleware",
        ]
        if flags.is_plan_mode:
            middlewares.append("TodoMiddleware")
        if supports_vision:
            middlewares.append("ViewImageMiddleware")
        if flags.subagent_enabled:
            middlewares.append("SubagentLimitMiddleware")
        middlewares.extend(
            [
                "LoopDetectionMiddleware",
                "ClarificationMiddleware",
            ]
        )
        return middlewares
