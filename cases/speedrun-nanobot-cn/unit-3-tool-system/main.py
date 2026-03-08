"""
Unit 3 演示：工具系统的注册、校验和执行

展示如何定义工具、注册到工具箱、校验参数、执行工具，
以及安全防护如何拦截危险命令。
"""

import asyncio
import json
import sys
import os
import tempfile

sys.path.insert(0, os.path.dirname(__file__))

from base import Tool
from registry import ToolRegistry
from tools import ReadFileTool, ExecTool
from typing import Any


# --- 自定义工具示例 ---
class GreetTool(Tool):
    """一个简单的问候工具，用于演示工具定义。"""

    @property
    def name(self) -> str:
        return "greet"

    @property
    def description(self) -> str:
        return "用指定语言向用户问好。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "用户名"},
                "language": {
                    "type": "string",
                    "enum": ["zh", "en", "ja"],
                    "description": "语言代码",
                },
            },
            "required": ["name"],
        }

    async def execute(self, name: str, language: str = "zh", **kwargs: Any) -> str:
        greetings = {"zh": f"你好，{name}！", "en": f"Hello, {name}!", "ja": f"こんにちは、{name}！"}
        return greetings.get(language, f"Hi, {name}!")


async def main():
    print("=" * 50)
    print("Unit 3: 工具系统演示")
    print("=" * 50)

    # 1. 创建工具注册表并注册工具
    registry = ToolRegistry()
    registry.register(GreetTool())
    registry.register(ReadFileTool())
    registry.register(ExecTool(timeout=10))

    print(f"\n已注册 {len(registry)} 个工具: {registry.tool_names}")

    # 2. 查看工具定义（这就是发给 LLM 的内容）
    print("\n--- 工具定义（OpenAI 格式）---")
    definitions = registry.get_definitions()
    for d in definitions:
        func = d["function"]
        print(f"  {func['name']}: {func['description']}")
        print(f"    参数: {json.dumps(func['parameters']['properties'], ensure_ascii=False)}")

    # 3. 参数校验
    print("\n--- 参数校验 ---")
    greet_tool = registry.get("greet")
    # 合法参数
    errors = greet_tool.validate_params({"name": "小明", "language": "zh"})
    print(f"  合法参数: errors={errors}")
    # 缺少必填参数
    errors = greet_tool.validate_params({})
    print(f"  缺少 name: errors={errors}")
    # 非法枚举值
    errors = greet_tool.validate_params({"name": "小明", "language": "fr"})
    print(f"  非法语言: errors={errors}")

    # 4. 执行工具
    print("\n--- 工具执行 ---")
    result = await registry.execute("greet", {"name": "nanobot", "language": "zh"})
    print(f"  greet: {result}")

    result = await registry.execute("greet", {"name": "nanobot", "language": "en"})
    print(f"  greet(en): {result}")

    # 5. 读取文件
    print("\n--- 读取文件 ---")
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write("这是一个测试文件的内容。\nnanobot 工具系统演示。")
        tmp_path = f.name
    result = await registry.execute("read_file", {"path": tmp_path})
    print(f"  文件内容: {result}")
    os.unlink(tmp_path)

    # 6. 执行命令
    print("\n--- 执行命令 ---")
    result = await registry.execute("exec", {"command": "echo 'Hello from nanobot!'"})
    print(f"  echo: {result.strip()}")

    result = await registry.execute("exec", {"command": "python3 -c \"print(2+2)\""})
    print(f"  python: {result.strip()}")

    # 7. 安全防护
    print("\n--- 安全防护 ---")
    result = await registry.execute("exec", {"command": "rm -rf /"})
    print(f"  rm -rf /: {result}")

    result = await registry.execute("exec", {"command": "shutdown now"})
    print(f"  shutdown: {result}")

    # 8. 调用不存在的工具
    print("\n--- 错误处理 ---")
    result = await registry.execute("nonexistent", {})
    print(f"  不存在的工具: {result}")


if __name__ == "__main__":
    asyncio.run(main())
