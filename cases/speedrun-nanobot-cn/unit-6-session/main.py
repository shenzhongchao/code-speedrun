"""
Unit 6 演示：会话管理的创建、持久化和历史查询

展示会话如何创建、消息如何追加、JSONL 持久化、
以及 last_consolidated 指针如何控制"可见历史"。
"""

import json
import sys
import os
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(__file__))

from session import Session, SessionManager


def main():
    print("=" * 50)
    print("Unit 6: 会话管理演示")
    print("=" * 50)

    # 创建临时工作区
    workspace = Path(tempfile.mkdtemp(prefix="nanobot_session_"))
    manager = SessionManager(workspace)
    print(f"\n工作区: {workspace}")

    # 1. 创建会话并添加消息
    print("\n--- 创建会话 ---")
    session = manager.get_or_create("telegram:12345")
    print(f"会话键: {session.key}")
    print(f"消息数: {len(session.messages)}")

    session.add_message("user", "你好，我是小明")
    session.add_message("assistant", "你好小明！有什么可以帮你的？")
    session.add_message("user", "帮我查一下天气")
    session.add_message("assistant", "好的，让我查一下。", tool_calls=[
        {"id": "c1", "type": "function", "function": {"name": "web_search", "arguments": '{"query":"天气"}'}}
    ])
    session.add_message("tool", "北京今天晴，25°C", tool_call_id="c1", name="web_search")
    session.add_message("assistant", "北京今天晴天，气温 25°C，适合出门。")

    print(f"添加 6 条消息后: {len(session.messages)} 条")

    # 2. 获取历史（全部未整合）
    print("\n--- 获取历史 ---")
    history = session.get_history()
    print(f"未整合消息: {len(history)} 条")
    for h in history:
        role = h["role"]
        content = str(h.get("content", ""))[:60]
        extra = ""
        if h.get("tool_calls"):
            extra = " [+tool_calls]"
        if h.get("tool_call_id"):
            extra = f" [tool_result: {h.get('name')}]"
        print(f"  {role:10s}: {content}{extra}")

    # 3. 模拟记忆整合（移动指针）
    print("\n--- 模拟记忆整合 ---")
    print(f"整合前: last_consolidated={session.last_consolidated}, 总消息={len(session.messages)}")
    session.last_consolidated = 4  # 前 4 条已整合
    print(f"整合后: last_consolidated={session.last_consolidated}")

    history = session.get_history()
    print(f"可见历史: {len(history)} 条")
    for h in history:
        print(f"  {h['role']:10s}: {str(h.get('content', ''))[:60]}")

    # 4. 持久化到磁盘
    print("\n--- 持久化 ---")
    manager.save(session)
    session_path = manager._get_session_path(session.key)
    print(f"文件路径: {session_path}")
    print(f"文件内容:")
    with open(session_path) as f:
        for i, line in enumerate(f):
            data = json.loads(line)
            if data.get("_type") == "metadata":
                print(f"  [元数据] key={data['key']}, last_consolidated={data['last_consolidated']}")
            else:
                print(f"  [{i}] {data.get('role', '?')}: {str(data.get('content', ''))[:50]}")

    # 5. 重新加载（模拟程序重启）
    print("\n--- 重新加载 ---")
    manager.invalidate(session.key)  # 清除缓存
    reloaded = manager.get_or_create("telegram:12345")
    print(f"重新加载: {len(reloaded.messages)} 条消息, last_consolidated={reloaded.last_consolidated}")
    print(f"可见历史: {len(reloaded.get_history())} 条")

    # 6. 对齐到 user 轮次
    print("\n--- 对齐到 user 轮次 ---")
    session2 = Session(key="test")
    # 故意以 tool 结果开头
    session2.messages = [
        {"role": "tool", "content": "orphan result", "tool_call_id": "x", "name": "test"},
        {"role": "assistant", "content": "orphan response"},
        {"role": "user", "content": "真正的开始"},
        {"role": "assistant", "content": "好的！"},
    ]
    history = session2.get_history()
    print(f"原始消息: {len(session2.messages)} 条")
    print(f"对齐后历史: {len(history)} 条（跳过了开头的 tool 和 assistant）")
    for h in history:
        print(f"  {h['role']}: {h['content']}")

    # 7. 清空会话
    print("\n--- 清空会话 ---")
    session.clear()
    print(f"清空后: {len(session.messages)} 条, last_consolidated={session.last_consolidated}")

    # 清理
    import shutil
    shutil.rmtree(workspace)
    print(f"\n已清理临时工作区")


if __name__ == "__main__":
    main()
