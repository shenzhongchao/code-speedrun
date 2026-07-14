# Code Speedrun

> Everything to Nano

把复杂代码库压缩成最小、可运行的学习单元。这里的 `Nano`，指的是你真的能跑起来、看明白、逐步展开的最小理解单位。

一个 AI skill，把任意代码库拆解为最小化、可独立运行的学习单元——通过跑代码来理解项目，而不是读代码。

## 为什么做这个

读代码很慢。读文档更慢。DeepWiki 之类的工具能生成详尽的代码库剖析，但被动地读大段文字几乎没有正反馈——不到十分钟就开始犯困。

真正让人"搞懂了"的时刻来自运行代码、观察结果。一个断点命中、一行日志打印、一个输出变化——这就是即时反馈，这才是让人保持专注的东西。

Code Speedrun 反转了学习路径：不再自上而下地阅读代码库，而是提取出一系列可以执行、修改、调试的小单元。Unit 1 用桩函数跑通完整主流程，几秒钟就能看到全貌。后续每个 unit 聚焦一个子系统。通过动手建立认知，而不是通过阅读。

## 工作方式

1. 指向一个 GitHub URL 或本地目录
2. 分析代码库，拆解为 4–8 个可运行的 unit
3. 每个 unit 是独立的迷你项目，有自己的入口文件、README 和调试配置
4. Unit 1 始终是端到端概览——用桩函数跑通完整主流程
5. Unit 2+ 逐个深入具体子系统（路由、存储、认证等）

产物结构：

```
speedrun-<repo-name>/
├── README.md                  # 学习路径和快速开始
├── package.json               # 共享依赖
├── .vscode/launch.json        # 所有 unit 的调试配置
├── unit-1-overall/            # 端到端主流程（桩函数）
│   ├── README.md
│   └── index.ts
├── unit-2-<slug>/             # 深入子系统 A
│   ├── README.md
│   └── ...
└── unit-N-<slug>/             # 深入子系统 N
    ├── README.md
    └── ...
```

## 核心设计决策

- **先跑后读** — 每个 unit 都有可执行的入口，在读任何一行解释之前就能跑起来
- **全景 → 聚焦** — Unit 1 建立全局心智模型，后续 unit 填充细节
- **费曼方法** — 所有讲解先用通俗类比，再叠加技术精度
- **调试友好** — 内置 VS Code launch 配置，每个 unit 都比原始代码库更容易调试
- **用自己的话说** — 每个 unit 包含"Explain It Back"练习，用自己的语言复述概念，暴露代码修改练习发现不了的理解盲区

## 使用方式

这是一个 [Claude Code](https://docs.anthropic.com/en/docs/claude-code) skill。使用方式：

将 .claude/skills/code-speedrun 目录复制到自己项目的 .claude/skills/ 或 ~/.claude/skills/ 中，打开claude

```
speedrun this codebase: https://github.com/user/repo
```

或指向本地目录：

```
break down ./my-project for learning
```

## 案例：Protenix（蛋白质结构预测）

[Protenix](https://github.com/bytedance/Protenix) 是一个类似 AlphaFold3 的蛋白质结构预测系统——约 5 万行 Python/PyTorch 代码，包含自定义 CUDA 算子、基于扩散模型的坐标生成、多链复合物处理等。

Code Speedrun 将其拆解为 7 个可运行的学习单元：

| 单元 | 主题 | 学到什么 |
|------|------|----------|
| 1 | 端到端总览 | 用桩函数跑通完整预测流程 |
| 2 | 数据管线 | 蛋白质序列 → Token → 特征张量 |
| 3 | 输入嵌入 | AtomAttentionEncoder + 相对位置编码 |
| 4 | Pairformer | 三角注意力 + 三角乘法更新 |
| 5 | 扩散模块 | 去噪扩散生成三维坐标 |
| 6 | 置信度与输出 | pLDDT/PAE/PTM 质量评估 |
| 7 | 训练流程 | 完整前向路径 + 损失函数 + 标签置换 + EMA |

每个单元用 `python unit-N-<slug>/main.py` 即可运行——不需要 GPU、不需要 50GB 模型权重、不需要下载数据库。生成的 `speedrun-Protenix/` 还包含一份[简化清单](Protenix/SIMPLIFICATIONS.md)，将每个简化点映射回原版源文件，方便借助 AI 编程工具逐步向原版扩展。

## 案例：DeerFlow（Super Agent 编排框架）

[DeerFlow](https://github.com/bytedance/deer-flow) 是一个开源的 super agent harness——不是聊天机器人 UI，也不是单轮问答 agent demo，而是一套把 LLM、工具调用、子代理、记忆、sandbox、skills 编排在一起的后端运行时。后端（Python/LangGraph）是大脑，Next.js 前端只是外表。

Code Speedrun 将后端拆解为 10 个可运行的学习单元：

| 单元 | 主题 | 学到什么 |
|------|------|----------|
| 1 | 后端主流程总览 | 用真实 import 串联 Unit 2-10，模拟一次完整请求 |
| 2 | Gateway 与配置 | FastAPI 边界处理模型列表、文件上传和配置驱动的 API |
| 3 | Thread 运行时 | 每个 thread 独立的主机路径、`/mnt/user-data` 虚拟路径和 sandbox 分配 |
| 4 | Lead Agent 工厂 | 将运行时参数翻译成模型、中间件、提示词和工具选择 |
| 5 | 工具与 Docker Sandbox | LangGraph 工具调用循环 + OpenAI 兼容 LLM + sandbox 执行 |
| 6 | Skills 提示词系统 | 扫描 skills、应用启用状态、注入紧凑的提示词索引 |
| 7 | Memory 生命周期 | 过滤对话、更新记忆 JSON、注入下一轮提示词上下文 |
| 8 | Subagent 委派 | 后台任务执行，带上过滤后的工具集和进度事件 |
| 9 | MCP 延迟工具 | 配置 mtime 缓存、延迟注册、`tool_search` 发现机制 |
| 10 | Artifact 与归档安全 | 线程作用域内的 artifact 服务与安全的 `.skill` 归档检查 |

Unit 1 用真实 import 串联全部 10 个单元，模拟一次后端请求和五条 secondary flow 摘要。跑完 speedrun 后，附带的[源码对照路径](cases/speedrun-deer-flow/ORIGINAL-READING-PATH.md)将每个单元映射回 DeerFlow 真实源文件——提供 90 分钟和 180 分钟两条路线，取决于你想挖多深。

## License

MIT
