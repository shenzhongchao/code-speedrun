"""
nanobot LLM 提供者 — 提供者注册表（简化版）

// LEARN: 提供者注册表就像一本"电话簿"。
// 每个 AI 公司（Anthropic、OpenAI、DeepSeek 等）在这里登记自己的信息：
// 名字、API 密钥的环境变量名、模型名关键词、LiteLLM 前缀等。
// 当用户指定一个模型名（如 "claude-opus-4-5"），注册表能自动找到对应的提供者。
"""

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ProviderSpec:
    """一个 LLM 提供者的元数据。"""

    name: str                                    # 配置字段名，如 "anthropic"
    keywords: tuple[str, ...]                    # 模型名关键词，用于匹配
    env_key: str                                 # 环境变量名，如 "ANTHROPIC_API_KEY"
    display_name: str = ""                       # 显示名称
    litellm_prefix: str = ""                     # LiteLLM 路由前缀
    is_gateway: bool = False                     # 是否为网关（可路由任意模型）
    detect_by_key_prefix: str = ""               # 通过 API Key 前缀检测
    detect_by_base_keyword: str = ""             # 通过 API Base URL 关键词检测
    default_api_base: str = ""                   # 默认 API 地址
    supports_prompt_caching: bool = False         # 是否支持提示词缓存

    @property
    def label(self) -> str:
        return self.display_name or self.name.title()


# LEARN: 这是注册表的核心数据。顺序决定匹配优先级。
# 网关（Gateway）放在前面，因为它们可以路由任意模型。
# 标准提供者按使用频率排列。
PROVIDERS: tuple[ProviderSpec, ...] = (
    # 网关：可以路由任意模型
    ProviderSpec(
        name="openrouter",
        keywords=("openrouter",),
        env_key="OPENROUTER_API_KEY",
        display_name="OpenRouter",
        litellm_prefix="openrouter",
        is_gateway=True,
        detect_by_key_prefix="sk-or-",
        detect_by_base_keyword="openrouter",
        default_api_base="https://openrouter.ai/api/v1",
        supports_prompt_caching=True,
    ),
    # 标准提供者
    ProviderSpec(
        name="anthropic",
        keywords=("anthropic", "claude"),
        env_key="ANTHROPIC_API_KEY",
        display_name="Anthropic",
        supports_prompt_caching=True,
    ),
    ProviderSpec(
        name="openai",
        keywords=("openai", "gpt"),
        env_key="OPENAI_API_KEY",
        display_name="OpenAI",
    ),
    ProviderSpec(
        name="deepseek",
        keywords=("deepseek",),
        env_key="DEEPSEEK_API_KEY",
        display_name="DeepSeek",
        litellm_prefix="deepseek",
    ),
    ProviderSpec(
        name="gemini",
        keywords=("gemini",),
        env_key="GEMINI_API_KEY",
        display_name="Gemini",
        litellm_prefix="gemini",
    ),
    ProviderSpec(
        name="moonshot",
        keywords=("moonshot", "kimi"),
        env_key="MOONSHOT_API_KEY",
        display_name="Moonshot",
        litellm_prefix="moonshot",
    ),
)


def find_by_model(model: str) -> ProviderSpec | None:
    """根据模型名关键词匹配提供者。"""
    model_lower = model.lower()
    for spec in PROVIDERS:
        if spec.is_gateway:
            continue
        if any(kw in model_lower for kw in spec.keywords):
            return spec
    return None


def find_gateway(
    provider_name: str | None = None,
    api_key: str | None = None,
    api_base: str | None = None,
) -> ProviderSpec | None:
    """检测是否使用网关提供者。"""
    # 1. 按名称直接匹配
    if provider_name:
        for spec in PROVIDERS:
            if spec.name == provider_name and spec.is_gateway:
                return spec
    # 2. 按 API Key 前缀检测
    for spec in PROVIDERS:
        if spec.detect_by_key_prefix and api_key and api_key.startswith(spec.detect_by_key_prefix):
            return spec
    # 3. 按 API Base URL 关键词检测
    for spec in PROVIDERS:
        if spec.detect_by_base_keyword and api_base and spec.detect_by_base_keyword in api_base:
            return spec
    return None
