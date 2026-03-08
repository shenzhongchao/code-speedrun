"""
nanobot 消息总线 — 事件定义

// LEARN: 消息总线就像邮局的分拣系统。
// InboundMessage 是"收到的信件"（从聊天平台进来的消息），
// OutboundMessage 是"要寄出的信件"（Agent 回复给用户的消息）。
// 两者通过 dataclass 定义，确保每条消息都携带完整的路由信息。
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class InboundMessage:
    """从聊天渠道收到的消息。"""

    channel: str          # 来源渠道: "telegram", "discord", "cli" 等
    sender_id: str        # 发送者标识
    chat_id: str          # 会话标识
    content: str          # 消息文本
    timestamp: datetime = field(default_factory=datetime.now)
    media: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # LEARN: session_key 是消息路由的"地址"。
    # 格式为 "channel:chat_id"，用于将消息分配到正确的会话。
    # 比如 "telegram:12345" 表示 Telegram 上 ID 为 12345 的聊天。
    @property
    def session_key(self) -> str:
        return f"{self.channel}:{self.chat_id}"


@dataclass
class OutboundMessage:
    """要发送到聊天渠道的消息。"""

    channel: str
    chat_id: str
    content: str
    reply_to: str | None = None
    media: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
