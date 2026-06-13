# Unit 6: Skills Prompt System

> **Motto**: *Skills are recipes the agent can open when needed*

## In Plain Language

DeerFlow 的 skills 不是“多几个工具按钮”。它更像一本工作流菜谱：agent 先在 prompt 里看到每本菜谱的名字、描述和位置，真的需要时才打开对应的 `SKILL.md`。这个单元教的就是：skills 怎样被扫描、启停状态怎样生效、最后怎样变成 `<skill_system>` prompt section。

## Background Knowledge

- **skill 像菜谱**：它告诉 agent 遇到某类任务时该怎么做，而不是直接执行动作。
- **front matter 像目录卡片**：`SKILL.md` 顶部的 `name` 和 `description` 用来生成 prompt 索引，正文不一开始全部塞进上下文。
- **enabled state 像开关面板**：Gateway 可以启停 skill，但 LangGraph 运行在另一个进程，所以状态要从配置文件重新读。
- **`.skill` archive 像安装包**：安装前要先解压到临时目录，确认里面真有合法 `SKILL.md`，再复制到 custom skills。

## Key Terminology

- **Skill**：按需加载的工作流说明书，真实代码在 `deerflow/skills/`
- **Front matter**：`SKILL.md` 顶部的元数据块
- **`<skill_system>`**：注入系统 prompt 的 skill 索引片段
- **Public skills**：项目自带 skills
- **Custom skills**：用户安装或自定义 skills
- **`.skill` archive**：用于安装 skill 的 ZIP 包

## What This Unit Does

这个单元保留了 skills 系统里四个最值得学的动作：

1. 扫描 `public` 和 `custom` 目录下的 `SKILL.md`
2. 解析 front matter，得到 `name / description / license`
3. 合并 `extensions_config.json` 里的启停状态
4. 生成只包含 enabled skills 的 `<skill_system>`
5. 演示把一个 `.skill` archive 安装到 custom 目录

学完这个单元，你应该能理解：为什么 DeerFlow 不把 skill 正文全塞进 prompt，而是先给 agent 一个轻量索引。

## Key Code Walkthrough

- `skills_prompt_demo.py:31`：`parse_skill_file()` 把 `SKILL.md` front matter 变成 `DemoSkill`。
- `skills_prompt_demo.py:78`：`list_demo_skills()` 每次扫描时重新读取 enabled state，模拟 Gateway 和 LangGraph 的进程边界。
- `skills_prompt_demo.py:110`：`build_skills_prompt_section()` 只输出 name、description 和 `/mnt/skills/.../SKILL.md` 位置。
- `skills_prompt_demo.py:133`：`_validate_archive_members()` 拒绝危险 archive member。
- `skills_prompt_demo.py:149`：`install_demo_skill_archive()` 先解压到临时目录，再复制到 `custom`。

## How to Run

```bash
cd cases/speedrun-deer-flow
python unit-6-skills-prompt-system/main.py
```

## Expected Output

你应该看到：

- `skills_before_install` 里有 `research` 和 disabled 的 `charting`
- `prompt_section` 里只出现 enabled 的 `research`
- skill 位置使用 `/mnt/skills/public/research/SKILL.md`
- `install_result.skill_name` 是 `table-maker`
- `skills_after_install` 里出现 `table-maker`

## Exercises

### Explain It Back

为什么 prompt 里只放 skill 的 `name / description / SKILL.md location`，而不是完整正文？

为什么 enabled state 放在 `extensions_config.json`，而不是写回 `SKILL.md`？

### Modify It

- 把 `_demo_data/extensions_config.json` 里的 `custom:charting` 改成 enabled，再观察 prompt 是否出现 charting。
- 新增一个 public skill 目录，写一个最小 `SKILL.md`，确认它会被扫描出来。

## Debug Guide

### Observation Points

File: `skills_prompt_demo.py:31`
What to observe: front matter 怎样变成 compact metadata
Breakpoint or log: 查看 `metadata`

File: `skills_prompt_demo.py:78`
What to observe: config 里的 enabled state 怎样覆盖默认值
Breakpoint or log: 查看 `enabled_state`

File: `skills_prompt_demo.py:110`
What to observe: prompt 为什么使用 `/mnt/skills/...`
Breakpoint or log: 查看 `skill.sandbox_skill_file`

File: `skills_prompt_demo.py:149`
What to observe: archive 安装为什么先进入临时目录
Breakpoint or log: 查看 `source_skill_dir`

### Common Failures

Symptom: skill 没出现在 prompt 里
Cause: skill 被 disabled，或者 `SKILL.md` 缺少 `name` / `description`
Fix: 检查 `SKILL.md` front matter 和 `extensions_config.json`
Verify: `prompt_section` 里重新出现该 skill

Symptom: archive 安装失败
Cause: ZIP 里没有合法 `SKILL.md` 根目录
Fix: 确保 archive 结构类似 `my-skill/SKILL.md`
Verify: `install_result.skill_name` 返回新 skill 名称

### State Inspection

- 用 `python -m pdb unit-6-skills-prompt-system/main.py`
- 在 `skills_prompt_demo.py:91` 后检查 `skills`
- 在 `skills_prompt_demo.py:116` 后检查 prompt lines
- 运行结束后看 `unit-6-skills-prompt-system/_demo_data/_runtime/skills/custom/`

### Isolation Testing

- 只测扫描：直接调用 `list_demo_skills(...)`
- 只测 prompt：直接调用 `build_skills_prompt_section(...)`
- 只测安装：手工构造 `.skill` ZIP 后调用 `install_demo_skill_archive(...)`
