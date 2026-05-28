from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


SPEEDRUN_ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, relative_path: str):
    path = SPEEDRUN_ROOT / relative_path
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_unit3_virtual_path_mapper_maps_only_user_data(tmp_path):
    unit3 = load_module("unit3_thread_runtime_demo", "unit-3-thread-runtime/thread_runtime_demo.py")
    user_data = tmp_path / "threads" / "thread-1" / "user-data"
    mapper = unit3.VirtualPathMapper(user_data)

    assert mapper.virtual_to_host("/mnt/user-data/outputs/result.md") == user_data / "outputs" / "result.md"
    assert mapper.host_to_virtual(user_data / "uploads" / "brief.txt") == "/mnt/user-data/uploads/brief.txt"

    with pytest.raises(ValueError):
        mapper.virtual_to_host("/etc/passwd")
    with pytest.raises(ValueError):
        mapper.virtual_to_host("/mnt/user-data/../secret.txt")
    with pytest.raises(ValueError):
        mapper.host_to_virtual(tmp_path / "outside.txt")


def test_unit2_uploads_use_the_same_virtual_path_contract(tmp_path):
    unit2 = load_module("unit2_gateway_config_demo", "unit-2-gateway-config/gateway_config_demo.py")
    gateway = unit2.GatewayAPI(config=unit2.build_demo_config(), storage_root=tmp_path)

    result = gateway.upload_files(
        thread_id="thread-upload",
        files=[unit2.UploadedFile(filename="../brief.docx", content="hello from upload")],
    )

    uploaded = result["files"][0]
    expected_host = tmp_path / "threads" / "thread-upload" / "user-data" / "uploads" / "brief.docx"
    assert uploaded["path"] == str(expected_host)
    assert uploaded["virtual_path"] == "/mnt/user-data/uploads/brief.docx"
    assert uploaded["artifact_url"] == "/api/threads/thread-upload/artifacts/mnt/user-data/uploads/brief.docx"
    assert uploaded["markdown_virtual_path"] == "/mnt/user-data/uploads/brief.md"


def test_unit5_docker_sandbox_mounts_user_data_and_resolves_virtual_paths(tmp_path):
    unit5 = load_module("unit5_tools_sandbox_demo", "unit-5-tools-sandbox/tools_sandbox_demo.py")
    calls: list[list[str]] = []

    def fake_runner(command, **kwargs):
        calls.append(command)
        return unit5.CompletedSandboxProcess(stdout="OK\n", stderr="", returncode=0)

    user_data = tmp_path / "thread-1" / "user-data"
    sandbox = unit5.DockerSandbox(
        sandbox_id="docker-thread-1",
        user_data_root=user_data,
        image="python:3.12-slim",
        runner=fake_runner,
    )

    sandbox.write_file("/mnt/user-data/uploads/input.txt", "upload content")
    assert (user_data / "uploads" / "input.txt").read_text(encoding="utf-8") == "upload content"
    assert sandbox.read_file("/mnt/user-data/uploads/input.txt") == "upload content"

    assert sandbox.execute_command("cat /mnt/user-data/uploads/input.txt") == "OK"
    assert calls[0] == [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{user_data}:/mnt/user-data",
        "-w",
        "/mnt/user-data/workspace",
        "python:3.12-slim",
        "/bin/sh",
        "-lc",
        "cat /mnt/user-data/uploads/input.txt",
    ]

    with pytest.raises(ValueError):
        sandbox.read_file("/workspace/input.txt")


def test_unit5_langgraph_tools_keep_virtual_paths_in_trace(tmp_path):
    unit5 = load_module("unit5_tools_sandbox_demo_for_graph", "unit-5-tools-sandbox/tools_sandbox_demo.py")
    user_data = tmp_path / "thread-graph" / "user-data"
    sandbox = unit5.DockerSandbox(
        sandbox_id="fake-docker",
        user_data_root=user_data,
        runner=lambda command, **kwargs: unit5.CompletedSandboxProcess(stdout="from docker\n", stderr="", returncode=0),
    )
    model = unit5.ScriptedToolCallingModel(
        tool_name="write_file",
        tool_args={
            "path": "/mnt/user-data/outputs/result.txt",
            "content": "virtual output",
        },
        final_text="wrote virtual output",
    )

    result = unit5.run_langgraph_sandbox_demo(
        prompt="Write the result to the virtual outputs directory.",
        sandbox=sandbox,
        model=model,
    )

    assert result["tool_trace"][0]["args"]["path"] == "/mnt/user-data/outputs/result.txt"
    assert (user_data / "outputs" / "result.txt").read_text(encoding="utf-8") == "virtual output"


def test_unit1_shows_upload_runtime_and_sandbox_share_virtual_paths():
    unit1 = load_module("unit1_overall_backend_flow", "unit-1-overall-backend-flow/main.py")

    result = unit1.run_demo()

    assert result["thread_runtime"]["virtual_workspace_path"] == "/mnt/user-data/workspace"
    assert result["uploaded_files"][0]["virtual_path"].startswith("/mnt/user-data/uploads/")
    assert result["virtual_path_flow"]["output_virtual_path"] == "/mnt/user-data/outputs/langgraph-result.txt"
    assert result["virtual_path_flow"]["host_output_exists"] is True
