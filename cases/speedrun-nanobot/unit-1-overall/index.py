"""Unit 1 overall flow: gateway-like orchestration across all units."""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.append(str(ROOT))

from speedrun_imports import load_unit_module

unit2 = load_unit_module("unit-2-message-bus/runtime_bus.py", "unit2_runtime_bus")
unit3 = load_unit_module("unit-3-context-prompt/context_builder.py", "unit3_context_builder")
unit4 = load_unit_module("unit-4-tool-execution-loop/runtime_loop.py", "unit4_runtime_loop")
unit5 = load_unit_module("unit-5-cron-heartbeat/scheduler.py", "unit5_scheduler")
unit6 = load_unit_module("unit-6-provider-tools/provider_tools.py", "unit6_provider_tools")


async def demo_overall() -> None:
    bus = unit2.MessageBus()
    sessions = unit2.SessionStore()

    prompt_inputs = unit3.PromptInputs(
        identity="# nanobot\\n你是一个可执行任务的个人 AI 助手。",
        bootstrap_files={"AGENTS.md": "- 工具调用失败时先分析再重试。"},
        memory_markdown="- 用户偏好：先给结论，再给步骤。",
        skills_summary="<skills><skill><name>cron</name></skill></skills>",
    )
    context_builder = unit3.ContextBuilder(prompt_inputs)

    provider = unit6.MockProvider()
    tools = unit6.ToolRegistry()
    tools.register(unit6.ListDirTool(root=ROOT))

    agent = unit4.AgentLoopCore(
        bus=bus,
        sessions=sessions,
        context_builder=context_builder,
        provider=provider,
        tools=tools,
        model="mock-model",
    )

    # LEARN: 这里是 nanobot 的主干编排层。
    # 它不自己做业务细节，而是把消息总线、上下文、工具循环、调度器拼成流水线。
    await bus.publish_inbound(
        unit2.InboundMessage(
            channel="telegram",
            sender_id="alice",
            chat_id="chat-007",
            content="请先列目录，再总结今天要做什么",
        )
    )
    await agent.handle_once()
    first_reply = await bus.consume_outbound()

    cron = unit5.CronService()
    cron.add_job(name="daily-plan", message="列目录并给出今日计划", interval_s=0)

    async def run_cron(job: unit5.CronJob) -> str:
        return await agent.process_direct(
            content=job.message,
            session_key=f"cron:{job.id}",
            channel="cli",
            chat_id="cron",
        )

    cron_results = await cron.run_pending(run_cron)

    async def run_heartbeat(tasks: str) -> str:
        return await agent.process_direct(
            content=tasks,
            session_key="heartbeat",
            channel="cli",
            chat_id="direct",
        )

    heartbeat = unit5.HeartbeatService(
        provider=unit5.HeartbeatDecisionProvider(),
        on_execute=run_heartbeat,
    )
    heartbeat_markdown = """# HEARTBEAT
- [ ] 列目录并检查当前学习单元执行状态
- [x] 昨晚备份日志
"""
    heartbeat_result = await heartbeat.tick(heartbeat_markdown)

    print("[Unit1] chat reply:", first_reply.content)
    print("[Unit1] cron result:", cron_results)
    print("[Unit1] heartbeat result:", heartbeat_result)
    print("[Unit1] sessions:", sessions.list_keys())


if __name__ == "__main__":
    asyncio.run(demo_overall())
