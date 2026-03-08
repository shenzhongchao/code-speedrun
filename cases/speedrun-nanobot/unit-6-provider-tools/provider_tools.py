"""Provider and tool abstractions inspired by nanobot."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: dict[str, Any]


@dataclass
class LLMResponse:
    content: str | None
    tool_calls: list[ToolCall] = field(default_factory=list)

    @property
    def has_tool_calls(self) -> bool:
        return bool(self.tool_calls)


class BaseProvider(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        model: str,
    ) -> LLMResponse:
        raise NotImplementedError


class MockProvider(BaseProvider):
    """A deterministic provider for local learning runs."""

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None,
        model: str,
    ) -> LLMResponse:
        if messages and messages[-1]["role"] == "tool":
            tool_result = str(messages[-1]["content"])
            return LLMResponse(content=f"我已读取工具结果：{tool_result[:60]}")

        last_user = ""
        for msg in reversed(messages):
            if msg["role"] == "user":
                last_user = str(msg["content"])
                break

        if "列目录" in last_user or "list" in last_user.lower():
            # LEARN: 像值班经理先派同事去查资料，再回来汇总。
            # 这里不直接回答，而是先发一个 tool call（-> Unit 4）。
            return LLMResponse(
                content="我先查看目录后再回答。",
                tool_calls=[ToolCall(id="call-1", name="list_dir", arguments={"path": "."})],
            )

        return LLMResponse(content=f"直接回复：{last_user}")


class Tool(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        raise NotImplementedError

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        raise NotImplementedError

    def to_schema(self) -> dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        self._tools[tool.name] = tool

    def definitions(self) -> list[dict[str, Any]]:
        return [tool.to_schema() for tool in self._tools.values()]

    async def execute(self, name: str, arguments: dict[str, Any]) -> str:
        tool = self._tools.get(name)
        if not tool:
            return f"Error: tool {name} not found"
        return await tool.execute(**arguments)


class ListDirTool(Tool):
    def __init__(self, root: Path):
        self.root = root

    @property
    def name(self) -> str:
        return "list_dir"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
            },
            "required": ["path"],
        }

    async def execute(self, **kwargs: Any) -> str:
        path = Path(kwargs["path"]).expanduser()
        target = (self.root / path).resolve() if not path.is_absolute() else path.resolve()
        names = sorted(item.name for item in target.iterdir())
        return ", ".join(names[:8]) if names else "(empty)"
