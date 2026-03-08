"""
nanobot 定时任务与心跳 — 心跳服务（简化版）

// LEARN: 心跳服务就像一个"值班员"。
// 每隔一段时间（默认 30 分钟），它会"醒来"检查 HEARTBEAT.md 文件，
// 看看有没有需要主动执行的任务。
//
// 分两个阶段：
// Phase 1（决策）：读取 HEARTBEAT.md，问 LLM "有没有要做的事？"
//   LLM 通过虚拟工具调用回答 "skip"（没事）或 "run"（有任务）
// Phase 2（执行）：如果有任务，通过回调函数交给 Agent 完整执行
//
// 这让 nanobot 不只是"被动回答"，还能"主动行动"。
"""

import asyncio
from pathlib import Path
from typing import Any, Callable, Coroutine


class HeartbeatService:
    """
    心跳服务：定期唤醒 Agent 检查任务。
    """

    def __init__(
        self,
        workspace: Path,
        on_decide: Callable[[str], Coroutine[Any, Any, tuple[str, str]]] | None = None,
        on_execute: Callable[[str], Coroutine[Any, Any, str]] | None = None,
        on_notify: Callable[[str], Coroutine[Any, Any, None]] | None = None,
        interval_s: int = 30 * 60,
        enabled: bool = True,
    ):
        self.workspace = workspace
        self.on_decide = on_decide    # Phase 1: 决策回调
        self.on_execute = on_execute  # Phase 2: 执行回调
        self.on_notify = on_notify    # 通知回调
        self.interval_s = interval_s
        self.enabled = enabled
        self._running = False
        self.tick_count = 0

    @property
    def heartbeat_file(self) -> Path:
        return self.workspace / "HEARTBEAT.md"

    def _read_heartbeat_file(self) -> str | None:
        if self.heartbeat_file.exists():
            return self.heartbeat_file.read_text(encoding="utf-8")
        return None

    # LEARN: tick 是心跳的核心逻辑。
    # 它模拟了真实 nanobot 中的两阶段流程：
    # 1. 读取 HEARTBEAT.md
    # 2. 调用决策函数判断是否有任务
    # 3. 如果有任务，调用执行函数
    # 4. 如果有结果，调用通知函数
    async def tick(self) -> str | None:
        """执行一次心跳检查。"""
        self.tick_count += 1
        content = self._read_heartbeat_file()
        if not content:
            return None

        print(f"  [Heartbeat] 检查 HEARTBEAT.md...")

        if self.on_decide:
            action, tasks = await self.on_decide(content)
            if action != "run":
                print(f"  [Heartbeat] 决策: skip（没有待办任务）")
                return None
            print(f"  [Heartbeat] 决策: run（发现任务: {tasks}）")

            if self.on_execute:
                result = await self.on_execute(tasks)
                if result and self.on_notify:
                    await self.on_notify(result)
                return result
        return None

    def stop(self) -> None:
        self._running = False
