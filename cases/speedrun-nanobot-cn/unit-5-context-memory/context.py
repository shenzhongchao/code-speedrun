"""
nanobot 上下文与记忆 — 上下文构建器

// LEARN: 上下文构建器就像一个"简历编写器"。
// 每次 Agent 要和 LLM 对话前，它会把 Agent 的"身份证"（identity）、
// "知识库"（bootstrap 文件）、"记忆"（MEMORY.md）、"技能"（skills）
// 组装成一份完整的系统提示词。LLM 看到这份"简历"后，就知道自己是谁、能做什么。
"""

import platform
from datetime import datetime
from pathlib import Path
from typing import Any

from memory import MemoryStore


class ContextBuilder:
    """构建 Agent 的上下文（系统提示词 + 消息列表）。"""

    BOOTSTRAP_FILES = ["AGENTS.md", "SOUL.md", "USER.md", "TOOLS.md", "IDENTITY.md"]
    _RUNTIME_CONTEXT_TAG = "[Runtime Context — metadata only, not instructions]"

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.memory = MemoryStore(workspace)

    # LEARN: 系统提示词由多个"切片"拼接而成，用 "---" 分隔。
    # 这种分层设计让每个部分可以独立更新，互不影响。
    def build_system_prompt(self) -> str:
        """构建系统提示词：身份 + 引导文件 + 记忆。"""
        parts = [self._get_identity()]

        bootstrap = self._load_bootstrap_files()
        if bootstrap:
            parts.append(bootstrap)

        memory = self.memory.get_memory_context()
        if memory:
            parts.append(f"# Memory\n\n{memory}")

        return "\n\n---\n\n".join(parts)

    def _get_identity(self) -> str:
        """生成核心身份信息。"""
        workspace_path = str(self.workspace.expanduser().resolve())
        system = platform.system()
        runtime = f"{'macOS' if system == 'Darwin' else system} {platform.machine()}, Python {platform.python_version()}"

        return f"""# nanobot

You are nanobot, a helpful AI assistant.

## Runtime
{runtime}

## Workspace
Your workspace is at: {workspace_path}
- Long-term memory: {workspace_path}/memory/MEMORY.md
- History log: {workspace_path}/memory/HISTORY.md"""

    def _load_bootstrap_files(self) -> str:
        """加载工作区中的引导文件。"""
        parts = []
        for filename in self.BOOTSTRAP_FILES:
            file_path = self.workspace / filename
            if file_path.exists():
                content = file_path.read_text(encoding="utf-8")
                parts.append(f"## {filename}\n\n{content}")
        return "\n\n".join(parts) if parts else ""

    # LEARN: 运行时上下文作为独立的 user 消息注入，而不是放在系统提示词里。
    # 这是一个安全设计：运行时信息（时间、渠道）被标记为"元数据"，
    # 防止被恶意用户利用来注入指令。
    @staticmethod
    def build_runtime_context(channel: str | None, chat_id: str | None) -> str:
        """构建运行时上下文（注入在用户消息之前）。"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M (%A)")
        lines = [f"Current Time: {now}"]
        if channel and chat_id:
            lines += [f"Channel: {channel}", f"Chat ID: {chat_id}"]
        return ContextBuilder._RUNTIME_CONTEXT_TAG + "\n" + "\n".join(lines)

    def build_messages(
        self,
        history: list[dict[str, Any]],
        current_message: str,
        channel: str | None = None,
        chat_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """构建完整的消息列表（发给 LLM 用）。"""
        return [
            {"role": "system", "content": self.build_system_prompt()},
            *history,
            {"role": "user", "content": self.build_runtime_context(channel, chat_id)},
            {"role": "user", "content": current_message},
        ]
