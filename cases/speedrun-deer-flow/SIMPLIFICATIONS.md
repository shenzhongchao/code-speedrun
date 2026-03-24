# Simplifications

这份 speedrun 追求的是“先跑懂主干”，不是“一比一复制原仓库”。下面每一条都说明了哪里被压缩了，以及真实实现在哪。

## Unit 1: Overall Backend Flow

- [ ] 把 `nginx -> langgraph server -> gateway -> frontend` 的多进程部署折叠成一个 Python 脚本，真实入口见 `src/deer-flow/backend/app/gateway/app.py`、`src/deer-flow/backend/langgraph.json`、`src/deer-flow/frontend/`
- [ ] 用本地 `_demo_data/` 目录代替真实线程目录生命周期，真实路径逻辑见 `src/deer-flow/backend/packages/harness/deerflow/config/paths.py`

## Unit 2: Gateway and Config

- [ ] 去掉了 FastAPI、Pydantic 和 OpenAPI，只保留“列模型”和“上传文件”这两个最能解释边界的动作，真实实现见 `src/deer-flow/backend/app/gateway/app.py`、`src/deer-flow/backend/app/gateway/routers/models.py`、`src/deer-flow/backend/app/gateway/routers/uploads.py`
- [ ] 文件转换用一段 Markdown 预览替代真实的 markitdown 转换流程，真实实现见 `src/deer-flow/backend/app/gateway/routers/uploads.py`

## Unit 3: Thread Runtime

- [ ] 把 `ThreadDataMiddleware`、`SandboxMiddleware`、`ToolErrorHandlingMiddleware` 压成一个可直接运行的教学版本，真实实现见 `src/deer-flow/backend/packages/harness/deerflow/agents/middlewares/thread_data_middleware.py`、`src/deer-flow/backend/packages/harness/deerflow/sandbox/middleware.py`、`src/deer-flow/backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py`
- [ ] 没有实现 LangGraph 的真正 middleware protocol，只保留状态变化本身

## Unit 4: Lead Agent Factory

- [ ] 没有调用 LangChain `create_agent()`，只保留“模型解析 + middleware 列表 + prompt section + tool list”四个关键结果，真实实现见 `src/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py`
- [ ] `skills prompt`、`memory prompt` 只展示为 section 名称，没有接真实 prompt 模板和内存存储，真实实现见 `src/deer-flow/backend/packages/harness/deerflow/agents/middlewares/memory_middleware.py`

## Unit 5: Tools and Sandbox

- [ ] Tool registry 只保留配置工具、builtin、subagent、vision、MCP 这五类来源，没有接真实反射加载和缓存，真实实现见 `src/deer-flow/backend/packages/harness/deerflow/tools/tools.py`
- [ ] 只演示 `LocalSandbox`，没有实现 Docker/provisioner 模式，真实实现见 `src/deer-flow/backend/packages/harness/deerflow/sandbox/local/` 和 `src/deer-flow/backend/packages/harness/deerflow/community/aio_sandbox/`
