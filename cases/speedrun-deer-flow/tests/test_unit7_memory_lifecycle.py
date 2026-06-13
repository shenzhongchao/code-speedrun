from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


SPEEDRUN_ROOT = Path(__file__).resolve().parents[1]


def load_unit7():
    path = SPEEDRUN_ROOT / "unit-7-memory-lifecycle" / "memory_lifecycle_demo.py"
    spec = importlib.util.spec_from_file_location("unit7_memory_lifecycle_demo", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_tool_call_ai_message_is_not_memory_input(tmp_path):
    unit7 = load_unit7()
    messages = [
        unit7.DemoMessage("human", "Remember that I prefer concise reports."),
        unit7.DemoMessage("ai", "", tool_calls=[{"name": "bash"}]),
        unit7.DemoMessage("tool", "intermediate shell output"),
        unit7.DemoMessage("ai", "I will keep reports concise."),
    ]

    filtered = unit7.filter_messages_for_memory(messages)

    assert [message.type for message in filtered] == ["human", "ai"]
    assert all(not message.tool_calls for message in filtered)


def test_upload_only_turn_is_dropped():
    unit7 = load_unit7()
    messages = [
        unit7.DemoMessage(
            "human",
            "<uploaded_files>\n- /mnt/user-data/uploads/brief.pdf\n</uploaded_files>",
        ),
        unit7.DemoMessage("ai", "I see the upload."),
        unit7.DemoMessage("human", "Use bullet summaries for research updates."),
        unit7.DemoMessage("ai", "Noted."),
    ]

    filtered = unit7.filter_messages_for_memory(messages)

    assert [message.content for message in filtered] == [
        "Use bullet summaries for research updates.",
        "Noted.",
    ]


def test_upload_paths_do_not_enter_saved_memory(tmp_path):
    unit7 = load_unit7()
    memory_path = tmp_path / "memory.json"

    result = unit7.run_memory_lifecycle(memory_path=memory_path)

    saved = json.loads(memory_path.read_text(encoding="utf-8"))
    assert "/mnt/user-data/uploads/" not in json.dumps(saved)
    assert "/mnt/user-data/uploads/" not in result["memory_context"]


def test_memory_update_uses_realistic_llm_structured_payload(tmp_path):
    unit7 = load_unit7()
    memory_path = tmp_path / "memory.json"

    result = unit7.run_memory_lifecycle(memory_path=memory_path)
    saved = json.loads(memory_path.read_text(encoding="utf-8"))

    structured_update = result["structured_update"]
    assert "patch" not in result
    assert structured_update["user"]["personalContext"]["shouldUpdate"] is True
    assert structured_update["newFacts"][0]["category"] == "preference"
    assert structured_update["factsToRemove"] == []

    assert saved["user"]["personalContext"]["summary"]
    assert saved["user"]["personalContext"]["updatedAt"]
    assert saved["facts"]
    assert {"content", "category", "confidence", "createdAt", "source"} <= set(saved["facts"][0])
    assert saved["facts"][0]["source"] == "demo-thread"
