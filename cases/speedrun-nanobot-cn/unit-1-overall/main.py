"""
Unit 1: 全局总览 — nanobot 端到端消息处理流程

// LEARN: 这是 nanobot 的"总指挥部"。
// 它把所有子系统串联起来，展示一条消息从用户发出到收到回复的完整旅程：
//
//   用户消息 → 消息总线(Unit 2) → Agent 循环 → 上下文构建(Unit 5)
//   → LLM 调用(Unit 4) → 工具执行(Unit 3) → 会话保存(Unit 6)
//   → 消息总线(Unit 2) → 回复给用户
//
// 这不是模拟——每个模块都是从对应 Unit 导入的真实实现。
"""

import asyncio
import json
import sys
import os
import tempfile
from pathlib import Path

# LEARN: 添加所有 Unit 的路径到 sys.path。
# 注意顺序：sys.path.insert(0, ...) 后插入的优先级更高。
# unit-3 和 unit-4 都有同名模块（base.py、registry.py），
# 这里先把路径都加入，再用分阶段导入避免命名冲突。
_base_dir = os.path.dirname(os.path.dirname(__file__))
_unit_paths = {
    "unit-7": os.path.join(_base_dir, "unit-7-cron-heartbeat"),
    "unit-6": os.path.join(_base_dir, "unit-6-session"),
    "unit-5": os.path.join(_base_dir, "unit-5-context-memory"),
    "unit-4": os.path.join(_base_dir, "unit-4-llm-provider"),
    "unit-2": os.path.join(_base_dir, "unit-2-message-bus"),
    "unit-3": os.path.join(_base_dir, "unit-3-tool-system"),
}
for _path in _unit_paths.values():
    if _path not in sys.path:
        sys.path.insert(0, _path)

# LEARN: 这些导入来自真实的 Unit 模块，不是 print 模拟。
from events import InboundMessage, OutboundMessage       # → Unit 2
from bus import MessageBus                                 # → Unit 2
from registry import ToolRegistry                          # → Unit 3
from tools import ReadFileTool, ExecTool                   # → Unit 3

# unit-3 和 unit-4 都有 base.py / registry.py。
# 先缓存 unit-3 模块，再临时清理同名模块导入 unit-4 provider，最后恢复缓存。
_tool_base_module = sys.modules.get("base")
_tool_registry_module = sys.modules.get("registry")
sys.modules.pop("base", None)
sys.modules.pop("registry", None)
_unit4_path = _unit_paths["unit-4"]
if _unit4_path in sys.path:
    sys.path.remove(_unit4_path)
sys.path.insert(0, _unit4_path)
from provider import MockProvider                          # → Unit 4
if _tool_base_module is not None:
    sys.modules["base"] = _tool_base_module
if _tool_registry_module is not None:
    sys.modules["registry"] = _tool_registry_module

from context import ContextBuilder                         # → Unit 5
from session import Session, SessionManager                # → Unit 6
from cron import CronService, CronSchedule, CronJob       # → Unit 7
from heartbeat import HeartbeatService                     # → Unit 7


# LEARN: AgentLoop 是 nanobot 的核心引擎。
# 它的工作循环非常简单：
# 1. 从消息总线取出用户消息
# 2. 构建上下文（系统提示词 + 历史 + 当前消息）
# 3. 调用 LLM
# 4. 如果 LLM 要调用工具 → 执行工具 → 把结果加入消息 → 回到步骤 3
# 5. 如果 LLM 直接回复 → 保存会话 → 发送回复
class AgentLoop:
    """nanobot 的核心处理引擎（简化版）。"""

    def __init__(
        self,
        bus: MessageBus,
        provider: MockProvider,
        workspace: Path,
        tools: ToolRegistry,
        sessions: SessionManager,
        max_iterations: int = 10,
    ):
        self.bus = bus
        self.provider = provider
        self.workspace = workspace
        self.tools = tools
        self.sessions = sessions
        self.context = ContextBuilder(workspace)
        self.max_iterations = max_iterations

    async def process_message(self, msg: InboundMessage) -> OutboundMessage:
        """处理一条入站消息，返回出站回复。"""
        print(f"\n  [AgentLoop] 收到: {msg.content}")

        # 1. 获取或创建会话 → Unit 6
        session = self.sessions.get_or_create(msg.session_key)

        # 2. 构建上下文 → Unit 5
        history = session.get_history(max_messages=50)
        messages = self.context.build_messages(
            history=history,
            current_message=msg.content,
            channel=msg.channel,
            chat_id=msg.chat_id,
        )
        print(f"  [AgentLoop] 上下文: {len(messages)} 条消息（含 {len(history)} 条历史）")

        # 3. Agent 循环：LLM 调用 + 工具执行 → Unit 4 + Unit 3
        final_content, tools_used = await self._run_loop(messages)

        # 4. 保存会话 → Unit 6
        session.add_message("user", msg.content)
        session.add_message("assistant", final_content or "", tools_used=tools_used)
        self.sessions.save(session)

        if tools_used:
            print(f"  [AgentLoop] 使用了工具: {tools_used}")
        print(f"  [AgentLoop] 回复: {final_content}")

        # 5. 构建出站消息 → Unit 2
        return OutboundMessage(
            channel=msg.channel,
            chat_id=msg.chat_id,
            content=final_content or "处理完成。",
        )

    async def _run_loop(self, messages: list[dict]) -> tuple[str | None, list[str]]:
        """Agent 迭代循环：调用 LLM → 执行工具 → 重复直到得到文本回复。"""
        tools_used: list[str] = []

        for iteration in range(self.max_iterations):
            # 调用 LLM → Unit 4
            response = await self.provider.chat(
                messages=messages,
                tools=self.tools.get_definitions(),
            )

            if response.has_tool_calls:
                # LLM 要调用工具
                for tc in response.tool_calls:
                    tools_used.append(tc.name)
                    print(f"  [AgentLoop] 工具调用: {tc.name}({tc.arguments})")

                    # 执行工具 → Unit 3
                    result = await self.tools.execute(tc.name, tc.arguments)
                    print(f"  [AgentLoop] 工具结果: {result[:80]}...")

                    # 把工具结果加入消息，继续循环
                    messages.append({
                        "role": "assistant", "content": response.content,
                        "tool_calls": [{"id": tc.id, "type": "function",
                                        "function": {"name": tc.name,
                                                     "arguments": json.dumps(tc.arguments)}}],
                    })
                    messages.append({
                        "role": "tool", "tool_call_id": tc.id,
                        "name": tc.name, "content": result,
                    })
            else:
                # LLM 直接回复，循环结束
                return response.content, tools_used

        return "达到最大迭代次数。", tools_used


