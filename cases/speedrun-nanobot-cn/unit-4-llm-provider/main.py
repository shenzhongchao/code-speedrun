"""
Unit 4 演示：LLM 提供者的统一接口、注册表匹配和模拟调用

展示提供者注册表如何根据模型名自动匹配提供者，
以及 LLM 如何返回文本回复或工具调用。
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from base import LLMResponse
from registry import PROVIDERS, find_by_model, find_gateway
from provider import MockProvider


async def main():
    print("=" * 50)
    print("Unit 4: LLM 提供者演示")
    print("=" * 50)

    # 1. 提供者注册表
    print("\n--- 已注册的提供者 ---")
    for spec in PROVIDERS:
        gateway_tag = " [网关]" if spec.is_gateway else ""
        cache_tag = " [缓存]" if spec.supports_prompt_caching else ""
        print(f"  {spec.label}{gateway_tag}{cache_tag}")
        print(f"    关键词: {spec.keywords}, 环境变量: {spec.env_key or '(OAuth)'}")

    # 2. 模型名匹配
    print("\n--- 模型名 → 提供者匹配 ---")
    test_models = [
        "claude-opus-4-5",
        "gpt-4o",
        "deepseek-chat",
        "gemini-2.0-flash",
        "kimi-k2.5",
        "unknown-model",
    ]
    for model in test_models:
        spec = find_by_model(model)
        result = spec.label if spec else "未匹配"
        print(f"  {model:30s} → {result}")

    # 3. 网关检测
    print("\n--- 网关自动检测 ---")
    gw = find_gateway(api_key="sk-or-abc123")
    print(f"  API Key 'sk-or-...' → {gw.label if gw else '未检测到'}")
    gw = find_gateway(api_base="https://openrouter.ai/api/v1")
    print(f"  API Base 'openrouter' → {gw.label if gw else '未检测到'}")
    gw = find_gateway(api_key="sk-normal-key")
    print(f"  API Key 'sk-normal-...' → {gw.label if gw else '未检测到'}")

    # 4. 模拟 LLM 调用
    print("\n--- 模拟 LLM 调用 ---")
    provider = MockProvider()

    # 4a. 纯文本回复
    response = await provider.chat(
        messages=[{"role": "user", "content": "你好，介绍一下自己"}],
    )
    print(f"\n  [纯文本回复]")
    print(f"  has_tool_calls: {response.has_tool_calls}")
    print(f"  content: {response.content}")
    print(f"  usage: {response.usage}")

    # 4b. 工具调用回复
    tool_defs = [{"type": "function", "function": {"name": "web_search", "parameters": {}}}]
    response = await provider.chat(
        messages=[{"role": "user", "content": "今天天气怎么样？"}],
        tools=tool_defs,
    )
    print(f"\n  [工具调用回复]")
    print(f"  has_tool_calls: {response.has_tool_calls}")
    print(f"  content: {response.content}")
    for tc in response.tool_calls:
        print(f"  tool_call: {tc.name}({tc.arguments}), id={tc.id}")

    # 4c. 工具结果后的总结
    response = await provider.chat(
        messages=[
            {"role": "user", "content": "今天天气怎么样？"},
            {"role": "assistant", "content": "让我搜索一下。", "tool_calls": [{"id": "c1", "type": "function", "function": {"name": "web_search", "arguments": "{}"}}]},
            {"role": "tool", "tool_call_id": "c1", "name": "web_search", "content": "北京今天晴，25°C，微风"},
        ],
    )
    print(f"\n  [工具结果总结]")
    print(f"  content: {response.content}")

    print(f"\n  总调用次数: {provider.call_count}")


if __name__ == "__main__":
    asyncio.run(main())
