from __future__ import annotations

import json
import re
from copy import copy
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any


CURRENT_DIR = Path(__file__).resolve().parent
DEFAULT_MEMORY_PATH = CURRENT_DIR / "_demo_data" / "memory.json"
UPLOAD_BLOCK_RE = re.compile(r"<uploaded_files>[\s\S]*?</uploaded_files>\n*", re.IGNORECASE)
UPLOAD_PATH_RE = re.compile(r"/mnt/user-data/uploads/[^\s<]+")


@dataclass
class DemoMessage:
    type: str
    content: str
    tool_calls: list[dict[str, Any]] = field(default_factory=list)


def filter_messages_for_memory(messages: list[DemoMessage]) -> list[DemoMessage]:
    filtered: list[DemoMessage] = []
    skip_next_ai = False
    for message in messages:
        if message.type == "human":
            cleaned = UPLOAD_BLOCK_RE.sub("", message.content).strip()
            if cleaned != message.content:
                # LEARN: Uploaded file paths are session-scoped. Memory should
                # remember user preferences, not /mnt/user-data/uploads handles.
                if not cleaned:
                    skip_next_ai = True
                    continue
                clean_message = copy(message)
                clean_message.content = cleaned
                filtered.append(clean_message)
                skip_next_ai = False
            else:
                filtered.append(message)
                skip_next_ai = False
        elif message.type == "ai":
            # LEARN: AI messages with tool calls and ToolMessage results are
            # process noise. Long-term memory keeps the user/final-answer lesson.
            if message.tool_calls:
                continue
            if skip_next_ai:
                skip_next_ai = False
                continue
            filtered.append(message)
    return filtered


def create_empty_memory() -> dict[str, Any]:
    return {
        "version": "1.0",
        "lastUpdated": "",
        "user": {
            "workContext": {"summary": "", "updatedAt": ""},
            "personalContext": {"summary": "", "updatedAt": ""},
            "topOfMind": {"summary": "", "updatedAt": ""},
        },
        "history": {
            "recentMonths": {"summary": "", "updatedAt": ""},
            "earlierContext": {"summary": "", "updatedAt": ""},
            "longTermBackground": {"summary": "", "updatedAt": ""},
        },
        "facts": [],
    }


def load_memory(memory_path: Path) -> dict[str, Any]:
    if not memory_path.exists():
        return create_empty_memory()
    return json.loads(memory_path.read_text(encoding="utf-8"))


def format_conversation_for_update(messages: list[DemoMessage]) -> str:
    lines: list[str] = []
    for message in messages:
        if message.type == "human":
            lines.append(f"User: {message.content}")
        elif message.type == "ai":
            lines.append(f"Assistant: {message.content}")
    return "\n\n".join(lines)


def scripted_llm_structured_update(memory: dict[str, Any], messages: list[DemoMessage]) -> dict[str, Any]:
    human_text = " ".join(message.content for message in messages if message.type == "human")
    cleaned = UPLOAD_PATH_RE.sub("", human_text).strip()

    # LEARN: In real DeerFlow, the LLM sees the current memory JSON plus the
    # filtered conversation, then returns a structured update payload. It is not
    # allowed to rewrite memory.json directly. The merge step below is separate,
    # which keeps validation, timestamps, fact IDs, and max-fact limits in code.
    def empty_section() -> dict[str, object]:
        return {"summary": "", "shouldUpdate": False}

    if not cleaned:
        return {
            "user": {
                "workContext": empty_section(),
                "personalContext": empty_section(),
                "topOfMind": empty_section(),
            },
            "history": {
                "recentMonths": empty_section(),
                "earlierContext": empty_section(),
                "longTermBackground": empty_section(),
            },
            "newFacts": [],
            "factsToRemove": [],
        }

    existing_summary = memory["user"]["personalContext"]["summary"]
    summary = "Prefers concise research summaries and source-backed bullet points."
    if existing_summary:
        summary = f"{existing_summary} {summary}"

    return {
        "user": {
            "workContext": {"summary": "", "shouldUpdate": False},
            "personalContext": {"summary": summary, "shouldUpdate": True},
            "topOfMind": {"summary": "", "shouldUpdate": False},
        },
        "history": {
            "recentMonths": {"summary": "", "shouldUpdate": False},
            "earlierContext": {"summary": "", "shouldUpdate": False},
            "longTermBackground": {"summary": "", "shouldUpdate": False},
        },
        "newFacts": [
            {
                "content": "User prefers concise research summaries.",
                "category": "preference",
                "confidence": 0.95,
            },
            {
                "content": "User prefers source-backed bullet points.",
                "category": "preference",
                "confidence": 0.9,
            },
        ],
        "factsToRemove": [],
    }


