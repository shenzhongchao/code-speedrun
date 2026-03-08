"""
nanobot 会话管理 — 对话历史持久化

// LEARN: 会话管理就像一个"聊天记录本"。
// 每个对话（由 session_key 标识）都有自己的记录本，
// 以 JSONL 格式（每行一条 JSON）存储在磁盘上。
// 这样即使程序重启，之前的对话也不会丢失。
//
// 关键设计：消息列表是"只追加"的（append-only）。
// 记忆整合不会删除旧消息，而是通过 last_consolidated 指针
// 标记哪些消息已经被总结过了。这样做是为了 LLM 缓存效率——
// 如果修改了消息列表，缓存就失效了。
"""

import json
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def safe_filename(name: str) -> str:
    """将字符串转为安全的文件名。"""
    return "".join(c if c.isalnum() or c in "-_" else "_" for c in name)


@dataclass
class Session:
    """
    一个对话会话。

    // LEARN: Session 的核心是 messages 列表和 last_consolidated 指针。
    // messages 存储所有消息（只追加），last_consolidated 标记整合进度。
    // get_history() 只返回未整合的消息，这就是 Agent 看到的"近期记忆"。
    """

    key: str  # channel:chat_id
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)
    last_consolidated: int = 0  # 已整合的消息数量

    def add_message(self, role: str, content: str, **kwargs: Any) -> None:
        """追加一条消息。"""
        msg = {
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **kwargs,
        }
        self.messages.append(msg)
        self.updated_at = datetime.now()

    # LEARN: get_history 的"对齐到 user 轮次"逻辑很重要。
    # LLM 要求消息列表必须以 user 消息开头（不能以 tool 结果开头）。
    # 所以这里会跳过开头的非 user 消息，避免"孤儿"工具结果。
    def get_history(self, max_messages: int = 500) -> list[dict[str, Any]]:
        """返回未整合的消息（对齐到 user 轮次）。"""
        unconsolidated = self.messages[self.last_consolidated:]
        sliced = unconsolidated[-max_messages:]

        # 跳过开头的非 user 消息
        for i, m in enumerate(sliced):
            if m.get("role") == "user":
                sliced = sliced[i:]
                break

        out: list[dict[str, Any]] = []
        for m in sliced:
            entry: dict[str, Any] = {"role": m["role"], "content": m.get("content", "")}
            for k in ("tool_calls", "tool_call_id", "name"):
                if k in m:
                    entry[k] = m[k]
            out.append(entry)
        return out

    def clear(self) -> None:
        """清空会话。"""
        self.messages = []
        self.last_consolidated = 0
        self.updated_at = datetime.now()


class SessionManager:
    """
    会话管理器：JSONL 文件持久化。

    // LEARN: JSONL（JSON Lines）格式的好处：
    // 1. 每行独立，追加写入不需要读取整个文件
    // 2. 即使某行损坏，其他行不受影响
    // 3. 可以用 head/tail/grep 等命令行工具直接查看
    """

    def __init__(self, workspace: Path):
        self.sessions_dir = ensure_dir(workspace / "sessions")
        self._cache: dict[str, Session] = {}

    def _get_session_path(self, key: str) -> Path:
        safe_key = safe_filename(key.replace(":", "_"))
        return self.sessions_dir / f"{safe_key}.jsonl"

    def get_or_create(self, key: str) -> Session:
        """获取或创建会话。"""
        if key in self._cache:
            return self._cache[key]
        session = self._load(key) or Session(key=key)
        self._cache[key] = session
        return session

    def _load(self, key: str) -> Session | None:
        """从磁盘加载会话。"""
        path = self._get_session_path(key)
        if not path.exists():
            return None

        try:
            messages = []
            metadata = {}
            created_at = None
            last_consolidated = 0

            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    data = json.loads(line)
                    if data.get("_type") == "metadata":
                        metadata = data.get("metadata", {})
                        created_at = (
                            datetime.fromisoformat(data["created_at"])
                            if data.get("created_at")
                            else None
                        )
                        last_consolidated = data.get("last_consolidated", 0)
                    else:
                        messages.append(data)

            return Session(
                key=key,
                messages=messages,
                created_at=created_at or datetime.now(),
                metadata=metadata,
                last_consolidated=last_consolidated,
            )
        except Exception:
            return None

    def save(self, session: Session) -> None:
        """保存会话到磁盘。"""
        path = self._get_session_path(session.key)
        with open(path, "w", encoding="utf-8") as f:
            metadata_line = {
                "_type": "metadata",
                "key": session.key,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "metadata": session.metadata,
                "last_consolidated": session.last_consolidated,
            }
            f.write(json.dumps(metadata_line, ensure_ascii=False) + "\n")
            for msg in session.messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")
        self._cache[session.key] = session

    def invalidate(self, key: str) -> None:
        """从缓存中移除会话。"""
        self._cache.pop(key, None)
