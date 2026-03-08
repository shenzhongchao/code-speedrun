"""Unit 5 demo: cron scheduling + heartbeat trigger."""

from __future__ import annotations

import asyncio

from scheduler import CronService, HeartbeatDecisionProvider, HeartbeatService


async def demo() -> None:
    cron = CronService()
    cron.add_job(name="daily-review", message="总结今天完成事项", interval_s=0)

    async def run_cron(job):
        return f"[cron:{job.id}] {job.message}"

    cron_outputs = await cron.run_pending(run_cron)
    print("[Unit5] cron_outputs:", cron_outputs)

    async def run_heartbeat(tasks: str) -> str:
        return f"[heartbeat] 执行任务: {tasks}"

    hb = HeartbeatService(provider=HeartbeatDecisionProvider(), on_execute=run_heartbeat)

    heartbeat_md = """# HEARTBEAT
- [ ] 每晚 22:00 复盘今天输出
- [x] 清理临时文件
"""
    result = await hb.tick(heartbeat_md)
    print("[Unit5] heartbeat_result:", result)


if __name__ == "__main__":
    asyncio.run(demo())
