# Original Reading Path

这份文档的目标不是“再讲一遍 speedrun”，而是把你从教学版代码平稳送回 DeerFlow 真源码。建议顺序是：

1. 先跑 `Unit 1`
2. 然后按 `Unit 2 -> Unit 3 -> Unit 4 -> Unit 5` 回看真实源码
3. 最后再决定要不要进入前端、Docker、测试或 IM channels

## 90-Minute Route

如果你只想用最少时间建立源码地图，按这个顺序看：

1. `backend/app/gateway/app.py`
2. `backend/app/gateway/routers/models.py`
3. `backend/app/gateway/routers/uploads.py`
4. `backend/packages/harness/deerflow/config/paths.py`
5. `backend/packages/harness/deerflow/agents/middlewares/thread_data_middleware.py`
6. `backend/packages/harness/deerflow/sandbox/middleware.py`
7. `backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py`
8. `backend/packages/harness/deerflow/agents/lead_agent/agent.py`
9. `backend/packages/harness/deerflow/agents/lead_agent/prompt.py`
10. `backend/packages/harness/deerflow/tools/tools.py`
11. `backend/packages/harness/deerflow/tools/builtins/__init__.py`
12. `backend/packages/harness/deerflow/sandbox/local/local_sandbox.py`

## Unit Crosswalk

### Unit 1: Overall Backend Flow

教学版入口：

- `src/speedrun-deer-flow/unit-1-overall-backend-flow/main.py`

对应原仓主线：

- `src/deer-flow/backend/app/gateway/app.py`
- `src/deer-flow/backend/app/gateway/routers/models.py`
- `src/deer-flow/backend/app/gateway/routers/uploads.py`
- `src/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py`
- `src/deer-flow/backend/packages/harness/deerflow/tools/tools.py`
- `src/deer-flow/backend/packages/harness/deerflow/sandbox/local/local_sandbox.py`

你在 speedrun 里看到的是一条“单进程压缩链路”。回到原仓后，要补上的现实复杂度是：

- gateway 和 LangGraph server 是分开的进程边界
- thread data 和 sandbox 来自 middleware，不是主脚本直接 new
- prompt、memory、skills、MCP cache 都在 agent 创建时动态拼接

建议阅读问题：

- DeerFlow 为什么把 `/api/*` 和 `/api/langgraph/*` 分开？
- 为什么 uploads 先落宿主目录，再同步到 sandbox 视图？
- 为什么 lead agent 的创建要晚于 config 解析？

### Unit 2: Gateway and Config

教学版入口：

- `src/speedrun-deer-flow/unit-2-gateway-config/gateway_config_demo.py`

对应原仓文件：

- `src/deer-flow/backend/app/gateway/app.py`
- `src/deer-flow/backend/app/gateway/config.py`
- `src/deer-flow/backend/app/gateway/routers/models.py`
- `src/deer-flow/backend/app/gateway/routers/uploads.py`
- `src/deer-flow/backend/packages/harness/deerflow/config/app_config.py`

speedrun 保留的概念：

- gateway 是普通 HTTP 边界
- model metadata 从配置中裁剪后暴露
- 上传文件会得到物理路径、虚拟路径、artifact URL

回到原仓要补的真实复杂度：

- FastAPI/Pydantic schema
- lifespan startup/shutdown
- IM channel service 的启动
- env var 和 `config.yaml` 的热加载逻辑

建议先读：

1. `app/gateway/app.py`
2. `app/gateway/routers/models.py`
3. `app/gateway/routers/uploads.py`
4. `packages/harness/deerflow/config/app_config.py`

### Unit 3: Thread Runtime

教学版入口：

- `src/speedrun-deer-flow/unit-3-thread-runtime/thread_runtime_demo.py`

对应原仓文件：

- `src/deer-flow/backend/packages/harness/deerflow/agents/thread_state.py`
- `src/deer-flow/backend/packages/harness/deerflow/agents/middlewares/thread_data_middleware.py`
- `src/deer-flow/backend/packages/harness/deerflow/sandbox/middleware.py`
- `src/deer-flow/backend/packages/harness/deerflow/agents/middlewares/tool_error_handling_middleware.py`
- `src/deer-flow/backend/packages/harness/deerflow/config/paths.py`

speedrun 保留的概念：

- `thread_id` 变成 `workspace / uploads / outputs`
- `lazy_init` 和 eager init 的差别
- 工具错误如何被翻译成可恢复消息

回到原仓要补的真实复杂度：

- LangGraph middleware 生命周期
- `runtime.context` 和 `config.configurable` 的双重取值路径
- `ThreadState` reducer 行为，比如 artifacts 和 viewed_images 的合并
- sandbox provider 的复用与释放策略

