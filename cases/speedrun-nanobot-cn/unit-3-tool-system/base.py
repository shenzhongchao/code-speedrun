"""
nanobot 工具系统 — 工具基类

// LEARN: 工具基类就像一份"工具说明书模板"。
// 每个工具（读文件、执行命令、搜索网页）都必须填写这份模板：
// 名字是什么、能做什么、需要什么参数、怎么执行。
// LLM 看到的是 JSON Schema 格式的"说明书"，据此决定调用哪个工具。
"""

from abc import ABC, abstractmethod
from typing import Any


class Tool(ABC):
    """
    工具抽象基类。

    每个工具必须实现四个属性/方法：
    - name: 工具名称（LLM 用这个名字来调用）
    - description: 工具描述（LLM 据此判断何时使用）
    - parameters: JSON Schema 格式的参数定义
    - execute: 实际执行逻辑
    """

    # LEARN: 类型映射表，用于参数校验。
    # JSON Schema 的类型名（如 "string"）映射到 Python 类型（如 str）。
    _TYPE_MAP = {
        "string": str,
        "integer": int,
        "number": (int, float),
        "boolean": bool,
        "array": list,
        "object": dict,
    }

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        pass

    @property
    @abstractmethod
    def parameters(self) -> dict[str, Any]:
        pass

    @abstractmethod
    async def execute(self, **kwargs: Any) -> str:
        pass

    def validate_params(self, params: dict[str, Any]) -> list[str]:
        """校验参数是否符合 JSON Schema。返回错误列表（空 = 合法）。"""
        schema = self.parameters or {}
        return self._validate(params, {**schema, "type": "object"}, "")

    def _validate(self, val: Any, schema: dict[str, Any], path: str) -> list[str]:
        t, label = schema.get("type"), path or "parameter"
        if t in self._TYPE_MAP and not isinstance(val, self._TYPE_MAP[t]):
            return [f"{label} should be {t}"]

        errors = []
        if "enum" in schema and val not in schema["enum"]:
            errors.append(f"{label} must be one of {schema['enum']}")
        if t == "object":
            props = schema.get("properties", {})
            for k in schema.get("required", []):
                if k not in val:
                    errors.append(f"missing required {path + '.' + k if path else k}")
            for k, v in val.items():
                if k in props:
                    errors.extend(self._validate(v, props[k], path + '.' + k if path else k))
        return errors

    # LEARN: to_schema() 把工具转换成 OpenAI Function Calling 格式。
    # 这是 LLM 理解"我有哪些工具可用"的标准协议。
    def to_schema(self) -> dict[str, Any]:
        """转换为 OpenAI function calling 格式。"""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }
