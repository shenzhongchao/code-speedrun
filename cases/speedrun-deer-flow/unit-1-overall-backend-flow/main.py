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
sys.path.insert(0, str(ROOT_DIR / "unit-6-skills-prompt-system"))
sys.path.insert(0, str(ROOT_DIR / "unit-7-memory-lifecycle"))
sys.path.insert(0, str(ROOT_DIR / "unit-8-subagent-delegation"))
sys.path.insert(0, str(ROOT_DIR / "unit-9-mcp-deferred-tools"))
sys.path.insert(0, str(ROOT_DIR / "unit-10-artifacts-archive-safety"))

from artifacts_archive_safety_demo import resolve_demo_artifact  # noqa: E402
from gateway_config_demo import GatewayAPI, UploadedFile, build_demo_config  # noqa: E402
from lead_agent_factory_demo import LeadAgentFactory, RuntimeFlags  # noqa: E402
from mcp_deferred_tools_demo import run_mcp_deferred_tools_demo  # noqa: E402
from memory_lifecycle_demo import build_memory_context, run_memory_lifecycle  # noqa: E402
from skills_prompt_demo import build_skills_prompt_section  # noqa: E402
from subagent_delegation_demo import run_subagent_demo  # noqa: E402
from thread_runtime_demo import ThreadRuntimeManager  # noqa: E402
from tools_sandbox_demo import (  # noqa: E402
    CompletedSandboxProcess,
    DockerSandbox,
    ScriptedToolCallingModel,
    build_tool_registry,
    run_langgraph_sandbox_demo,
)


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

    def fake_docker_runner(command: list[str], **kwargs: object) -> CompletedSandboxProcess:
        # LEARN: Unit 1 proves the virtual path contract without requiring Docker.
        # Unit 5 owns the real Docker execution path; this top-level flow only needs to show
        # that the same /mnt/user-data path can be mounted, written, and inspected.
        shell_command = command[-1]
        if shell_command == "ls -1 /mnt/user-data/workspace":
            names = sorted(path.name for path in Path(thread_runtime.workspace_path).iterdir())
            return CompletedSandboxProcess(stdout="\n".join(names) + "\n", stderr="", returncode=0)
        output_path = Path(thread_runtime.outputs_path) / "langgraph-result.txt"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text("LANGGRAPH_SANDBOX_OK\n", encoding="utf-8")
        return CompletedSandboxProcess(stdout="LANGGRAPH_SANDBOX_OK\n", stderr="", returncode=0)

    sandbox = DockerSandbox(
        "docker-thread-007",
        user_data_root=thread_runtime.user_data_path,
        runner=fake_docker_runner,
    )
    # LEARN: The lead agent receives prepared runtime state plus uploaded file metadata.
    # That is the key idea of DeerFlow's backend: orchestration prepares the stage first,
    # then tool execution happens inside a controlled sandbox.
    outcome = agent.run(
        prompt="Summarize the uploaded research and prepare a safe next step.",
        runtime=thread_runtime,
        uploaded_files=uploads["files"],
        sandbox=sandbox,
    )

    graph_outcome = run_langgraph_sandbox_demo(
        prompt="Write a final marker into /mnt/user-data/outputs/langgraph-result.txt.",
        sandbox=sandbox,
        model=ScriptedToolCallingModel(
            tool_name="bash",
            tool_args={
                "command": (
                    "printf 'LANGGRAPH_SANDBOX_OK\\n' "
                    "> /mnt/user-data/outputs/langgraph-result.txt && "
                    "cat /mnt/user-data/outputs/langgraph-result.txt"
                )
            },
            final_text="LANGGRAPH_SANDBOX_OK",
        ),
    )

    output_virtual_path = f"{thread_runtime.virtual_outputs_path}/langgraph-result.txt"
    output_host_path = thread_runtime.mapper().virtual_to_host(output_virtual_path)
    memory_path = base_dir / "memory.json"
    memory_result = run_memory_lifecycle(memory_path=memory_path)
    subagent_result = run_subagent_demo(base_dir=base_dir)
    mcp_result = run_mcp_deferred_tools_demo(config_path=base_dir / "extensions_config.json")
    artifact_result = resolve_demo_artifact(
        thread_id=thread_runtime.thread_id,
        virtual_path=output_virtual_path,
        threads_root=base_dir / "threads",
    )
    skills_prompt = build_skills_prompt_section()

    return {
        "health": gateway.get_health(),
        "models_seen_by_gateway": models["models"],
        "thread_runtime": {
            "thread_id": thread_runtime.thread_id,
            "workspace_path": thread_runtime.workspace_path,
            "uploads_path": thread_runtime.uploads_path,
            "outputs_path": thread_runtime.outputs_path,
            "user_data_path": thread_runtime.user_data_path,
            "virtual_workspace_path": thread_runtime.virtual_workspace_path,
            "virtual_uploads_path": thread_runtime.virtual_uploads_path,
            "virtual_outputs_path": thread_runtime.virtual_outputs_path,
            "sandbox_id": thread_runtime.sandbox_id,
        },
        "uploaded_files": uploads["files"],
        "lead_agent": outcome,
        "virtual_path_flow": {
            "mount": f"{thread_runtime.user_data_path}:/mnt/user-data",
            "output_virtual_path": output_virtual_path,
            "output_host_path": str(output_host_path),
            "host_output_exists": output_host_path.exists(),
            "langgraph_agent": graph_outcome,
        },
        "secondary_flows": {
            "skills_prompt": {
                "enabled_count": skills_prompt.count("/mnt/skills/"),
                "has_section": bool(skills_prompt),
            },
            "memory_context": {
                "has_section": bool(build_memory_context(memory_path=memory_path)),
                "filtered_message_count": len(memory_result["filtered_messages"]),
            },
            "subagent_events": [event["type"] for event in subagent_result["events"]],
            "mcp_deferred_tools": {
                "visible_tools": mcp_result["visible_tools"],
                "deferred_tool_count": len(mcp_result["deferred_tools"]),
                "search_results": [tool["name"] for tool in mcp_result["search_results"]],
            },
            "artifact_safety": {
                "response_kind": artifact_result["response_kind"],
                "virtual_path": artifact_result["virtual_path"],
                "host_path": artifact_result["host_path"],
            },
        },
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
