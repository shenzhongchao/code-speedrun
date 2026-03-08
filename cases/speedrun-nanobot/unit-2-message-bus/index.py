"""Unit 2 demo: message routing and session persistence."""

from __future__ import annotations

import asyncio

from runtime_bus import InboundMessage, MessageBus, OutboundMessage, SessionStore


async def demo() -> None:
    bus = MessageBus()
    sessions = SessionStore()

    incoming = InboundMessage(
        channel="telegram",
        sender_id="user-001",
        chat_id="chat-42",
        content="帮我记录今天要写周报",
    )
    await bus.publish_inbound(incoming)

    received = await bus.consume_inbound()
    session = sessions.get_or_create(received.session_key)

    # LEARN: 像客服系统给每个客户开工单。
    # 这里把消息写入会话，后续单元会基于这段历史构建提示词（-> Unit 3）。
    session.append("user", received.content)

    reply = OutboundMessage(
        channel=received.channel,
        chat_id=received.chat_id,
        content="已记录：今天写周报。",
    )
    await bus.publish_outbound(reply)
    sent = await bus.consume_outbound()

    print("[Unit2] session_key:", received.session_key)
    print("[Unit2] history size:", len(session.history()))
    print("[Unit2] outbound:", sent.content)


if __name__ == "__main__":
    asyncio.run(demo())
