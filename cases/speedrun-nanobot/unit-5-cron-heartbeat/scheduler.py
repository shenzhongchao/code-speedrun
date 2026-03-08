"""Minimal cron and heartbeat services inspired by nanobot."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Awaitable, Callable


@dataclass
class CronJob:
    id: str
    name: str
    message: str
    interval_s: int
    next_run_at: datetime
    enabled: bool = True


class CronService:
    """Simple in-memory scheduler."""

    def __init__(self) -> None:
        self.jobs: list[CronJob] = []

    def add_job(self, name: str, message: str, interval_s: int) -> CronJob:
        job = CronJob(
            id=f"job-{len(self.jobs) + 1}",
            name=name,
            message=message,
            interval_s=interval_s,
            next_run_at=datetime.now() + timedelta(seconds=interval_s),
        )
        self.jobs.append(job)
        return job

    async def run_pending(self, runner: Callable[[CronJob], Awaitable[str]]) -> list[str]:
        now = datetime.now()
        outputs: list[str] = []
        for job in self.jobs:
            if not job.enabled or now < job.next_run_at:
                continue
            result = await runner(job)
            outputs.append(result)
            job.next_run_at = now + timedelta(seconds=job.interval_s)
        return outputs


@dataclass
class HeartbeatDecision:
    action: str
    tasks: str = ""


class HeartbeatDecisionProvider:
    """Small deterministic decision model."""

    async def decide(self, heartbeat_markdown: str) -> HeartbeatDecision:
        if "- [ ]" in heartbeat_markdown:
            pending = [line.strip() for line in heartbeat_markdown.splitlines() if line.strip().startswith("- [ ]")]
            tasks = "；".join(item.replace("- [ ]", "").strip() for item in pending)
            return HeartbeatDecision(action="run", tasks=tasks)
        return HeartbeatDecision(action="skip")


class HeartbeatService:
    """Two-phase heartbeat: decide -> execute."""

    def __init__(
        self,
        provider: HeartbeatDecisionProvider,
        on_execute: Callable[[str], Awaitable[str]],
    ) -> None:
        self.provider = provider
        self.on_execute = on_execute

    async def tick(self, heartbeat_markdown: str) -> str | None:
        decision = await self.provider.decide(heartbeat_markdown)

        # LEARN: 像值班巡检。先判断“有没有事”，再决定“要不要叫醒主循环”。
        # 这就是 nanobot heartbeat 的两阶段思路（-> Unit 1）。
        if decision.action != "run":
            return None
        return await self.on_execute(decision.tasks)
