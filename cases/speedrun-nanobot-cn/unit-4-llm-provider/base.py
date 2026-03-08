"""
nanobot LLM 提供者 — 基础接口

// LEARN: LLM 提供者就像"翻译官"。
// 不同的 AI 公司（OpenAI、Anthropic、DeepSeek）各有各的 API 格式，
// 但 nanobot 只需要一个统一的接口：发消息 → 收回复。
// LLMProvider 定义了这个统一接口，具体的"翻译"工作交给子类。
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


@dataclass
class ToolCallRequest:
    """LLM 返回的工具调用请求。"""
    id: str                      # 调用 ID（用于匹配结果）
    name: str                    # 工具名称
    arguments: dict[str, Any]    # 工具参数


@dataclass
class LLMResponse:
    """
    LLM 的统一回复格式。

    // LEARN: 一次 LLM 调用的结果只有两种情况：
    // 1. 纯文本回复（content 有值，tool_calls 为空）→ 对话结束
    // 2. 工具调用（tool_calls 有值）→ 需要执行工具后继续对话
    // 这个二选一的逻辑驱动了整个 Agent 循环。
    """
    content: str | None
    tool_calls: list[ToolCallRequest] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)
    reasoning_content: str | None = None  # 思维链内容（DeepSeek-R1、Kimi 等）

    @property
    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0


class LLMProvider(ABC):
    """
    LLM 提供者抽象基类。

    所有提供者（LiteLLM、Custom、OAuth）都实现这个接口。
    """

    def __init__(self, api_key: str | None = None, api_base: str | None = None):
        self.api_key = api_key
        self.api_base = api_base

    @abstractmethod
    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        """发送聊天请求，返回统一格式的回复。"""
        pass

    @abstractmethod
    def get_default_model(self) -> str:
        """获取默认模型名称。"""
        pass
