"""
nanobot 定时任务与心跳 — 定时任务服务（简化版）

// LEARN: 定时任务就像手机上的"闹钟"应用。
// 你可以设置三种闹钟：
// 1. "at"（定时）：在某个时间点执行一次，比如"明天早上 8 点提醒我"
// 2. "every"（间隔）：每隔一段时间执行，比如"每 30 分钟检查一次"
// 3. "cron"（表达式）：用 cron 表达式定义复杂周期，比如"每周一早上 9 点"
//
// 到了时间，定时任务服务会调用回调函数，把任务交给 Agent 执行。
"""

import asyncio
import json
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Coroutine


@dataclass
class CronSchedule:
    """定时计划。"""
    kind: str  # "at", "every", "cron"
    at_ms: int | None = None       # 定时：执行时间戳（毫秒）
    every_ms: int | None = None    # 间隔：毫秒数
    expr: str | None = None        # cron 表达式


@dataclass
class CronJob:
    """一个定时任务。"""
    id: str
    name: str
    enabled: bool = True
    schedule: CronSchedule = field(default_factory=lambda: CronSchedule(kind="every"))
    message: str = ""              # 要执行的指令
    next_run_at_ms: int | None = None
    last_run_at_ms: int | None = None
    last_status: str | None = None
    created_at_ms: int = 0


def _now_ms() -> int:
    return int(time.time() * 1000)


def _compute_next_run(schedule: CronSchedule, now_ms: int) -> int | None:
    """计算下次执行时间。"""
    if schedule.kind == "at":
        return schedule.at_ms if schedule.at_ms and schedule.at_ms > now_ms else None
    if schedule.kind == "every" and schedule.every_ms and schedule.every_ms > 0:
        return now_ms + schedule.every_ms
    return None


class CronService:
    """
    定时任务服务：管理和执行计划任务。

    // LEARN: CronService 的核心是一个"定时器循环"：
    // 1. 计算所有任务中最近的下次执行时间
    // 2. 用 asyncio.sleep 等到那个时间
    // 3. 执行到期的任务
    // 4. 重新计算下次执行时间，回到步骤 2
    """

    def __init__(
        self,
        store_path: Path,
        on_job: Callable[[CronJob], Coroutine[Any, Any, str | None]] | None = None,
    ):
        self.store_path = store_path
        self.on_job = on_job
        self.jobs: list[CronJob] = []
        self._running = False
        self._timer_task: asyncio.Task | None = None

    def _save(self) -> None:
        """保存任务到磁盘。"""
        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "jobs": [
                {
                    "id": j.id, "name": j.name, "enabled": j.enabled,
                    "schedule": {"kind": j.schedule.kind, "atMs": j.schedule.at_ms, "everyMs": j.schedule.every_ms},
                    "message": j.message,
                    "nextRunAtMs": j.next_run_at_ms, "lastRunAtMs": j.last_run_at_ms,
                    "lastStatus": j.last_status, "createdAtMs": j.created_at_ms,
                }
                for j in self.jobs
            ]
        }
        self.store_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    def add_job(self, name: str, schedule: CronSchedule, message: str) -> CronJob:
        """添加一个定时任务。"""
        now = _now_ms()
        job = CronJob(
            id=str(uuid.uuid4())[:8],
            name=name, schedule=schedule, message=message,
            next_run_at_ms=_compute_next_run(schedule, now),
            created_at_ms=now,
        )
        self.jobs.append(job)
        self._save()
        return job

    def remove_job(self, job_id: str) -> bool:
        """移除一个定时任务。"""
        before = len(self.jobs)
        self.jobs = [j for j in self.jobs if j.id != job_id]
        if len(self.jobs) < before:
            self._save()
            return True
        return False

    def list_jobs(self) -> list[CronJob]:
        """列出所有启用的任务。"""
        return [j for j in self.jobs if j.enabled]

    async def _execute_job(self, job: CronJob) -> None:
        """执行一个任务。"""
        print(f"  [Cron] 执行任务 '{job.name}': {job.message}")
        try:
            if self.on_job:
                result = await self.on_job(job)
                print(f"  [Cron] 结果: {result}")
            job.last_status = "ok"
        except Exception as e:
            job.last_status = "error"
            print(f"  [Cron] 失败: {e}")
        job.last_run_at_ms = _now_ms()

        # 一次性任务执行后禁用
        if job.schedule.kind == "at":
            job.enabled = False
            job.next_run_at_ms = None
        else:
            job.next_run_at_ms = _compute_next_run(job.schedule, _now_ms())

    async def tick(self) -> int:
        """检查并执行到期的任务。返回执行的任务数。"""
        now = _now_ms()
        due = [j for j in self.jobs if j.enabled and j.next_run_at_ms and now >= j.next_run_at_ms]
        for job in due:
            await self._execute_job(job)
        if due:
            self._save()
        return len(due)
