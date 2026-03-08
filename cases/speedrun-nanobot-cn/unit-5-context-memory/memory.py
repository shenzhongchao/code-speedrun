"""
nanobot 上下文与记忆 — 双层记忆系统

// LEARN: 记忆系统就像人的大脑有"长期记忆"和"日记本"。
// MEMORY.md 是长期记忆——存储重要事实（用户偏好、项目信息等），
// 每次对话都会被加载到系统提示词中。
// HISTORY.md 是日记本——按时间记录发生了什么，可以用 grep 搜索。
// 当对话太长时，"记忆整合"过程会让 LLM 把旧消息总结成这两个文件。
"""

from pathlib import Path


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


class MemoryStore:
    """
    双层记忆：MEMORY.md（长期事实）+ HISTORY.md（可搜索日志）。
    """

    def __init__(self, workspace: Path):
        self.memory_dir = ensure_dir(workspace / "memory")
        self.memory_file = self.memory_dir / "MEMORY.md"
        self.history_file = self.memory_dir / "HISTORY.md"

    def read_long_term(self) -> str:
        """读取长期记忆。"""
        if self.memory_file.exists():
            return self.memory_file.read_text(encoding="utf-8")
        return ""

    def write_long_term(self, content: str) -> None:
        """写入长期记忆（覆盖）。"""
        self.memory_file.write_text(content, encoding="utf-8")

    def append_history(self, entry: str) -> None:
        """追加历史日志条目。"""
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(entry.rstrip() + "\n\n")

    def get_memory_context(self) -> str:
        """获取用于系统提示词的记忆内容。"""
        long_term = self.read_long_term()
        return f"## Long-term Memory\n{long_term}" if long_term else ""

    # LEARN: 记忆整合是 nanobot 最精妙的设计之一。
    # 当对话消息超过 memory_window（默认 100 条）时，
    # 旧消息会被发给 LLM，让它总结成：
    # 1. history_entry: 一段摘要，追加到 HISTORY.md
    # 2. memory_update: 更新后的长期记忆，覆盖 MEMORY.md
    # 这样 Agent 既不会"失忆"，又不会因为上下文太长而变慢。
    #
    # 真实实现中，整合通过一个虚拟工具调用（save_memory）完成，
    # 这里简化为直接写入文件。
    def consolidate_simple(
        self,
        old_messages: list[dict],
        history_entry: str,
        memory_update: str | None = None,
    ) -> None:
        """简化版记忆整合（真实版本通过 LLM 工具调用完成）。"""
        if history_entry:
            self.append_history(history_entry)
        if memory_update is not None:
            current = self.read_long_term()
            if memory_update != current:
                self.write_long_term(memory_update)
