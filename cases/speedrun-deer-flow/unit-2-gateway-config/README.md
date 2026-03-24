# Unit 2: Gateway and Config

> **Motto**: *HTTP is the front desk*

## In Plain Language

这个单元回答一个很实际的问题：为什么 DeerFlow 不把所有事都塞进 agent？因为“列模型”“收文件”这种动作，本质上是普通后端接口，放在 Gateway API 会更稳定、更容易给前端调用。

## Background Knowledge

- **配置像菜单**：系统先公开自己“有什么模型、有什么工具”，前端才能让用户选。技术上就是从配置对象里挑出能安全暴露的字段。
- **上传像前台收件**：文件先被收进一个线程专属的地方，后面的 agent 才能拿到路径。技术上就是把上传保存到 `uploads` 目录，并生成虚拟路径。
- **虚拟路径像货架编号**：真实文件放在磁盘，但 agent 看到的是统一的 `/mnt/user-data/...` 路径。这样后端以后换 sandbox 实现时，路径语义不用跟着变。

## Key Terminology

- **Gateway API**：DeerFlow 的 REST 边界层，真实代码在 `backend/app/gateway/`
- **Model metadata**：给前端展示的模型信息，不包括 API key 这种敏感字段
- **Artifact URL**：前端回头下载文件时使用的 HTTP 路径
- **Convertible extension**：上传后会顺手转成 Markdown 预览的文件后缀

## What This Unit Does

这个单元保留了 Gateway API 最值得学的两个动作：

1. 从配置里列出模型清单
2. 接收上传文件，为每个文件生成物理路径、虚拟路径和 artifact URL

这正好对应原仓库里的 `models` router 和 `uploads` router。学会这两个动作，你就能明白：为什么 DeerFlow 前端不是直接和 agent“硬聊”，而是先靠 gateway 打通很多普通后端能力。

## Key Code Walkthrough

- `gateway_config_demo.py:46-84`：构造 demo config。这里保留了多模型和多工具的形状，好让后面的 `LeadAgentFactory` 和 `ToolRegistry` 能真实复用。
- `gateway_config_demo.py:97-110`：`list_models()` 只返回前端该看到的字段，模仿原仓库 `GET /api/models` 的行为。
- `gateway_config_demo.py:112-144`：`upload_files()` 做了三件要紧的事：清理文件名、写入线程上传目录、生成虚拟路径和 artifact URL。
- `gateway_config_demo.py:132-137`：可转换文件多生成一个 Markdown 预览。这是原仓库 uploads 路由里最容易被忽略但非常实用的细节。
- `gateway_config_demo.py:165-189`：`run_demo()` 用两个文件跑一遍最小上传流，输出就是一个精简版的 gateway 响应。

## How to Run

```bash
cd src/speedrun-deer-flow
python unit-2-gateway-config/main.py
```

## Expected Output

你应该看到一个 JSON，其中：

- `health.status` 是 `healthy`
- `models.models` 有 3 个模型
- `uploads.files` 有 2 个文件
- `roadmap.docx` 会额外生成 `roadmap.md`

## Exercises

### Explain It Back

为什么 DeerFlow 要在 gateway 里先把上传文件整理成 `path / virtual_path / artifact_url`，而不是把原始字节直接塞进 prompt？

### Modify It

- 给 `build_demo_config()` 再加一个模型，看看 `list_models()` 会不会自动带出来。
- 把 `CONVERTIBLE_EXTENSIONS` 里的 `.docx` 去掉，再观察 `roadmap.md` 是否还会出现。

## Debug Guide

### Observation Points

File: `gateway_config_demo.py:46`
What to observe: demo config 怎样同时为后面几个单元提供模型和工具信息
Breakpoint or log: 查看 `build_demo_config()` 的返回值

File: `gateway_config_demo.py:97`
What to observe: 哪些字段被暴露给前端，哪些字段没有
Breakpoint or log: 在 `list_models()` 里检查生成的 `models` 列表

File: `gateway_config_demo.py:112`
What to observe: 上传逻辑如何生成路径和 URL
Breakpoint or log: 单步进入 `upload_files()`

File: `gateway_config_demo.py:132`
What to observe: 哪些文件会生成 Markdown 预览
Breakpoint or log: 查看 `file_path.suffix.lower()`

### Common Failures

Symptom: 文件名里带路径后上传结果异常
Cause: 忘了用 `Path(file.filename).name` 做清理
Fix: 回到 `gateway_config_demo.py:118`
Verify: 返回值里的 `filename` 只剩文件名本身

Symptom: `.docx` 没有生成 `.md`
Cause: 后缀不在 `CONVERTIBLE_EXTENSIONS`
Fix: 检查 `gateway_config_demo.py:9`
Verify: 返回值里有 `markdown_file`

Symptom: 模型列表缺字段
Cause: `list_models()` 里没把该字段带出去
Fix: 检查 `gateway_config_demo.py:100-107`
Verify: JSON 里重新出现该字段

### State Inspection

- 用 `python -m pdb unit-2-gateway-config/main.py`
- 在 `gateway_config_demo.py:168` 后检查 `gateway.config.models`
- 运行结束后看 `unit-2-gateway-config/_demo_data/threads/thread-gateway/user-data/uploads/`

### Isolation Testing

- 只测模型列表：在 `run_demo()` 里临时删掉 `uploads = ...`
- 只测上传：直接在交互式 Python 里调用 `GatewayAPI(...).upload_files(...)`
- 想模拟危险文件名：把 `filename` 改成 `../../secret.txt`，确认最终被清洗成普通文件名
