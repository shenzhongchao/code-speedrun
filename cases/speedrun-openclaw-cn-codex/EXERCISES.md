# Exercises

## Unit 1

目标：增加一个普通问答 turn。  
修改文件：`unit-1-overall/index.js`。  
任务：新增一个不触发工具的 WebChat 场景。  
预期输出：Loop 只有 assistant stream，没有 tool stream。  
参考思路：请求文本避免出现“提醒”或 `remind`。

## Unit 2

目标：新增一种入口。  
修改文件：`unit-2-gateway-entry/entry.js`。  
任务：实现 `createDiscordChannel()`。  
预期输出：Discord message 规范化成 `agent:main:discord:<channelId>`。  
参考思路：复用 Slack 的 thread/session 设计。

## Unit 3

目标：改进 memory ranking。  
修改文件：`unit-3-session-context/session-context.js`。  
任务：给旧记忆增加时间衰减。  
预期输出：同分内容中较新的 entry 排在前面。  
参考思路：在 `rankMemory()` 中加入 `updatedAt` 权重。

## Unit 4

目标：实现 abort signal。  
修改文件：`unit-4-agent-loop/agent-loop.js`。  
任务：让 `submit(context, { signal })` 可以在 started 前取消。  
预期输出：`wait()` 返回 lifecycle error 或 aborted。  
参考思路：在 queued job 执行前检查 signal。

## Unit 5

目标：实现 `after_tool_call` 清洗。  
修改文件：`unit-5-tools-safety/tools-safety.js`。  
任务：把 tool result 中的 `secret` 字段删除。  
预期输出：最终返回不包含敏感字段。  
参考思路：在 hook 中返回替换后的 result。

## Unit 6

目标：新增 Discord formatter。  
修改文件：`unit-6-reply-delivery/reply-delivery.js`。  
任务：把 Discord group reply 增加 mention tag。  
预期输出：群内回复以 `<@userId>` 开头。  
参考思路：在 `formatForChannel()` 中处理 `source.from`。
