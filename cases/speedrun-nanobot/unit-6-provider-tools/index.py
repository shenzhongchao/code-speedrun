"""Unit 6 demo: provider + tools contract."""

from __future__ import annotations

import asyncio
from pathlib import Path

from provider_tools import ListDirTool, MockProvider, ToolRegistry


async def demo() -> None:
    provider = MockProvider()
    registry = ToolRegistry()
    registry.register(ListDirTool(root=Path.cwd()))

    messages = [{"role": "user", "content": "请先列目录再回答"}]
    response = await provider.chat(messages, registry.definitions(), model="demo")

    if response.has_tool_calls:
        tool = response.tool_calls[0]
        result = await registry.execute(tool.name, tool.arguments)
        messages.extend(
            [
                {"role": "assistant", "content": response.content},
                {"role": "tool", "name": tool.name, "content": result},
            ]
        )
        final = await provider.chat(messages, registry.definitions(), model="demo")
        print("[Unit6] final:", final.content)
    else:
        print("[Unit6] direct:", response.content)


if __name__ == "__main__":
    asyncio.run(demo())
