# Unit 10: Artifacts and Archive Safety

> **Motto**: *Outputs are useful only if serving them is safe*

## In Plain Language

Agent 生成的文件只有能安全交给用户，才算真正有用。DeerFlow 的 artifact endpoint 不能让请求随便指定 host path，也不能信任 `.skill` ZIP 里的文件名。这个单元教的是：artifact virtual path 怎样映射回当前 thread 的输出目录，以及 skill archive 为什么也要做路径穿越、symlink 和大小检查。

## Background Knowledge

- **artifact 像交付物**：agent 最终产物应该放在 `/mnt/user-data/outputs`，前端再通过 Gateway 下载或预览。
- **virtual path 像取件编号**：请求里传的是 `/mnt/user-data/...`，后端根据 `thread_id` 找到真实文件。
- **MIME decision 像分拣规则**：HTML、纯文本、二进制文件返回方式不同。
- **ZIP member 像不可信输入**：ZIP 里的文件名也可能是 `../evil.txt` 或 symlink。
- **zip bomb 像压缩陷阱**：压缩包很小，解压后可能非常大，所以要按 uncompressed size 计数。

## Key Terminology

- **Artifact API**：按 thread 和 virtual path 返回生成文件的 Gateway endpoint
- **Virtual path resolver**：把 `/mnt/user-data/...` 映射到当前 thread host path 的逻辑
- **`.skill` archive**：本质是 ZIP 包，用于安装或预览 skill
- **Path traversal**：通过 `..` 或绝对路径逃出允许目录
- **Symlink member**：ZIP 内部伪装成文件的符号链接条目

## What This Unit Does

这个单元保留了 artifact 和 archive safety 里五个关键动作：

1. 把 artifact virtual path 解析到 thread-scoped host path
2. 按 MIME/content 判断 HTML、text、binary response kind
3. 从 `.skill` archive 里读取 `SKILL.md`
4. 拒绝 `../evil.txt`、绝对路径和 symlink member
5. 按 total uncompressed size 拒绝过大的 archive

学完这个单元，你应该能理解：为什么“下载一个文件”也必须经过后端路径安全边界。

## Key Code Walkthrough

- `artifacts_archive_safety_demo.py:24`：`_resolve_virtual_path()` 只允许当前 thread 的 `/mnt/user-data/...`。
- `artifacts_archive_safety_demo.py:59`：`resolve_demo_artifact()` 判断 HTML、text 和 binary response kind。
- `artifacts_archive_safety_demo.py:96`：`_is_symlink_member()` 识别 ZIP 里的 symlink。
- `artifacts_archive_safety_demo.py:104`：`validate_archive_members()` 检查 traversal、symlink 和 uncompressed size。
- `artifacts_archive_safety_demo.py:128`：`inspect_skill_archive()` 支持读取 archive 内的 `SKILL.md`。

## How to Run

```bash
cd cases/speedrun-deer-flow
python unit-10-artifacts-archive-safety/main.py
```

## Expected Output

你应该看到：

- `html_artifact.response_kind` 是 `html`
- `text_artifact.response_kind` 是 `text`
- `skill_archive.found` 是 `true`
- `skill_archive.internal_path` 指向 `SKILL.md`
- `unsafe_archive_error` 说明危险 member 被拒绝

## Exercises

### Explain It Back

为什么 artifact API 要通过 `thread_id + virtual_path` 解析文件，而不是直接接受 host 绝对路径？

为什么 `.skill` 文件本身在 outputs 目录里，也不能信任 ZIP 内部 member path？

### Modify It

- 在 outputs 目录加一个二进制文件，确认 `response_kind` 变成 `binary`。
- 构造一个带绝对路径 member 的 ZIP，确认 `validate_archive_members()` 会拒绝。

## Debug Guide

### Observation Points

File: `artifacts_archive_safety_demo.py:24`
What to observe: virtual path 如何被限制在当前 thread `user-data`
Breakpoint or log: 查看 `root` 和 `actual_path`

File: `artifacts_archive_safety_demo.py:59`
What to observe: MIME 和内容检测怎样决定 response kind
Breakpoint or log: 查看 `media_type`

File: `artifacts_archive_safety_demo.py:104`
What to observe: ZIP member path 怎样被判定 unsafe
Breakpoint or log: 查看 `info.filename`

File: `artifacts_archive_safety_demo.py:121`
What to observe: uncompressed size 怎样累加
Breakpoint or log: 查看 `total_size`

### Common Failures

Symptom: 合法 artifact 找不到
Cause: virtual path 没有映射到指定 `thread_id` 的目录下
Fix: 检查 `_resolve_virtual_path()` 返回的 host path
Verify: `actual_path.exists()` 为 true

Symptom: archive inspection 返回 `found: false`
Cause: archive 里没有 `SKILL.md`，或 internal path 不匹配
Fix: 列出 ZIP members，传入正确 internal path
Verify: `skill_archive.found` 是 true

### State Inspection

- 用 `python -m pdb unit-10-artifacts-archive-safety/main.py`
- 在 `artifacts_archive_safety_demo.py:170` 后检查 safe 和 unsafe archive 路径
- 在 `artifacts_archive_safety_demo.py:177` 后检查 artifact response
- 运行结束后看 `unit-10-artifacts-archive-safety/_demo_data/threads/thread-artifact/user-data/outputs/`

### Isolation Testing

- 只测 path resolver：直接调用 `resolve_demo_artifact(...)`
- 只测 ZIP 校验：构造临时 ZIP 后调用 `validate_archive_members(...)`
- 只测 archive 读取：调用 `inspect_skill_archive(archive_path, "SKILL.md")`
