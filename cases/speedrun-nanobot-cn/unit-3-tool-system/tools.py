"""
nanobot 工具系统 — 示例工具实现

包含两个简化版工具：
- ReadFileTool: 读取文件内容
- ExecTool: 执行 shell 命令（带安全防护）
"""

import asyncio
import os
import re
from pathlib import Path
from typing import Any

from base import Tool


class ReadFileTool(Tool):
    """读取文件内容的工具。"""

    def __init__(self, workspace: Path | None = None):
        self._workspace = workspace

    @property
    def name(self) -> str:
        return "read_file"

    @property
    def description(self) -> str:
        return "读取指定路径的文件内容。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "文件路径"},
            },
            "required": ["path"],
        }

    async def execute(self, path: str, **kwargs: Any) -> str:
        p = Path(path).expanduser()
        if not p.is_absolute() and self._workspace:
            p = self._workspace / p
        p = p.resolve()

        if not p.exists():
            return f"Error: File not found: {path}"
        if not p.is_file():
            return f"Error: Not a file: {path}"
        return p.read_text(encoding="utf-8")


class ExecTool(Tool):
    """
    执行 shell 命令的工具（带安全防护）。

    // LEARN: 这是 nanobot 最强大也最危险的工具。
    // 为了防止 LLM 执行破坏性命令（如 rm -rf /），
    // 内置了一套"黑名单"正则匹配机制。
    // 任何匹配到危险模式的命令都会被拦截。
    """

    # LEARN: 危险命令模式列表。
    # 每个正则匹配一类危险操作：删除文件、格式化磁盘、关机、fork 炸弹等。
    DENY_PATTERNS = [
        r"\brm\s+-[rf]{1,2}\b",
        r"\b(mkfs|diskpart)\b",
        r"\bdd\s+if=",
        r"\b(shutdown|reboot|poweroff)\b",
        r":\(\)\s*\{.*\};\s*:",  # fork bomb
    ]

    def __init__(self, timeout: int = 60, working_dir: str | None = None):
        self.timeout = timeout
        self.working_dir = working_dir

    @property
    def name(self) -> str:
        return "exec"

    @property
    def description(self) -> str:
        return "执行 shell 命令并返回输出。请谨慎使用。"

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的 shell 命令"},
            },
            "required": ["command"],
        }

    async def execute(self, command: str, **kwargs: Any) -> str:
        # 安全检查
        lower = command.strip().lower()
        for pattern in self.DENY_PATTERNS:
            if re.search(pattern, lower):
                return "Error: 命令被安全防护拦截（检测到危险模式）"

        cwd = self.working_dir or os.getcwd()
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self.timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                return f"Error: 命令超时（{self.timeout}秒）"

            parts = []
            if stdout:
                parts.append(stdout.decode("utf-8", errors="replace"))
            if stderr:
                text = stderr.decode("utf-8", errors="replace").strip()
                if text:
                    parts.append(f"STDERR:\n{text}")
            if process.returncode != 0:
                parts.append(f"\nExit code: {process.returncode}")

            result = "\n".join(parts) if parts else "(no output)"
            # 截断过长输出
            if len(result) > 10000:
                result = result[:10000] + f"\n... (截断，还有 {len(result) - 10000} 字符)"
            return result
        except Exception as e:
            return f"Error: {e}"
