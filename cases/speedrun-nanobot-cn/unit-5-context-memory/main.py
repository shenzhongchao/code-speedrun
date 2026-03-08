"""
Unit 5 演示：上下文构建和双层记忆系统

展示系统提示词如何组装、记忆如何读写和整合。
"""

import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from context import ContextBuilder
from memory import MemoryStore


def main():
    print("=" * 50)
    print("Unit 5: 上下文与记忆演示")
    print("=" * 50)

    # 创建临时工作区
    workspace = Path(tempfile.mkdtemp(prefix="nanobot_demo_"))
    print(f"\n工作区: {workspace}")

    # --- 记忆系统 ---
    print("\n--- 双层记忆系统 ---")
    memory = MemoryStore(workspace)

    # 初始状态
    print(f"长期记忆: '{memory.read_long_term()}'（空）")

    # 写入长期记忆
    memory.write_long_term("- 用户名: 小明\n- 偏好语言: 中文\n- 项目: nanobot 学习")
    print(f"写入后: {memory.read_long_term()}")

    # 追加历史日志
    memory.append_history("[2025-01-15 10:30] 用户询问了 nanobot 的架构，讨论了消息总线的设计。")
    memory.append_history("[2025-01-15 14:00] 用户要求实现一个天气查询功能，使用了 web_search 工具。")
    print(f"\n历史日志文件: {memory.history_file}")
    print(f"内容:\n{memory.history_file.read_text()}")

    # 记忆整合
    print("--- 记忆整合 ---")
    old_messages = [
        {"role": "user", "content": "我叫小明，我在学 Python"},
        {"role": "assistant", "content": "你好小明！Python 是个好选择。"},
        {"role": "user", "content": "我最喜欢用 VS Code"},
        {"role": "assistant", "content": "VS Code 确实很适合 Python 开发。"},
    ]
    memory.consolidate_simple(
        old_messages=old_messages,
        history_entry="[2025-01-15 16:00] 用户自我介绍：小明，学习 Python，使用 VS Code。",
        memory_update="- 用户名: 小明\n- 偏好语言: 中文\n- 项目: nanobot 学习\n- 编程语言: Python\n- 编辑器: VS Code",
    )
    print(f"整合后长期记忆:\n{memory.read_long_term()}")

    # --- 上下文构建 ---
    print("\n--- 上下文构建 ---")
    ctx = ContextBuilder(workspace)

    # 构建系统提示词
    system_prompt = ctx.build_system_prompt()
    print(f"\n系统提示词（前 500 字符）:")
    print(system_prompt[:500])
    print("...")

    # 构建运行时上下文
    runtime = ctx.build_runtime_context(channel="telegram", chat_id="12345")
    print(f"\n运行时上下文:\n{runtime}")

    # 构建完整消息列表
    history = [
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好！有什么可以帮你的？"},
    ]
    messages = ctx.build_messages(
        history=history,
        current_message="帮我查一下天气",
        channel="telegram",
        chat_id="12345",
    )

    print(f"\n完整消息列表（{len(messages)} 条）:")
    for i, msg in enumerate(messages):
        role = msg["role"]
        content = msg["content"]
        if isinstance(content, str) and len(content) > 80:
            content = content[:80] + "..."
        print(f"  [{i}] {role}: {content}")

    # 创建引导文件看效果
    print("\n--- 引导文件效果 ---")
    (workspace / "SOUL.md").write_text("你是一个友善、专业的 AI 助手。回答要简洁有用。")
    (workspace / "USER.md").write_text("用户是一名 Python 开发者，偏好中文交流。")

    system_prompt = ctx.build_system_prompt()
    print(f"加入引导文件后，系统提示词长度: {len(system_prompt)} 字符")
    # 检查各部分是否存在
    has_identity = "nanobot" in system_prompt
    has_soul = "友善" in system_prompt
    has_user = "Python 开发者" in system_prompt
    has_memory = "小明" in system_prompt
    print(f"  包含身份信息: {has_identity}")
    print(f"  包含 SOUL.md: {has_soul}")
    print(f"  包含 USER.md: {has_user}")
    print(f"  包含长期记忆: {has_memory}")

    # 清理
    import shutil
    shutil.rmtree(workspace)
    print(f"\n已清理临时工作区")


if __name__ == "__main__":
    main()
