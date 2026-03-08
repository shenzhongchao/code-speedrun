# Unit 8: Skills Engine — 技能安装、卸载与三方合并

## 用大白话说

这个单元就像一个"插件管理器"，但比普通插件系统复杂得多。想象你有一份食谱（源代码），不同的厨师（技能）要在上面做修改——有的加新配料（新文件），有的改烹饪步骤（修改现有文件）。Skills Engine 的工作是：安全地合并这些修改，确保不同厨师的改动不冲突，出问题时能一键回滚。

## 背景知识

NanoClaw 的核心哲学是"不加功能，加技能"。想要 Telegram 支持？不是往代码里加 if/else，而是运行 `/add-telegram` 技能，它会自动修改你的代码。这意味着每个用户的 NanoClaw 代码都不一样——是为自己定制的。

Skills Engine 是实现这个哲学的基础设施。它解决了几个难题：
1. **三方合并**: 技能修改的文件可能已经被其他技能或用户手动修改过，需要 `git merge-file` 做三方合并
2. **原子性**: 安装要么完全成功，要么完全回滚，不会留下半成品
3. **卸载**: 卸载一个技能时，需要从干净基线重新"回放"剩余技能
4. **漂移检测**: 检测文件是否被手动修改过（相对于基线的 hash 变化）

## 关键术语

- **Manifest（清单）**: `manifest.yaml`，声明技能添加哪些文件、修改哪些文件、依赖哪些其他技能
- **Base（基线）**: `.nanoclaw/base/` 目录，保存每个文件被技能修改前的"原始版本"
- **State（状态）**: `.nanoclaw/state.yaml`，记录已安装的技能、版本、文件哈希
- **三方合并 (Three-way Merge)**: `git merge-file current base skill`，用基线作为共同祖先合并当前文件和技能文件
- **Drift（漂移）**: 文件的当前内容与基线不一致，说明被手动修改过
- **Replay（回放）**: 卸载技能时，从基线开始重新按顺序应用剩余技能
- **Lock（锁）**: `.nanoclaw/lock` 文件，防止并发操作
- **Structured Operations**: 结构化操作，如合并 npm 依赖、.env 变量、docker-compose 服务

## 这个单元做了什么

模拟 Skills Engine 的完整生命周期：
1. 解析 manifest.yaml（技能清单）
2. 预检：版本兼容性、依赖、冲突
3. 备份 → 复制新文件 → 三方合并修改文件 → 结构化操作
4. 记录状态 → 运行测试 → 清理
5. 卸载：回放剩余技能

## 关键代码走读

### 安装流程 `applySkill()`
1. 读取 manifest → 检查系统版本、核心版本、依赖、冲突
2. 检测漂移（当前文件 vs 基线的 hash 差异）
3. 获取锁 → 创建备份
4. 执行 file_ops（重命名、删除、移动）
5. 复制 `add/` 目录下的新文件
6. 对 `modifies` 列表中的文件做三方合并
7. 合并 npm 依赖、.env、docker-compose
8. 运行 `npm install`、`post_apply` 命令、测试
9. 记录状态 → 清理备份
10. 任何步骤失败 → 回滚所有更改

### 三方合并
核心调用：`git merge-file current base skill`。`current` 是用户当前的文件，`base` 是技能修改前的原始版本，`skill` 是技能想要的版本。Git 会自动合并不冲突的部分，冲突的部分标记为 `<<<<<<<` / `=======` / `>>>>>>>`。

### 卸载流程 `uninstallSkill()`
不能简单地"撤销"一个技能的修改，因为后续技能可能依赖它的改动。正确做法：
1. 从基线开始
2. 按原始顺序重新应用除被卸载技能外的所有技能（replay）
3. 重新应用用户的自定义修改（custom patches）
4. 运行所有技能的测试

## 运行方式

```bash
npm run unit8
```

## 预期输出

```
--- 解析 Manifest ---
[manifest] 技能: add-telegram v1.0.0
[manifest] 核心版本要求: 1.1.0
[manifest] 新增文件: src/channels/telegram.ts
[manifest] 修改文件: src/index.ts, src/config.ts
[manifest] 依赖: (无)
[manifest] 冲突: add-signal
--- 预检 ---
[预检] 系统版本: ✅ 0.1.0 >= 0.1.0
[预检] 核心版本: ✅ 1.1.0 <= 1.1.3
[预检] 依赖检查: ✅ 无缺失
[预检] 冲突检查: ✅ add-signal 未安装
--- 漂移检测 ---
[漂移] src/index.ts: 无漂移 (hash 匹配)
[漂移] src/config.ts: ⚠️ 检测到漂移 (将使用三方合并)
--- 安装技能 ---
[备份] 已备份 3 个文件
[安装] 复制新文件: src/channels/telegram.ts
[合并] src/index.ts: 三方合并 ✅ 无冲突
[合并] src/config.ts: 三方合并 ✅ 无冲突 (漂移已自动合并)
[结构化] 合并 npm 依赖: telegraf@^4.0.0
[结构化] 合并 .env: TELEGRAM_BOT_TOKEN
[安装] npm install 完成
[状态] 记录技能: add-telegram v1.0.0, 3 个文件哈希
[备份] 已清理
[结果] ✅ 安装成功
--- 模拟卸载 ---
[卸载] 卸载技能: add-telegram
[卸载] 从基线恢复独占文件: src/channels/telegram.ts (删除)
[卸载] 回放剩余技能: add-slack
[卸载] 运行测试: add-slack ✅
[状态] 已更新
[结果] ✅ 卸载成功
--- 演示结束 ---
```

## 练习

1. **模拟合并冲突**: 修改 `simulateThreeWayMerge()` 让它返回冲突，观察回滚流程
2. **添加 `upgrade` 操作**: 实现技能升级——先卸载旧版本，再安装新版本
3. **用自己的话解释**: 为什么卸载技能不能简单地"撤销 diff"，而要从基线重新回放所有剩余技能？

## 调试指南

- **观察点**: 在 `applySkill()` 的 `catch` 块打断点，观察回滚如何恢复所有文件
- **常见问题**: 如果三方合并失败，检查 `.nanoclaw/base/` 下是否有正确的基线文件
- **状态检查**: 读取 `.nanoclaw/state.yaml`，确认 `applied_skills` 列表和 `file_hashes` 是否正确
