# Unit 4: 容器运行器 — 容器挂载、进程生成与流式输出

## 用大白话说

这个单元就像一个"安全屋"管理员：每次有任务来了，管理员会准备一间隔离的房间（容器），把需要的文件搬进去（挂载），让工人（Claude 智能体）在里面干活，然后通过门缝传递结果（流式输出）。工人只能看到搬进去的文件，碰不到外面的东西。

## 背景知识

NanoClaw 的核心安全模型是**容器隔离**：Claude 智能体不是直接在你的电脑上运行，而是在 Docker 容器里运行。容器只能访问明确挂载进去的目录。这意味着即使智能体"想"做坏事，它也碰不到你的 SSH 密钥、浏览器密码等敏感文件。

**流式输出协议**: 容器通过 stdout 输出结果，使用特殊的标记对（`---NANOCLAW_OUTPUT_START---` 和 `---NANOCLAW_OUTPUT_END---`）包裹 JSON 数据。主进程实时解析这些标记，实现"边生成边发送"的效果。

## 关键术语

- **Volume Mount（卷挂载）**: 把宿主机的目录映射到容器内部，`-v /host/path:/container/path`
- **只读挂载 (ro)**: 容器只能读取，不能修改。用于保护源代码和全局配置
- **stdin 注入**: 通过标准输入传递密钥（API Key），避免写入磁盘或环境变量
- **Sentinel Marker（哨兵标记）**: 输出流中的特殊字符串，用于可靠地分割 JSON 数据块
- **Idle Timeout（空闲超时）**: 容器在最后一次输出后等待 30 分钟，期间可以接收新消息（IPC 管道）

## 这个单元做了什么

模拟容器运行器的核心逻辑：
1. 构建卷挂载列表（主群组 vs 普通群组的不同权限）
2. 生成 Docker 命令行参数
3. 模拟容器进程的生命周期
4. 解析流式输出中的哨兵标记
5. 超时管理和优雅停止

## 关键代码走读

### 挂载策略 `buildVolumeMounts()`
主群组（main）获得项目根目录的只读挂载 + 自己的群组文件夹读写挂载。普通群组只获得自己的文件夹 + 全局记忆目录（只读）。每个群组还有独立的 IPC 目录和 Claude 会话目录。

### 密钥安全
API Key 通过 `container.stdin.write(JSON.stringify(input))` 传入，然后立即从 `input` 对象中删除。这样密钥既不会出现在命令行参数中（`ps aux` 可见），也不会写入日志文件。

### 流式输出解析
容器的 stdout 是一个持续的字节流。解析器维护一个 `parseBuffer`，每次收到数据就追加进去，然后循环查找 `OUTPUT_START_MARKER` 和 `OUTPUT_END_MARKER` 对。找到完整的一对就提取中间的 JSON 并处理。

## 运行方式

```bash
npm run unit4
```

## 预期输出

```
--- 构建挂载列表 (主群组) ---
[挂载] /project -> /workspace/project (只读)
[挂载] /groups/main -> /workspace/group (读写)
[挂载] /sessions/main/.claude -> /home/node/.claude (读写)
[挂载] /ipc/main -> /workspace/ipc (读写)
[挂载] /sessions/main/agent-runner-src -> /app/src (读写)
--- 构建挂载列表 (普通群组) ---
[挂载] /groups/family -> /workspace/group (读写)
[挂载] /groups/global -> /workspace/global (只读)
[挂载] /sessions/family/.claude -> /home/node/.claude (读写)
[挂载] /ipc/family -> /workspace/ipc (读写)
[挂载] /sessions/family/agent-runner-src -> /app/src (读写)
--- 构建 Docker 命令 ---
[命令] docker run -i --rm --name nanoclaw-main-xxx -e TZ=Asia/Shanghai -v ... nanoclaw-agent:latest
--- 模拟容器执行 (流式输出) ---
[容器] 启动容器 nanoclaw-demo-xxx
[容器] 收到数据块...
[解析] 找到输出标记对，解析 JSON...
[输出] status=success, result="这是智能体的回复"
[输出] 新会话 ID: session-new-123
[容器] 容器退出，代码: 0，耗时: 205ms
--- 模拟超时场景 ---
[容器] 启动容器 nanoclaw-timeout-xxx
[容器] 超时！正在优雅停止...
[容器] 容器退出，代码: 137 (被杀)
--- 演示结束 ---
```

## 练习

1. **添加额外挂载**: 在 `buildVolumeMounts()` 中为主群组添加一个 `~/Documents` 的只读挂载
2. **实现输出大小限制**: 当 stdout 累积超过 10MB 时截断并记录警告（参考真实实现的 `CONTAINER_MAX_OUTPUT_SIZE`）
3. **用自己的话解释**: 为什么密钥通过 stdin 传递而不是环境变量？两种方式的安全差异是什么？

## 调试指南

- **观察点**: 在 `parseStreamOutput()` 的 `while` 循环中打断点，观察 `parseBuffer` 如何逐步积累和消费
- **常见问题**: 如果输出解析失败，检查 JSON 字符串中是否包含换行符（需要 `trim()`）
- **状态检查**: 打印 `mounts` 数组，确认每个挂载的 `hostPath`、`containerPath` 和 `readonly` 是否正确