async def main():
    print("=" * 60)
    print("Unit 1: 全局总览 — nanobot 端到端消息处理")
    print("=" * 60)

    # 初始化所有子系统
    workspace = Path(tempfile.mkdtemp(prefix="nanobot_overall_"))
    print(f"\n工作区: {workspace}")

    # 写入一些引导文件，让上下文更丰富
    (workspace / "SOUL.md").write_text("你是一个友善、专业的 AI 助手。")
    (workspace / "memory").mkdir(exist_ok=True)
    (workspace / "memory" / "MEMORY.md").write_text("- 用户偏好: 中文\n- 项目: nanobot 学习")

    bus = MessageBus()                              # → Unit 2
    provider = MockProvider()                        # → Unit 4
    tools = ToolRegistry()                           # → Unit 3
    tools.register(ReadFileTool(workspace=workspace))
    tools.register(ExecTool(timeout=10))
    sessions = SessionManager(workspace)             # → Unit 6

    agent = AgentLoop(
        bus=bus, provider=provider, workspace=workspace,
        tools=tools, sessions=sessions,
    )

    # ========== 场景 1: 简单对话 ==========
    print("\n" + "=" * 40)
    print("场景 1: 简单对话（纯文本回复）")
    print("=" * 40)

    msg1 = InboundMessage(
        channel="telegram", sender_id="user_001",
        chat_id="chat_42", content="你好，介绍一下自己",
    )
    reply1 = await agent.process_message(msg1)
    print(f"\n  最终回复: {reply1.content}")

    # ========== 场景 2: 工具调用 ==========
    print("\n" + "=" * 40)
    print("场景 2: 工具调用（读取文件）")
    print("=" * 40)

    # 创建一个测试文件
    (workspace / "test.txt").write_text("这是 nanobot 的测试文件内容。")

    msg2 = InboundMessage(
        channel="telegram", sender_id="user_001",
        chat_id="chat_42", content="帮我读取文件 test.txt",
    )
    reply2 = await agent.process_message(msg2)
    print(f"\n  最终回复: {reply2.content}")

    # ========== 场景 3: 多轮对话（会话持久化）==========
    print("\n" + "=" * 40)
    print("场景 3: 多轮对话（会话持久化）")
    print("=" * 40)

    session = sessions.get_or_create("telegram:chat_42")
    print(f"  会话消息数: {len(session.messages)}")
    print(f"  会话历史:")
    for m in session.messages:
        print(f"    {m['role']}: {str(m.get('content', ''))[:60]}")

    # ========== 场景 4: 定时任务 ==========
    print("\n" + "=" * 40)
    print("场景 4: 定时任务（→ Unit 7）")
    print("=" * 40)

    async def cron_handler(job: CronJob) -> str:
        result = await agent.process_message(InboundMessage(
            channel="system", sender_id="cron",
            chat_id="cron:direct", content=job.message,
        ))
        return result.content

    cron = CronService(store_path=workspace / "cron.json", on_job=cron_handler)
    import time
    job = cron.add_job(
        name="状态检查",
        schedule=CronSchedule(kind="at", at_ms=int(time.time() * 1000) - 1),
        message="报告当前状态",
    )
    print(f"  添加定时任务: {job.name}")
    executed = await cron.tick()
    print(f"  执行了 {executed} 个任务")

    # ========== 场景 5: 心跳服务 ==========
    print("\n" + "=" * 40)
    print("场景 5: 心跳服务（→ Unit 7）")
    print("=" * 40)

    async def heartbeat_decide(content: str) -> tuple[str, str]:
        if "TODO" in content:
            return "run", "检查待办事项"
        return "skip", ""

    async def heartbeat_execute(tasks: str) -> str:
        result = await agent.process_message(InboundMessage(
            channel="system", sender_id="heartbeat",
            chat_id="heartbeat:direct", content=tasks,
        ))
        return result.content

    heartbeat = HeartbeatService(
        workspace=workspace,
        on_decide=heartbeat_decide,
        on_execute=heartbeat_execute,
    )
    (workspace / "HEARTBEAT.md").write_text("# 待办\n\n## TODO\n- 检查系统状态")
    result = await heartbeat.tick()
    print(f"  心跳结果: {result}")

    # ========== 总结 ==========
    print("\n" + "=" * 60)
    print("总结")
    print("=" * 60)
    print(f"  LLM 调用次数: {provider.call_count}")
    print(f"  注册工具数: {len(tools)}")
    print(f"  会话文件: {list(sessions.sessions_dir.glob('*.jsonl'))}")

    # 清理
    import shutil
    shutil.rmtree(workspace)
    print(f"\n  已清理临时工作区")


if __name__ == "__main__":
    asyncio.run(main())
