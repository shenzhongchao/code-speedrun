"""
nanobot 消息总线 — 异步队列

// LEARN: MessageBus 就像一个双向传送带。
// 一条传送带（inbound）把用户消息送给 Agent，
// 另一条传送带（outbound）把 Agent 回复送回给用户。
// 两条传送带互不干扰，这就是"解耦"的核心思想：
// 聊天渠道不需要知道 Agent 怎么工作，Agent 也不需要知道消息来自哪个平台。
"""

import asyncio
from events import InboundMessage, OutboundMessage


class MessageBus:
    """
    异步消息总线：解耦聊天渠道与 Agent 核心。

    渠道把消息推入 inbound 队列，Agent 处理后把回复推入 outbound 队列。
    """

    def __init__(self):
        # LEARN: asyncio.Queue 是 Python 异步编程中的线程安全队列。
        # 生产者用 put() 放入消息，消费者用 get() 取出消息。
        # 如果队列为空，get() 会自动等待（挂起协程），不会阻塞整个程序。
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue()
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue()

    async def publish_inbound(self, msg: InboundMessage) -> None:
        """渠道调用：把用户消息放入入站队列。"""
        await self.inbound.put(msg)

    async def consume_inbound(self) -> InboundMessage:
        """Agent 调用：从入站队列取出下一条消息（阻塞等待）。"""
        return await self.inbound.get()

    async def publish_outbound(self, msg: OutboundMessage) -> None:
        """Agent 调用：把回复放入出站队列。"""
        await self.outbound.put(msg)

    async def consume_outbound(self) -> OutboundMessage:
        """渠道调用：从出站队列取出下一条回复（阻塞等待）。"""
        return await self.outbound.get()

    @property
    def inbound_size(self) -> int:
        return self.inbound.qsize()

    @property
    def outbound_size(self) -> int:
        return self.outbound.qsize()
