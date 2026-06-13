# Real Sandbox Flow

这份文档把 DeerFlow 真实环境里的 sandbox 执行链路串起来。Unit 5 的代码是教学压缩版，但它保留的核心契约和真实后端一致：真实文件在宿主机，模型只看 `/mnt/user-data/...` 虚拟路径，危险动作在 sandbox 边界里执行。

## One-Line Flow

```text
用户上传
  -> Gateway 保存到 thread user-data/uploads
  -> Agent runtime 准备 thread user-data
  -> Sandbox 挂载 user-data 到 /mnt/user-data
  -> Model 发起 tool call
  -> Tool 在 sandbox 内执行
  -> 输出写入 /mnt/user-data/outputs
  -> Artifact API 安全解析并返回文件
```

## Step By Step

### 1. 用户上传文件

前端把文件发到 Gateway API。Gateway 不把文件字节直接塞进 prompt，而是保存到当前 thread 的宿主机目录：

```text
<base>/threads/thread-007/user-data/uploads/brief.docx
```

同时 Gateway 返回一个 agent 可见的虚拟路径：

```text
/mnt/user-data/uploads/brief.docx
```

如果上传文件可以转换成 Markdown，真实后端还会生成类似：

```text
/mnt/user-data/uploads/brief.md
```

### 2. 请求进入 agent runtime

LangGraph 收到用户请求和 `thread_id=thread-007`。Thread runtime 根据这个 `thread_id` 准备当前对话独有的目录：

```text
threads/thread-007/user-data/workspace
threads/thread-007/user-data/uploads
threads/thread-007/user-data/outputs
```

这一步的意义是把一次对话的文件系统边界先固定下来。后面的工具、sandbox、artifact API 都围绕同一个 `user-data` 目录工作。

### 3. sandbox 被创建或复用

后端创建或复用一个 sandbox。以 Docker 形态理解，就是把当前 thread 的宿主机 `user-data` 挂载进容器：

```bash
docker run \
  -v <base>/threads/thread-007/user-data:/mnt/user-data \
  -w /mnt/user-data/workspace \
  ...
```

容器内部能看到：

```text
/mnt/user-data/uploads/brief.docx
/mnt/user-data/workspace/
/mnt/user-data/outputs/
```

它看不到宿主机任意目录。模型和工具都应该使用 `/mnt/user-data/...` 这套路径语言。

### 4. lead agent 被装配

`make_lead_agent()` 会根据配置和 runtime flags 组装 agent：

```text
model
system prompt
skills prompt
memory context
middleware
tools: bash, read_file, write_file, present_file, task, ...
```

prompt 会告诉模型：

```text
Uploaded files are in /mnt/user-data/uploads
Temporary work goes in /mnt/user-data/workspace
Final outputs go in /mnt/user-data/outputs
```

模型不需要知道宿主机真实路径，也不应该知道。

### 5. 模型决定调用工具

用户可能说：

```text
总结我上传的 brief.docx，生成 report.txt
```

模型不会直接读写文件。它只会产生一个 tool call，例如：

```json
{
  "name": "bash",
  "args": {
    "command": "cat /mnt/user-data/uploads/brief.md > /mnt/user-data/outputs/report.txt"
  }
}
```

这个 tool call 是一张工单，不是已经执行过的动作。

### 6. 工具进入 sandbox 执行

工具层拿到 tool call 后，把命令交给 sandbox 执行。因为 sandbox 已经挂载了：

```text
host:      <base>/threads/thread-007/user-data
container: /mnt/user-data
```

所以容器里写入：

```text
/mnt/user-data/outputs/report.txt
```

宿主机上实际出现：

```text
<base>/threads/thread-007/user-data/outputs/report.txt
```

这就是 `/mnt/user-data` virtual path 和 host path 的对应关系。

### 7. 工具结果回到模型

sandbox 返回 stdout、stderr 和 exit code。LangGraph 把结果包装成 `ToolMessage`，再交还给模型：

```text
Tool bash returned: report.txt created
```

模型基于这个工具结果继续推理，最后回复用户。

### 8. 前端下载 artifact

最终文件通常放在：

```text
/mnt/user-data/outputs/report.txt
```

模型或工具可以通过 `present_file` 把它呈现给前端。Gateway artifact API 再把这个虚拟路径解析回宿主机路径：

```text
<base>/threads/thread-007/user-data/outputs/report.txt
```

artifact API 会检查路径是否仍在当前 thread 的 `user-data` 下，拒绝路径穿越或任意 host path，然后把文件返回给前端。

## Why Sandbox Matters

sandbox 的意义不是“为了演示 Docker”，而是把模型的意图和真实机器隔开：

- 模型只能使用 `/mnt/user-data/...` 路径，不能随便访问宿主机。
- `bash` 这类危险动作在受控环境里执行，不直接跑在主进程里。
- 每个 thread 有自己的 `workspace / uploads / outputs`，文件不会混到别的对话里。
- 后端可以替换 sandbox 实现，而 prompt 和工具参数仍然保持同一套虚拟路径契约。

## Where Unit 5 Compresses Reality

Unit 5 现在保留了真实流程的几个关键中转层：

```text
LangGraph tool node
  -> dispatch_runtime_tool()
  -> ensure_sandbox_initialized(runtime)
  -> validate/resolve path if local sandbox
  -> sandbox.read_file / sandbox.write_file / sandbox.execute_command
```

`build_tool_runtime()` 模拟真实 `ToolRuntime` 里的两类状态：

```text
runtime.context: thread_id, sandbox_id
runtime.state: sandbox state, thread_data, directory-created flag
```

Unit 5 的 `DockerSandbox.execute_command()` 展示真实 Docker mount 的形状：

```text
<host user-data>:/mnt/user-data
```

Unit 5 的 runtime tool 层则把工具参数里的虚拟路径映射回宿主机路径，用于 local sandbox 下的 `read_file` / `write_file`：

```text
/mnt/user-data/outputs/result.txt
  -> <host user-data>/outputs/result.txt
```

它同时拒绝这些不安全路径：

```text
/etc/passwd
/workspace/input.txt
/mnt/user-data/../secret.txt
```

`DockerSandbox.virtual_to_host()` 仍然保留，用来解释 Docker mount 下同一份文件如何在 host 和 `/mnt/user-data` 之间对应；真实同构流程的重点则在 `read_file_runtime_tool()`、`write_file_runtime_tool()` 和 `bash_runtime_tool()`。

所以 runtime tool 层负责路径翻译和边界检查；sandbox 是真实执行边界。两者一起构成 Unit 5 想讲的核心：模型提出动作，后端在受控文件系统里执行动作。
