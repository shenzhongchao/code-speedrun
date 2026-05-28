from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


UNIT5_PATH = Path(__file__).resolve().parents[1] / "unit-5-tools-sandbox" / "tools_sandbox_demo.py"


def load_unit5():
    spec = importlib.util.spec_from_file_location("unit5_tools_sandbox_demo", UNIT5_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_docker_sandbox_executes_commands_through_docker_run(tmp_path):
    unit5 = load_unit5()
    calls: list[list[str]] = []

    def fake_runner(command, **kwargs):
        calls.append(command)
        return unit5.CompletedSandboxProcess(stdout="WORK_DONE\n", stderr="", returncode=0)

    sandbox = unit5.DockerSandbox(
        sandbox_id="teaching",
        user_data_root=tmp_path,
        image="python:3.12-slim",
        runner=fake_runner,
    )

    output = sandbox.execute_command("python - <<'PY'\nprint('WORK_DONE')\nPY")

    assert output == "WORK_DONE"
    assert calls == [
        [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{tmp_path}:/mnt/user-data",
            "-w",
            "/mnt/user-data/workspace",
            "python:3.12-slim",
            "/bin/sh",
            "-lc",
            "python - <<'PY'\nprint('WORK_DONE')\nPY",
        ]
    ]


def test_langgraph_agent_routes_model_tool_call_to_sandbox(tmp_path):
    unit5 = load_unit5()
    sandbox = unit5.DockerSandbox(
        sandbox_id="fake-docker",
        user_data_root=tmp_path,
        runner=lambda command, **kwargs: unit5.CompletedSandboxProcess(
            stdout="agent wrote summary\n",
            stderr="",
            returncode=0,
        ),
    )

    model = unit5.ScriptedToolCallingModel(
        tool_name="bash",
        tool_args={"command": "printf 'agent wrote summary\\n' > /mnt/user-data/outputs/result.txt && cat /mnt/user-data/outputs/result.txt"},
        final_text="The sandbox task finished.",
    )

    result = unit5.run_langgraph_sandbox_demo(
        prompt="Write a summary inside the sandbox.",
        sandbox=sandbox,
        model=model,
    )

    assert result["final_message"] == "The sandbox task finished."
    assert result["tool_trace"] == [
        {
            "tool": "bash",
            "args": {"command": "printf 'agent wrote summary\\n' > /mnt/user-data/outputs/result.txt && cat /mnt/user-data/outputs/result.txt"},
            "output": "agent wrote summary",
        }
    ]
    assert result["messages"][-2]["type"] == "tool"
    assert result["messages"][-2]["content"] == "agent wrote summary"


def test_openai_compatible_config_builds_chat_openai_kwargs():
    unit5 = load_unit5()

    config = unit5.OpenAICompatibleConfig(
        model="gpt-4o-mini",
        base_url="https://llm.example/v1",
        api_key="test-key",
        temperature=0,
    )

    assert config.to_chat_openai_kwargs() == {
        "model": "gpt-4o-mini",
        "base_url": "https://llm.example/v1",
        "api_key": "test-key",
        "temperature": 0,
    }
