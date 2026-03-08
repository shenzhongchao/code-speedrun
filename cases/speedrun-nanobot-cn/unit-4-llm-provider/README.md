# Unit 4: LLM 提供者

## 用大白话说

这个单元就像一个"万能翻译官"。不同的 AI 公司（Anthropic、OpenAI、DeepSeek、Moonshot 等）各说各的"方言"（API 格式不同），但 nanobot 只需要一个统一的对话接口。提供者系统负责把 nanobot 的请求"翻译"成各家 API 能理解的格式，再把回复"翻译"回来。

## 背景知识

**LiteLLM**：一个 Python 库，提供统一接口调用 100+ 个 LLM 提供者。你只需要 `acompletion(model="anthropic/claude-3", messages=[...])`，它会自动处理不同提供者的 API 差异。nanobot 的 `LiteLLMProvider` 就是基于它构建的。

**OpenAI Chat Completion 格式**：已成为事实标准的 LLM API 格式。核心是 `messages` 列表（每条消息有 `role` 和 `content`）和 `tools` 列表（工具定义）。几乎所有 LLM 提供者都兼容这个格式。

**网关（Gateway）**：像 OpenRouter 这样的服务，本身不提供模型，而是代理转发请求到各个提供者。好处是一个 API Key 就能访问所有模型。

**提示词缓存（Prompt Caching）**：Anthropic 等提供者支持的优化技术。对于重复的系统提示词，只需要在第一次请求时发送完整内容，后续请求可以复用缓存，节省 token 费用。

## 关键术语

- **LLMProvider**：LLM 提供者抽象基类，定义了 `chat()` 和 `get_default_model()` 接口
- **LLMResponse**：统一的 LLM 回复格式，包含文本内容和/或工具调用
- **ToolCallRequest**：LLM 返回的工具调用请求，包含工具名和参数
- **ProviderSpec**：提供者元数据，记录名称、关键词、环境变量等信息
- **Gateway**：网关提供者，可以路由任意模型（如 OpenRouter）
- **litellm_prefix**：LiteLLM 路由前缀，如 `deepseek/deepseek-chat`

## 这个单元做了什么

从 nanobot 的 `providers/` 目录提取了 LLM 提供者系统的核心逻辑：

1. **base.py** — 统一接口定义（LLMProvider、LLMResponse、ToolCallRequest）
2. **registry.py** — 提供者注册表，根据模型名或 API Key 自动匹配提供者
3. **provider.py** — MockProvider 模拟实现，演示 LLM 的两种回复模式
4. **main.py** — 完整演示：注册表匹配、网关检测、模拟调用

在真实的 nanobot 中，还有：
- `LiteLLMProvider`：通过 LiteLLM 库调用真实 API
- `CustomProvider`：直接调用 OpenAI 兼容端点（绕过 LiteLLM）
- `OpenAICodexProvider`：OAuth 认证的提供者
- 提示词缓存注入（→ Unit 5 上下文构建中会用到）

## 关键代码走读

**base.py — LLMResponse 的二元性**

```python
@property
def has_tool_calls(self) -> bool:
    return len(self.tool_calls) > 0
```

这个简单的属性驱动了整个 Agent 循环（→ Unit 1）：
- `has_tool_calls == True` → 执行工具，把结果加入消息，继续调用 LLM
- `has_tool_calls == False` → 对话结束，把 content 返回给用户

**registry.py — 三级匹配策略**

```python
# 1. 按名称直接匹配（用户在配置中指定了 provider）
# 2. 按 API Key 前缀检测（如 "sk-or-" → OpenRouter）
# 3. 按 API Base URL 关键词检测（如 URL 包含 "openrouter"）
```

为什么需要三级？因为用户可能以不同方式配置提供者：有人直接写名字，有人只填 API Key，有人只填 URL。三级匹配确保都能正确识别。

## 运行方式

```bash
cd unit-4-llm-provider
python main.py
```

## 预期输出

```
==================================================
Unit 4: LLM 提供者演示
==================================================

--- 已注册的提供者 ---
  OpenRouter [网关] [缓存]
    关键词: ('openrouter',), 环境变量: OPENROUTER_API_KEY
  Anthropic [缓存]
    关键词: ('anthropic', 'claude'), 环境变量: ANTHROPIC_API_KEY
  ...

--- 模型名 → 提供者匹配 ---
  claude-opus-4-5                → Anthropic
  gpt-4o                         → OpenAI
  deepseek-chat                  → DeepSeek
  ...

--- 网关自动检测 ---
  API Key 'sk-or-...' → OpenRouter
  ...

--- 模拟 LLM 调用 ---

  [纯文本回复]
  has_tool_calls: False
  content: 你好！我是 nanobot...

  [工具调用回复]
  has_tool_calls: True
  content: 让我搜索一下天气信息。
  tool_call: web_search({'query': '今天天气'}), id=call_...

  [工具结果总结]
  content: 根据工具返回的结果：北京今天晴，25°C，微风
```

## 练习

1. **修改练习**：在 `PROVIDERS` 中添加一个新的提供者（比如"百度文心一言"），设置合适的 keywords 和 env_key，然后验证 `find_by_model("ernie-bot")` 能正确匹配。

2. **扩展练习**：修改 `MockProvider`，让它支持 `reasoning_content`——当消息包含"思考"时，返回一个带有思维链的回复。

3. **用自己的话解释**：为什么 nanobot 要用注册表模式来管理提供者，而不是在代码里写一堆 if-elif？这种设计在添加新提供者时有什么优势？

## 调试指南

**观察点**：
- 在 `find_by_model()` 处加断点，观察模型名如何匹配到提供者
- 在 `provider.chat()` 处观察消息列表的结构

**常见问题**：
- `find_by_model()` 返回 None → 模型名不包含任何已知关键词，检查拼写
- 网关检测失败 → API Key 前缀不匹配，或 API Base URL 不包含关键词
- LLM 返回空 content → 某些提供者在有 tool_calls 时不返回 content，这是正常的

**状态检查**：
- `provider.call_count` 可以追踪 LLM 被调用了多少次
- `response.usage` 可以查看 token 消耗