建议先读：

1. `config/paths.py`
2. `agents/thread_state.py`
3. `agents/middlewares/thread_data_middleware.py`
4. `sandbox/middleware.py`
5. `agents/middlewares/tool_error_handling_middleware.py`

### Unit 4: Lead Agent Factory

教学版入口：

- `src/speedrun-deer-flow/unit-4-lead-agent-factory/lead_agent_factory_demo.py`

对应原仓文件：

- `src/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/agent.py`
- `src/deer-flow/backend/packages/harness/deerflow/agents/lead_agent/prompt.py`
- `src/deer-flow/backend/packages/harness/deerflow/agents/middlewares/`
- `src/deer-flow/backend/packages/harness/deerflow/models/`
- `src/deer-flow/backend/packages/harness/deerflow/config/agents_config.py`

speedrun 保留的概念：

- runtime flags 决定模型、中间件、工具
- plan mode、vision、subagent 开关会改变 agent 形状
- agent 在真正调用工具前，已经被“装配完成”

回到原仓要补的真实复杂度：

- `create_agent(...)` 的真实 LangChain/LangGraph 装配
- summarization middleware 的条件插入
- memory、title、clarification、loop detection 的次序要求
- prompt 里技能、memory、working directory、clarification system 的全文拼接

建议先读：

1. `agents/lead_agent/agent.py`
2. `agents/lead_agent/prompt.py`
3. `agents/middlewares/` 下的 `todo`、`memory`、`clarification`、`view_image`

### Unit 5: Tools and Sandbox

教学版入口：

- `src/speedrun-deer-flow/unit-5-tools-sandbox/tools_sandbox_demo.py`

对应原仓文件：

- `src/deer-flow/backend/packages/harness/deerflow/tools/tools.py`
- `src/deer-flow/backend/packages/harness/deerflow/tools/builtins/__init__.py`
- `src/deer-flow/backend/packages/harness/deerflow/tools/builtins/task_tool.py`
- `src/deer-flow/backend/packages/harness/deerflow/sandbox/__init__.py`
- `src/deer-flow/backend/packages/harness/deerflow/sandbox/local/local_sandbox.py`
- `src/deer-flow/backend/packages/harness/deerflow/sandbox/local/local_sandbox_provider.py`
- `src/deer-flow/backend/packages/harness/deerflow/community/aio_sandbox/`

speedrun 保留的概念：

- tool list 由 config + builtin + subagent + vision + MCP 拼出来
- local sandbox 暴露最小命令执行和文件 IO 接口

回到原仓要补的真实复杂度：

- `resolve_variable(...)` 的动态加载
- MCP cache、deferred registry、tool search 的联动
- Docker/provisioner sandbox provider
- task tool 与 subagent executor 的后台执行链路

建议先读：

1. `tools/tools.py`
2. `tools/builtins/__init__.py`
3. `sandbox/local/local_sandbox.py`
4. `sandbox/local/local_sandbox_provider.py`
5. `community/aio_sandbox/`

## Read With Commands

从仓库根目录运行：

```bash
cd src/deer-flow/backend
```

按 gateway 主线搜：

```bash
rg -n "FastAPI\\(|include_router|upload_files|list_models" app packages
```

按 runtime 主线搜：

```bash
rg -n "ThreadDataMiddleware|SandboxMiddleware|ToolErrorHandlingMiddleware|ThreadState" packages/harness/deerflow
```

按 lead agent 主线搜：

```bash
rg -n "make_lead_agent|_build_middlewares|create_agent|apply_prompt_template" packages/harness/deerflow
```

按 tools 和 sandbox 主线搜：

```bash
rg -n "get_available_tools|task_tool|view_image_tool|get_sandbox_provider|LocalSandbox" packages/harness/deerflow
```

## What To Read Later

先不要急着跳到这些区域，除非你已经把上面的四条主线看顺了：

- `frontend/`：产品界面层，不是 backend 主干理解的前置条件
- `docker/`：部署层，适合在你理解 runtime 和 sandbox 之后再读
- `backend/tests/`：适合用来检验你是否真的理解了边界，而不是拿来当第一份文档
- `app/channels/`：是额外接入层，不是 DeerFlow 后端主线的起点

## Exit Criteria

读完这份路线后，你应该能回答这四个问题：

1. DeerFlow 里哪个进程负责普通 REST API，哪个进程负责 agent runtime？
2. 一个 `thread_id` 最终怎样变成 `workspace / uploads / outputs`？
3. `make_lead_agent()` 真正装配了哪些东西？
4. 为什么工具执行一定要经过 sandbox，而不是直接让模型碰宿主机？
