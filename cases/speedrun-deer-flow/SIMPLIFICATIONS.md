# Simplifications

这份 speedrun 追求的是“先跑懂主干”，不是“一比一复制原仓库”。下面每一条都说明了哪里被压缩了，以及真实实现在哪。

## Unit 1: Overall Backend Flow

- [ ] 把 `nginx -> langgraph server -> gateway -> frontend` 的多进程部署折叠成一个 Python 脚本，真实入口见 `src/deer-flow/backend/app/gateway/app.py`、`src/deer-flow/backend/langgraph.json`、`src/deer-flow/frontend/`
- [ ] 用本地 `_demo_data/` 目录代替真实线程目录生命周期，真实路径逻辑见 `src/deer-flow/backend/packages/harness/deerflow/config/paths.py`
- [ ] 用 fake Docker runner 保持总装单元离线可跑；真实 Docker 执行留给 Unit 5 的 `--live` 路径

## Unit 2: Gateway and Config

- [ ] 去掉了 FastAPI、Pydantic 和 OpenAPI，只保留“列模型”和“上传文件”这两个最能解释边界的动作，真实实现见 `src/deer-flow/backend/app/gateway/app.py`、`src/deer-flow/backend/app/gateway/routers/models.py`、`src/deer-flow/backend/app/gateway/routers/uploads.py`
- [ ] 文件转换用一段 Markdown 预览替代真实的 markitdown 转换流程，真实实现见 `src/deer-flow/backend/app/gateway/routers/uploads.py`
- [ ] virtual path 只覆盖 `/mnt/user-data/uploads/...` 这条上传主线，没有实现真实 artifact serving 的全部下载、安全和 MIME 逻辑

## Unit 3: Thread Runtime

- [ ] 把 `ThreadDataMiddleware`、`SandboxMiddleware`、`ToolErrorHandlingMiddleware` 压成一个可直接运行的教学版本，真实实现见 `src/deer-flow/backend/packages/harness/deerflow/agents/middlewares/thread_data_middleware.py`、`src/deer-flow/backend/packages/harness/deerflow/sandbox/middleware.py`、`src/deer-flow/backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py`
- [ ] 没有实现 LangGraph 的真正 middleware protocol，只保留状态变化本身
- [ ] `VirtualPathMapper` 只实现 `/mnt/user-data` 到当前 thread `user-data/` 的映射，没有实现 skills、artifacts 或 Windows 路径的全部兼容逻辑

## Unit 4: Lead Agent Factory

- [ ] 没有调用 LangChain `create_agent()`，只保留“模型解析 + middleware 列表 + prompt section + tool list”四个关键结果，真实实现见 `src/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py`
- [ ] `skills prompt` 和 `memory prompt` 只接 Unit 6/7 的摘要，不复制真实 prompt 全文和异步 memory queue，真实实现见 `src/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/prompt.py` 和 `src/deer-flow/backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py`

## Unit 5: LangGraph Tools and Docker Sandbox

- [ ] Tool registry 只保留配置工具、builtin、subagent、vision、MCP 这五类来源，没有接真实反射加载和缓存，真实实现见 `src/deer-flow/backend/packages/harness/deerflow/tools/tools.py`
- [ ] LangGraph 只保留 `model -> tools -> model` 这条最小循环，没有复制 DeerFlow 的 middleware、checkpointer、streaming 和 `create_agent()` 装配，真实实现见 `src/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py`
- [ ] Docker sandbox 用短生命周期 `docker run --rm` 教学实现，没有实现真实 provider 的 acquire/release、远程 provisioner、容器复用和 shutdown 生命周期，真实实现见 `src/deer-flow/backend/packages/harness/deerflow/sandbox/` 和 `src/deer-flow/backend/packages/harness/deerflow/community/aio_sandbox/`
- [ ] 默认 demo 用 `ScriptedToolCallingModel` 保证离线可跑；只有 `--live` 模式才接 OpenAI-compatible LLM 和 Docker。真实模型配置逻辑见 `src/deer-flow/backend/packages/harness/deerflow/models/factory.py`
- [ ] Unit 5 只说明 MCP tools 会进入工具来源；MCP config、cache、deferred registry、`tool_search` 的完整流程放在 Unit 9

## Unit 6: Skills Prompt System

- [ ] front matter 解析只支持简单 `key: value`，没有完整 YAML 解析和全部校验，真实实现见 `src/deer-flow/backend/packages/harness/deerflow/skills/parser.py`
- [ ] `.skill` 安装保留 temp extract -> validate -> copy 的主形状，没有实现 FastAPI schema 和 router 错误模型，真实实现见 `src/deer-flow/backend/app/gateway/routers/skills.py`

## Unit 7: Memory Lifecycle

- [ ] 用 scripted LLM 代替真实模型调用，但保留真实 updater 的 `user/history/newFacts/factsToRemove` 结构化 payload 和 merge 形状，真实实现见 `src/deer-flow/backend/packages/harness/deerflow/agents/memory/updater.py`
- [ ] 没有实现 debounce queue 和 per-agent memory，只保留过滤、原子写入、重新加载三件事

## Unit 8: Subagent Delegation

- [ ] 用同步 deterministic executor 表达后台任务状态，没有复制线程池、timeout 和 LangGraph stream writer，真实实现见 `src/deer-flow/backend/packages/harness/deerflow/tools/builtins/task_tool.py`
- [ ] 保留父 agent 决策、runtime snapshot、子 agent initial state、事件流和父 agent synthesis，但没有创建真实 LangChain agent，也没有实现真实 subagent registry

## Unit 9: MCP Deferred Tools

- [ ] MCP loader 是 fake tool list，没有启动真实 MCP server，真实实现见 `src/deer-flow/backend/packages/harness/deerflow/mcp/client.py`
- [ ] deferred registry 只保留 name/description 搜索，没有接 LangChain schema serialization 的全部细节，真实实现见 `src/deer-flow/backend/packages/harness/deerflow/tools/builtins/tool_search.py`

## Unit 10: Artifacts and Archive Safety

- [ ] artifact response 用 dict 表达 HTML/text/binary 分支，没有启动 FastAPI response 类，真实实现见 `src/deer-flow/backend/app/gateway/routers/artifacts.py`
- [ ] archive validation 保留 traversal、absolute path、symlink、uncompressed size 防护，没有实现生产 router 的 HTTPException 包装
