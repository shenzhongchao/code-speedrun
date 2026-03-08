"""
nanobot 工具系统 — 工具注册表

// LEARN: 工具注册表就像一个"工具箱"。
// 你可以往里面放工具（register）、取出工具（get）、查看有哪些工具（get_definitions）。
// Agent 每次调用 LLM 时，会把工具箱里所有工具的"说明书"一起发给 LLM，
// LLM 根据用户请求决定用哪个工具，然后 Agent 通过 execute() 执行。
"""

from typing import Any
from base import Tool


class ToolRegistry:
    """
    工具注册表：动态注册和执行工具。
    """

    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, tool: Tool) -> None:
        """注册一个工具。"""
        self._tools[tool.name] = tool

    def unregister(self, name: str) -> None:
        """注销一个工具。"""
        self._tools.pop(name, None)

    def get(self, name: str) -> Tool | None:
        """按名称获取工具。"""
        return self._tools.get(name)

    def get_definitions(self) -> list[dict[str, Any]]:
        """获取所有工具的 OpenAI 格式定义（发给 LLM 用）。"""
        return [tool.to_schema() for tool in self._tools.values()]

    # LEARN: execute 是工具执行的入口。
    # 它做三件事：1) 找到工具 2) 校验参数 3) 执行并返回结果。
    # 如果出错，会在错误信息后附加提示，引导 LLM 换个方式重试。
    async def execute(self, name: str, params: dict[str, Any]) -> str:
        _HINT = "\n\n[分析上面的错误，尝试不同的方法。]"

        tool = self._tools.get(name)
        if not tool:
            return f"Error: Tool '{name}' not found. Available: {', '.join(self.tool_names)}"

        try:
            errors = tool.validate_params(params)
            if errors:
                return f"Error: Invalid parameters for tool '{name}': " + "; ".join(errors) + _HINT
            result = await tool.execute(**params)
            if isinstance(result, str) and result.startswith("Error"):
                return result + _HINT
            return result
        except Exception as e:
            return f"Error executing {name}: {str(e)}" + _HINT

    @property
    def tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def __len__(self) -> int:
        return len(self._tools)
