# Unit 3: Setup 与 Config

> **口号**: *先把工作层装进去*

## 用大白话先讲
这个单元解释了为什么 `omx setup` 很重要。只有当 OMX 把 prompts、skills、hooks、config 和 `AGENTS.md` 放到 Codex 真能读取的位置时，它才算真正“装好了”。

## 背景知识
- **安装器像搬家团队**：他们不发明家具，只负责把东西摆到对的位置。技术上说，setup 会把资产写入后续命令依赖的文件系统布局。
- **受管配置像预留书架**：用户自己的书可以放，但其中有一层专门留给系统规则。技术上说，OMX 会管理一小部分 TOML key，同时尽量不覆盖用户自己的其他配置。

## 关键术语
- **受管配置**：`config.toml` 中被 OMX 视为自己负责维护的部分。
- **Scope**：setup 是写入项目本地 `.codex/`，还是写入更广泛的用户位置。
- **Asset**：被复制到目标 workspace 的 prompt、skill、template 或 hook 文件。

## 这个单元做了什么
这个单元会构建一个简化的受管 TOML 块，规划 setup 应该写入哪些路径，然后写出一个看起来像迷你版 OMX 安装结果的 demo workspace。它的输出可以让你直接检查后续命令实际依赖的文件。

## 关键代码走读
`index.js:51-76` 会构建受管 TOML 块。最关键的是 `index.js:56` 这条规则：除非显式 override，否则已有的 `model` 会被保留。这与原始仓库“只改 OMX 自己拥有的字段”的思路一致。

`index.js:78-93` 会把逻辑上的 setup scope 转成具体文件路径。接着 `index.js:100-140` 会写入 config、prompt 文件、skill 文件、hook 文件和 `AGENTS.md`。`index.js:124-126` 的注释就是这里最重要的结论：setup 首先是文件布局问题，而不只是 config 问题。

`index.js:143-157` 的 demo 会清空本地 demo 目录，执行 setup，再打印写入的文件和 config 预览。

## 运行方式
```bash
cd /root/key_projects/learn-codebase/speedrun-oh-my-codex
node unit-3-setup-config/index.js
```

## 预期输出
你应该看到一个 JSON，里面有 `workspaceRoot`、`configPreview` 和 `written`。`written` 数组里应该包含 `.codex/config.toml`、至少两个 prompt 文件、两个 skill 文件、`.omx/hooks/notify-hook.js` 和 `AGENTS.md`。

## 练习
### 用自己的话解释
为什么只写一个 `config.toml` 还不足以让 OMX 看起来像“已经安装完成”？

### 动手改
- 往 `SAMPLE_SKILLS` 里加第三个 skill，然后确认新的 `SKILL.md` 出现在输出中。
- 调用 `buildManagedConfig()` 时传入自定义 `modelOverride`，确认 model 行发生变化。

## 调试指南
### 观察点
文件：`index.js:51`
观察什么：OMX 如何决定写出哪一条 `model` 配置。
断点或日志：检查 `existingConfig`、`modelOverride` 和最终 `model` 值。

文件：`index.js:78`
观察什么：路径规划步骤如何决定资产写到哪里。
断点或日志：查看 `planSetupInstall()` 返回的对象。

文件：`index.js:100`
观察什么：文件是按什么顺序被写入 demo workspace 的。
断点或日志：单步 `applySetup()`，每次 push 后都查看 `written`。

### 常见故障
现象：config 文件写到了意料之外的位置。
原因：setup scope 被改成了 `project` 以外的值。
修复：调用 `applySetup()` 时传入 `scope: "project"`。
验证：重新运行，确认 config 路径位于 `.codex/config.toml`。

现象：model 行消失了。
原因：`buildManagedConfig()` 被改坏，不再输出 `model` key。
修复：恢复受管配置中的 `model = "${model}"` 行。
验证：打开生成后的 config 文件，确认这个 key 存在。

现象：`AGENTS.md` 没有出现。
原因：setup 代码不再写 template 文件。
修复：恢复 `ensureTextFile(plan.agentsFile, SAMPLE_TEMPLATE_AGENTS)` 调用。
验证：重新运行，确认 `AGENTS.md` 出现在 `written` 数组中。

### 状态检查
- 查看 config：`cat unit-3-setup-config/demo-workspace/.codex/config.toml`
- 查看安装出来的资产：`find unit-3-setup-config/demo-workspace -maxdepth 4 -type f | sort`
- 查看 setup summary：`cat unit-3-setup-config/demo-workspace/.omx/setup-summary.json`

### 隔离测试
- 在 speedrun 根目录运行：`node --input-type=module -e "import { buildManagedConfig } from './unit-3-setup-config/index.js'; console.log(buildManagedConfig({ existingConfig: 'model = \"gpt-4.1\"' }))"`
- 从 `SAMPLE_PROMPTS` 里删掉一个条目，确认写入文件数量发生变化。
- 用 VS Code 的 `Unit 3: Setup & Config` 启动项停在 `applySetup()` 内部。
