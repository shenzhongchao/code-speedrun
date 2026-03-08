"""
Unit 2 演示：消息总线的工作流程

模拟一个聊天渠道发送消息，Agent 接收并回复的完整过程。
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from events import InboundMessage, OutboundMessage
from bus import MessageBus


async def simulate_channel(bus: MessageBus):
    """模拟聊天渠道：发送用户消息，接收 Agent 回复。"""
    # 用户发了一条消息
    user_msg = InboundMessage(
        channel="telegram",
        sender_id="user_001",
        chat_id="chat_42",
        content="你好，今天天气怎么样？",
    )
    print(f"[渠道] 用户发送: {user_msg.content}")
    print(f"[渠道] 会话键: {user_msg.session_key}")
    await bus.publish_inbound(user_msg)

    # 等待 Agent 回复
    reply = await bus.consume_outbound()
    print(f"[渠道] 收到回复: {reply.content}")
    print(f"[渠道] 回复目标: {reply.channel}:{reply.chat_id}")


async def simulate_agent(bus: MessageBus):
    """模拟 Agent 核心：接收消息，生成回复。"""
    msg = await bus.consume_inbound()
    print(f"\n[Agent] 收到消息: {msg.content}")
    print(f"[Agent] 来自: {msg.channel}, 发送者: {msg.sender_id}")

    # 生成回复
    reply = OutboundMessage(
        channel=msg.channel,
        chat_id=msg.chat_id,
        content="今天晴天，适合出门散步！🌞",
    )
    await bus.publish_outbound(reply)
    print(f"[Agent] 已回复: {reply.content}\n")


async def main():
    print("=" * 50)
    print("Unit 2: 消息总线演示")
    print("=" * 50)

    bus = MessageBus()
    print(f"\n初始状态: 入站队列={bus.inbound_size}, 出站队列={bus.outbound_size}")

    # 并发运行渠道和 Agent
    # LEARN: asyncio.gather 让两个协程"同时"运行。
    # 渠道发消息 → 消息进入 inbound 队列 → Agent 从队列取出 → 处理 → 回复进入 outbound → 渠道取出回复
    await asyncio.gather(
        simulate_channel(bus),
        simulate_agent(bus),
    )

    print(f"结束状态: 入站队列={bus.inbound_size}, 出站队列={bus.outbound_size}")

    # 演示多条消息
    print("\n--- 批量消息演示 ---")
    messages = ["帮我查一下航班", "明天提醒我开会", "写一首诗"]
    for text in messages:
        await bus.publish_inbound(InboundMessage(
            channel="cli", sender_id="user", chat_id="direct", content=text,
        ))
    print(f"入站队列积压: {bus.inbound_size} 条消息")

    while bus.inbound_size > 0:
        msg = await bus.consume_inbound()
        print(f"  处理: {msg.content}")
    print(f"处理完毕，队列剩余: {bus.inbound_size}")


if __name__ == "__main__":
    asyncio.run(main())
