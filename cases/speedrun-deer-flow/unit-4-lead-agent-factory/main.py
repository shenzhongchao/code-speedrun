from __future__ import annotations

import json
import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
sys.path.insert(0, str(ROOT_DIR / "unit-2-gateway-config"))
sys.path.insert(0, str(ROOT_DIR / "unit-5-tools-sandbox"))

from gateway_config_demo import build_demo_config  # noqa: E402
from lead_agent_factory_demo import LeadAgentFactory, RuntimeFlags  # noqa: E402
from tools_sandbox_demo import LocalSandbox, build_tool_registry  # noqa: E402


def run_demo() -> dict[str, object]:
    config = build_demo_config()
    registry = build_tool_registry(config.tools)
    available_tools = registry.resolve_tools(model_supports_vision=True, subagent_enabled=True)
    sandbox = LocalSandbox("local")
    runtime = {"workspace_path": str(CURRENT_DIR / "_demo_data" / "workspace")}

    agent = LeadAgentFactory(config.models).create(
        RuntimeFlags(
            thinking_enabled=True,
            reasoning_effort="medium",
            model_name="gpt-5-responses",
            is_plan_mode=True,
            subagent_enabled=True,
        ),
        available_tools=available_tools,
    )
    result = agent.run(
        prompt="Summarize the repo and decide whether to call subagents.",
        runtime=runtime,
        uploaded_files=[{"filename": "roadmap.docx", "virtual_path": "/mnt/user-data/uploads/roadmap.docx"}],
        sandbox=sandbox,
    )
    return result


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