def apply_structured_update(
    memory: dict[str, Any],
    structured_update: dict[str, Any],
    *,
    thread_id: str,
) -> dict[str, Any]:
    updated_at = datetime.utcnow().isoformat() + "Z"

    for section_group, section_names in {
        "user": ("workContext", "personalContext", "topOfMind"),
        "history": ("recentMonths", "earlierContext", "longTermBackground"),
    }.items():
        for section_name in section_names:
            section_update = structured_update.get(section_group, {}).get(section_name, {})
            if section_update.get("shouldUpdate") and section_update.get("summary"):
                memory[section_group][section_name] = {
                    "summary": section_update["summary"],
                    "updatedAt": updated_at,
                }

    facts_to_remove = set(structured_update.get("factsToRemove", []))
    if facts_to_remove:
        memory["facts"] = [fact for fact in memory.get("facts", []) if fact.get("id") not in facts_to_remove]

    existing_fact_content = {fact.get("content") for fact in memory.get("facts", [])}
    for fact in structured_update.get("newFacts", []):
        content = fact.get("content", "").strip()
        confidence = fact.get("confidence", 0.0)
        if not content or content in existing_fact_content or confidence < 0.7:
            continue
        memory["facts"].append(
            {
                "id": f"fact_{len(memory['facts']) + 1:04d}",
                "content": content,
                "category": fact.get("category", "context"),
                "confidence": confidence,
                "createdAt": updated_at,
                "source": thread_id,
            }
        )
        existing_fact_content.add(content)

    memory["lastUpdated"] = updated_at
    return scrub_upload_mentions(memory)


def scrub_upload_mentions(memory: dict[str, Any]) -> dict[str, Any]:
    serialized = json.dumps(memory)
    if "/mnt/user-data/uploads/" not in serialized:
        return memory
    for section_name in ("user", "history"):
        for value in memory.get(section_name, {}).values():
            if isinstance(value, dict) and "summary" in value:
                value["summary"] = UPLOAD_PATH_RE.sub("", value["summary"]).strip()
    memory["facts"] = [
        fact
        for fact in memory.get("facts", [])
        if "/mnt/user-data/uploads/" not in json.dumps(fact)
    ]
    return memory


def save_memory_atomic(memory: dict[str, Any], memory_path: Path) -> None:
    memory_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = memory_path.with_suffix(".tmp")
    temp_path.write_text(json.dumps(memory, indent=2), encoding="utf-8")
    temp_path.replace(memory_path)


def build_memory_context(*, memory_path: Path | None = None) -> str:
    memory_path = memory_path or DEFAULT_MEMORY_PATH
    # LEARN: Memory is cross-request state, so the prompt builder reloads the
    # memory file instead of trusting stale data from a previous run.
    memory = load_memory(memory_path)
    formatted = []
    personal = memory["user"]["personalContext"]["summary"]
    if personal:
        formatted.append(f"- Personal: {personal}")
    facts = [fact for fact in memory.get("facts", []) if fact.get("content")]
    for fact in sorted(facts, key=lambda item: item.get("confidence", 0), reverse=True):
        formatted.append(f"- [{fact.get('category', 'context')} | {fact.get('confidence', 0):.2f}] {fact['content']}")
    if not formatted:
        return ""
    return "\n".join(["<memory>", *formatted, "</memory>"])


def build_demo_messages() -> list[DemoMessage]:
    return [
        DemoMessage("human", "I prefer concise research summaries."),
        DemoMessage("ai", "", tool_calls=[{"name": "bash", "args": {"command": "ls"}}]),
        DemoMessage("tool", "workspace listing"),
        DemoMessage("ai", "I will keep research summaries concise."),
        DemoMessage(
            "human",
            "<uploaded_files>\n- /mnt/user-data/uploads/brief.pdf\n</uploaded_files>",
        ),
        DemoMessage("ai", "I see the upload."),
        DemoMessage(
            "human",
            "<uploaded_files>\n- /mnt/user-data/uploads/source.docx\n</uploaded_files>\nUse source-backed bullets next time.",
        ),
        DemoMessage("ai", "Noted."),
    ]


def run_memory_lifecycle(*, memory_path: Path | None = None) -> dict[str, object]:
    memory_path = memory_path or DEFAULT_MEMORY_PATH
    memory = load_memory(memory_path)
    messages = build_demo_messages()
    filtered = filter_messages_for_memory(messages)
    conversation_for_llm = format_conversation_for_update(filtered)
    structured_update = scripted_llm_structured_update(memory, filtered)
    updated = apply_structured_update(memory, structured_update, thread_id="demo-thread")
    save_memory_atomic(updated, memory_path)
    return {
        "filtered_messages": [asdict(message) for message in filtered],
        "conversation_for_llm": conversation_for_llm,
        "structured_update": structured_update,
        "memory_path": str(memory_path),
        "memory_context": build_memory_context(memory_path=memory_path),
    }


def run_demo() -> dict[str, object]:
    runtime_path = CURRENT_DIR / "_demo_data" / "_runtime" / "memory.json"
    if runtime_path.exists():
        runtime_path.unlink()
    return run_memory_lifecycle(memory_path=runtime_path)
