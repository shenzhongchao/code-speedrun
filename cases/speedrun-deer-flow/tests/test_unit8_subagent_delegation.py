from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


SPEEDRUN_ROOT = Path(__file__).resolve().parents[1]


def load_unit8():
    path = SPEEDRUN_ROOT / "unit-8-subagent-delegation" / "subagent_delegation_demo.py"
    spec = importlib.util.spec_from_file_location("unit8_subagent_delegation_demo", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_subagent_tools_do_not_include_task(tmp_path):
    unit8 = load_unit8()
    result = unit8.run_subagent_demo(base_dir=tmp_path)

    assert "task" not in result["subagent_tools"]
    assert "bash" in result["subagent_tools"]


def test_subagent_events_are_started_running_completed(tmp_path):
    unit8 = load_unit8()
    result = unit8.run_subagent_demo(base_dir=tmp_path)

    assert [event["type"] for event in result["events"]] == [
        "task_started",
        "task_running",
        "task_completed",
    ]


def test_terminal_task_is_cleaned_up(tmp_path):
    unit8 = load_unit8()
    executor = unit8.SubagentExecutor(
        config=unit8.build_general_purpose_config(),
        available_tools=["bash", "read_file", "task"],
        parent_context=unit8.ParentContext(
            thread_id="thread-test",
            sandbox_id="sandbox-test",
            workspace_path=str(tmp_path / "workspace"),
            uploads_path=str(tmp_path / "uploads"),
            outputs_path=str(tmp_path / "outputs"),
            parent_model="gpt-5-responses",
            trace_id="trace-test",
        ),
    )

    task_id = executor.execute("Summarize the workspace")
    assert task_id in executor.background_tasks

    executor.cleanup_terminal_tasks()

    assert task_id not in executor.background_tasks


def test_demo_shows_parent_task_call_runtime_snapshot_and_synthesis(tmp_path):
    unit8 = load_unit8()
    result = unit8.run_subagent_demo(base_dir=tmp_path)

    task_call = result["parent_decision"]["task_calls"][0]
    assert task_call["description"] == "inspect workspace"
    assert task_call["subagent_type"] == "general-purpose"
    assert "Return concise findings" in task_call["prompt"]

    runtime_snapshot = result["runtime_snapshot"]
    assert runtime_snapshot["thread_id"] == "thread-subagent"
    assert runtime_snapshot["sandbox_id"] == "sandbox-thread-subagent"
    assert runtime_snapshot["parent_model"] == "gpt-5-responses"
    assert runtime_snapshot["subagent_type"] == "general-purpose"

    initial_state = result["subagent_initial_state"]
    assert initial_state["messages"] == [{"role": "human", "content": task_call["prompt"]}]
    assert initial_state["thread_data"]["workspace_path"] == "/mnt/user-data/workspace"
    assert "parent conversation" not in str(initial_state).lower()

    assert result["tool_result_for_parent"].startswith("Task Succeeded. Result:")
    assert "Parent answer:" in result["parent_final_answer"]
    assert result["parent_final_answer"].count("workspace") >= 1


def test_workspace_inspection_ignores_hidden_scaffold_files(tmp_path):
    unit8 = load_unit8()
    parent_context = unit8.build_parent_context(tmp_path)
    (Path(parent_context.workspace_path) / ".gitkeep").write_text("", encoding="utf-8")
    executor = unit8.SubagentExecutor(
        config=unit8.build_general_purpose_config(),
        available_tools=["bash", "read_file", "write_file", "task"],
        parent_context=parent_context,
    )

    assert ".gitkeep" not in executor.inspect_workspace_files()
