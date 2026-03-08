"""
nanobot LLM 提供者 — 模拟实现

// LEARN: 真实的 nanobot 通过 LiteLLM 库统一调用 100+ 个 LLM 提供者。
// 这里我们用一个 MockProvider 来模拟 LLM 的行为：
// 收到消息后，根据内容决定是直接回复还是调用工具。
// 这样不需要 API Key 就能完整演示 Agent 循环。
"""

import uuid
from typing import Any

from base import LLMProvider, LLMResponse, ToolCallRequest
from registry import find_by_model, find_gateway


class MockProvider(LLMProvider):
    """
    模拟 LLM 提供者（不需要真实 API Key）。

    行为规则：
    - 消息包含"天气" → 调用 web_search 工具
    - 消息包含"文件" → 调用 read_file 工具
    - 消息包含"命令" → 调用 exec 工具
    - 其他 → 直接文本回复
    """

    def __init__(self, default_model: str = "mock/demo-model"):
        super().__init__(api_key="mock-key")
        self.default_model = default_model
        self.call_count = 0

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]] | None = None,
        model: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> LLMResponse:
        self.call_count += 1
        last_msg = messages[-1].get("content", "") if messages else ""

        # 如果上一条是工具结果，生成总结回复
        if messages and messages[-1].get("role") == "tool":
            tool_result = messages[-1].get("content", "")
            return LLMResponse(
                content=f"根据工具返回的结果：{tool_result[:100]}",
                usage={"prompt_tokens": 50, "completion_tokens": 30, "total_tokens": 80},
            )

        # 根据内容决定是否调用工具
        if tools and isinstance(last_msg, str):
            if "天气" in last_msg:
                return LLMResponse(
                    content="让我搜索一下天气信息。",
                    tool_calls=[ToolCallRequest(
                        id=f"call_{uuid.uuid4().hex[:8]}",
                        name="web_search",
                        arguments={"query": "今天天气"},
                    )],
                )
            if "文件" in last_msg:
                return LLMResponse(
                    content="让我读取文件内容。",
                    tool_calls=[ToolCallRequest(
                        id=f"call_{uuid.uuid4().hex[:8]}",
                        name="read_file",
                        arguments={"path": "README.md"},
                    )],
                )

        # 默认：纯文本回复
        return LLMResponse(
            content=f"你好！我是 nanobot，使用模型 {model or self.default_model}。你说了：{last_msg}",
            usage={"prompt_tokens": 30, "completion_tokens": 20, "total_tokens": 50},
        )

    def get_default_model(self) -> str:
        return self.default_model
