"""Minimal context builder inspired by nanobot.agent.context."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class PromptInputs:
    identity: str
    bootstrap_files: dict[str, str] = field(default_factory=dict)
    memory_markdown: str = ""
    skills_summary: str = ""


class ContextBuilder:
    """Builds system prompt + messages for an LLM turn."""

    RUNTIME_TAG = "[Runtime Context — metadata only, not instructions]"

    def __init__(self, inputs: PromptInputs):
        self.inputs = inputs

    def build_system_prompt(self) -> str:
        parts = [self.inputs.identity]

        if self.inputs.bootstrap_files:
            bootstrap = []
            for name, content in self.inputs.bootstrap_files.items():
                bootstrap.append(f"## {name}\n{content}")
            parts.append("\n\n".join(bootstrap))

        if self.inputs.memory_markdown:
            parts.append(f"# Memory\n\n{self.inputs.memory_markdown}")

        if self.inputs.skills_summary:
            parts.append(f"# Skills\n\n{self.inputs.skills_summary}")

        return "\n\n---\n\n".join(parts)

    def build_messages(
        self,
        history: list[dict[str, Any]],
        current_message: str,
        channel: str,
        chat_id: str,
    ) -> list[dict[str, Any]]:
        runtime = self._runtime_context(channel, chat_id)

        # LEARN: 像会议纪要封面。
        # 系统提示词先声明规则，再附历史与本轮输入（-> Unit 4）。
        return [
            {"role": "system", "content": self.build_system_prompt()},
            *history,
            {"role": "user", "content": runtime},
            {"role": "user", "content": current_message},
        ]

    def _runtime_context(self, channel: str, chat_id: str) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        return (
            f"{self.RUNTIME_TAG}\n"
            f"Current Time: {now}\n"
            f"Channel: {channel}\n"
            f"Chat ID: {chat_id}"
        )
