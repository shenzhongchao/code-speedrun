"""
Unit 7 演示：定时任务和心跳服务

展示如何创建定时任务、检查到期任务、
以及心跳服务如何读取 HEARTBEAT.md 并决策执行。
"""

import asyncio
import sys
import os
import time
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from cron import CronService, CronSchedule, CronJob
from heartbeat import HeartbeatService


async def mock_job_handler(job: CronJob) -> str:
    """模拟任务执行回调。"""
    return f"已完成: {job.message}"


async def mock_decide(content: str) -> tuple[str, str]:
    """模拟心跳决策：检查 HEARTBEAT.md 内容。"""
    if "TODO" in content or "任务" in content:
        return "run", content.strip()
    return "skip", ""


async def mock_execute(tasks: str) -> str:
    """模拟心跳任务执行。"""
    return f"心跳执行完成: {tasks[:50]}"


async def mock_notify(result: str) -> None:
    """模拟通知。"""
    print(f"  [通知] {result}")


async def main():
    print("=" * 50)
    print("Unit 7: 定时任务与心跳演示")
    print("=" * 50)

    workspace = Path(tempfile.mkdtemp(prefix="nanobot_cron_"))

    # ========== 定时任务 ==========
    print("\n--- 定时任务服务 ---")
    cron = CronService(
        store_path=workspace / "cron.json",
        on_job=mock_job_handler,
    )

    # 添加任务
    job1 = cron.add_job(
        name="天气播报",
        schedule=CronSchedule(kind="every", every_ms=60000),  # 每 60 秒
        message="查询今天的天气并播报",
    )
    print(f"添加任务: {job1.name} (id={job1.id}, 每 60 秒)")

    job2 = cron.add_job(
        name="一次性提醒",
        schedule=CronSchedule(kind="at", at_ms=int(time.time() * 1000) - 1000),  # 已过期
        message="提醒用户开会",
    )
    print(f"添加任务: {job2.name} (id={job2.id}, 一次性)")

    job3 = cron.add_job(
        name="未来提醒",
        schedule=CronSchedule(kind="at", at_ms=int(time.time() * 1000) + 3600000),  # 1 小时后
        message="提醒用户喝水",
    )
    print(f"添加任务: {job3.name} (id={job3.id}, 1 小时后)")

    # 列出任务
    print(f"\n当前任务: {len(cron.list_jobs())} 个")
    for j in cron.list_jobs():
        status = "待执行" if j.next_run_at_ms else "无计划"
        print(f"  [{j.id}] {j.name}: {j.schedule.kind}, {status}")

    # 检查到期任务
    print(f"\n--- 检查到期任务 ---")
    executed = await cron.tick()
    print(f"执行了 {executed} 个到期任务")

    # 查看执行后状态
    for j in cron.jobs:
        if j.last_status:
            enabled = "启用" if j.enabled else "已禁用"
            print(f"  [{j.id}] {j.name}: {j.last_status} ({enabled})")

    # 移除任务
    print(f"\n--- 移除任务 ---")
    removed = cron.remove_job(job3.id)
    print(f"移除 '{job3.name}': {removed}")
    print(f"剩余任务: {len(cron.jobs)} 个")

    # 查看持久化文件
    print(f"\n持久化文件: {cron.store_path}")
    if cron.store_path.exists():
        import json
        data = json.loads(cron.store_path.read_text())
        print(f"  存储了 {len(data['jobs'])} 个任务")

    # ========== 心跳服务 ==========
    print("\n\n--- 心跳服务 ---")
    heartbeat = HeartbeatService(
        workspace=workspace,
        on_decide=mock_decide,
        on_execute=mock_execute,
        on_notify=mock_notify,
        interval_s=1800,
    )

    # 没有 HEARTBEAT.md 时
    print("\n场景 1: 没有 HEARTBEAT.md")
    result = await heartbeat.tick()
    print(f"  结果: {result}（None = 无事可做）")

    # 有 HEARTBEAT.md 但没有任务
    print("\n场景 2: HEARTBEAT.md 无任务")
    heartbeat.heartbeat_file.write_text("# 心跳配置\n\n一切正常，无待办事项。")
    result = await heartbeat.tick()
    print(f"  结果: {result}")

    # 有 HEARTBEAT.md 且有任务
    print("\n场景 3: HEARTBEAT.md 有任务")
    heartbeat.heartbeat_file.write_text("# 心跳配置\n\n## TODO\n- 每天早上 9 点发送天气预报\n- 检查服务器状态")
    result = await heartbeat.tick()
    print(f"  结果: {result}")

    print(f"\n心跳总检查次数: {heartbeat.tick_count}")

    # 清理
    import shutil
    shutil.rmtree(workspace)
    print(f"\n已清理临时工作区")


if __name__ == "__main__":
    asyncio.run(main())
