"""Unit 4 demo: run a complete tool-call loop once."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from speedrun_imports import load_unit_module

unit2 = load_unit_module("unit-2-message-bus/runtime_bus.py", "unit2_runtime_bus")
unit3 = load_unit_module("unit-3-context-prompt/context_builder.py", "unit3_context_builder")
unit6 = load_unit_module("unit-6-provider-tools/provider_tools.py", "unit6_provider_tools")

from runtime_loop import AgentLoopCore


async def demo() -> None:
    bus = unit2.MessageBus()
    sessions = unit2.SessionStore()

    prompt_inputs = unit3.PromptInputs(identity="# nanobot\n你是可靠助手")
    context_builder = unit3.ContextBuilder(prompt_inputs)

    provider = unit6.MockProvider()
    tools = unit6.ToolRegistry()
    tools.register(unit6.ListDirTool(root=ROOT))

    agent = AgentLoopCore(
        bus=bus,
        sessions=sessions,
        context_builder=context_builder,
        provider=provider,
        tools=tools,
    )

    await bus.publish_inbound(
        unit2.InboundMessage(
            channel="cli",
            sender_id="u1",
            chat_id="direct",
            content="请先列目录再给我一句总结",
        )
    )

    await agent.handle_once()
    reply = await bus.consume_outbound()
    print("[Unit4] reply:", reply.content)
    print("[Unit4] sessions:", sessions.list_keys())


if __name__ == "__main__":
    asyncio.run(demo())
