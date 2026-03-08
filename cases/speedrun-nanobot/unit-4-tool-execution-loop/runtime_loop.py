"""Simplified agent loop inspired by nanobot.agent.loop."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from speedrun_imports import load_unit_module

unit2 = load_unit_module("unit-2-message-bus/runtime_bus.py", "unit2_runtime_bus")
unit3 = load_unit_module("unit-3-context-prompt/context_builder.py", "unit3_context_builder")
unit6 = load_unit_module("unit-6-provider-tools/provider_tools.py", "unit6_provider_tools")

InboundMessage = unit2.InboundMessage
OutboundMessage = unit2.OutboundMessage
MessageBus = unit2.MessageBus
SessionStore = unit2.SessionStore
ContextBuilder = unit3.ContextBuilder
BaseProvider = unit6.BaseProvider
ToolRegistry = unit6.ToolRegistry


class AgentLoopCore:
    """Core loop: build context -> call model -> execute tools -> reply."""

    def __init__(
        self,
        bus: MessageBus,
        sessions: SessionStore,
        context_builder: ContextBuilder,
        provider: BaseProvider,
        tools: ToolRegistry,
        model: str = "demo-model",
        max_iterations: int = 4,
    ) -> None:
        self.bus = bus
        self.sessions = sessions
        self.context_builder = context_builder
        self.provider = provider
        self.tools = tools
        self.model = model
        self.max_iterations = max_iterations

    async def handle_once(self) -> None:
        incoming = await self.bus.consume_inbound()
        outgoing = await self.process_message(incoming)
        await self.bus.publish_outbound(outgoing)

    async def process_direct(
        self,
        content: str,
        session_key: str,
        channel: str,
        chat_id: str,
    ) -> str:
        msg = InboundMessage(channel=channel, sender_id="system", chat_id=chat_id, content=content)
        outgoing = await self.process_message(msg, force_session_key=session_key)
        return outgoing.content

    async def process_message(
        self,
        msg: InboundMessage,
        force_session_key: str | None = None,
    ) -> OutboundMessage:
        key = force_session_key or msg.session_key
        session = self.sessions.get_or_create(key)
        history = session.history(limit=12)

        messages = self.context_builder.build_messages(
            history=history,
            current_message=msg.content,
            channel=msg.channel,
            chat_id=msg.chat_id,
        )

        final_content = ""
        for _ in range(self.max_iterations):
            response = await self.provider.chat(
                messages=messages,
                tools=self.tools.definitions(),
                model=self.model,
            )

            if response.has_tool_calls:
                messages.append({"role": "assistant", "content": response.content})

                # LEARN: 像“先查资料再回答”。
                # 每个 tool_call 都会立刻执行并把结果插回消息列表（-> Unit 6）。
                for call in response.tool_calls:
                    result = await self.tools.execute(call.name, call.arguments)
                    messages.append(
                        {
                            "role": "tool",
                            "name": call.name,
                            "tool_call_id": call.id,
                            "content": result,
                        }
                    )
                continue

            final_content = response.content or "(empty response)"
            messages.append({"role": "assistant", "content": final_content})
            break

        session.append("user", msg.content)
        session.append("assistant", final_content)

        return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content=final_content)
