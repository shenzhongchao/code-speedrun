"""Unit 3 demo: build nanobot-like prompt context."""

from __future__ import annotations

from context_builder import ContextBuilder, PromptInputs


def demo() -> None:
    inputs = PromptInputs(
        identity="# nanobot\n你是一个可靠的 AI 助手。",
        bootstrap_files={
            "AGENTS.md": "- 修改文件前先读取。",
            "TOOLS.md": "- 优先使用最小必要工具。",
        },
        memory_markdown="- 用户偏好：回复尽量简洁。",
        skills_summary="<skills><skill><name>weather</name></skill></skills>",
    )
    builder = ContextBuilder(inputs)

    history = [{"role": "user", "content": "昨天我们讨论了部署脚本"}]
    messages = builder.build_messages(
        history=history,
        current_message="帮我总结一下今天任务",
        channel="cli",
        chat_id="direct",
    )

    print("[Unit3] message_count:", len(messages))
    print("[Unit3] system_head:", messages[0]["content"].splitlines()[0])
    print("[Unit3] runtime_tag:", messages[-2]["content"].splitlines()[0])


if __name__ == "__main__":
    demo()
