from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path


CURRENT_DIR = Path(__file__).resolve().parent
ROOT_DIR = CURRENT_DIR.parent
# LEARN: Unit 1 is the "conductor" unit. It imports the other units directly
# so the learner can watch one end-to-end flow instead of reading five isolated demos.
sys.path.insert(0, str(ROOT_DIR / "unit-2-gateway-config"))
sys.path.insert(0, str(ROOT_DIR / "unit-3-thread-runtime"))
sys.path.insert(0, str(ROOT_DIR / "unit-4-lead-agent-factory"))
sys.path.insert(0, str(ROOT_DIR / "unit-5-tools-sandbox"))

from gateway_config_demo import GatewayAPI, UploadedFile, build_demo_config  # noqa: E402
from lead_agent_factory_demo import LeadAgentFactory, RuntimeFlags  # noqa: E402
from thread_runtime_demo import ThreadRuntimeManager  # noqa: E402
from tools_sandbox_demo import LocalSandbox, build_tool_registry  # noqa: E402


def run_demo() -> dict[str, object]:
    base_dir = CURRENT_DIR / "_demo_data"
    # LEARN: Start from a clean thread workspace each run.
    # This makes the demo deterministic, so the learner sees the same files and outputs every time.
    shutil.rmtree(base_dir, ignore_errors=True)

    config = build_demo_config()
    gateway = GatewayAPI(config=config, storage_root=base_dir)

    models = gateway.list_models()
    uploads = gateway.upload_files(
        thread_id="thread-007",
        files=[
            UploadedFile(
                filename="research_brief.docx",
                content=(
                    "Goal: inspect DeerFlow backend architecture. "
                    "Need a summary of gateway, middleware, lead agent, and tools."
                ),
            ),
            UploadedFile(
                filename="constraints.txt",
                content="Scope the speedrun to Python backend. Frontend remains an external boundary.",
            ),
        ],
    )

    # LEARN: DeerFlow does not let the agent improvise file-system paths on the fly.
    # It derives a thread-scoped runtime first, then attaches a sandbox id, so later tools
    # all talk about the same workspace / uploads / outputs trio.
    thread_runtime = ThreadRuntimeManager(base_dir=base_dir, lazy_init=False).before_agent("thread-007")
    thread_runtime = ThreadRuntimeManager(base_dir=base_dir, lazy_init=False).attach_sandbox(thread_runtime)

    registry = build_tool_registry(config.tools)
    # LEARN: Tool visibility is dynamic, not hardcoded.
    # These flags mimic the real backend: model capability, subagent mode, and MCP/tool-search
    # all change what the lead agent is allowed to call.
    available_tools = registry.resolve_tools(
        model_supports_vision=True,
        subagent_enabled=True,
        include_mcp=True,
        tool_search_enabled=True,
    )

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

    sandbox = LocalSandbox("local")
    # LEARN: The lead agent receives prepared runtime state plus uploaded file metadata.
    # That is the key idea of DeerFlow's backend: orchestration prepares the stage first,
    # then tool execution happens inside a controlled sandbox.
    outcome = agent.run(
        prompt="Summarize the uploaded research and prepare a safe next step.",
        runtime=thread_runtime,
        uploaded_files=uploads["files"],
        sandbox=sandbox,
    )

    return {
        "health": gateway.get_health(),
        "models_seen_by_gateway": models["models"],
        "thread_runtime": {
            "thread_id": thread_runtime.thread_id,
            "workspace_path": thread_runtime.workspace_path,
            "uploads_path": thread_runtime.uploads_path,
            "outputs_path": thread_runtime.outputs_path,
            "sandbox_id": thread_runtime.sandbox_id,
        },
        "uploaded_files": uploads["files"],
        "lead_agent": outcome,
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
