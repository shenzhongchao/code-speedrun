# Architecture

## Full Link

```text
Telegram / Slack / WebChat / Node
        |
        v
Gateway normalize
  -> envelope(runId, sessionKey, idempotencyKey, source)
        |
        v
Session Context
  -> agent scope
  -> bootstrap files
  -> memory recall
  -> session history
  -> skills
  -> system prompt
        |
        v
Agent Loop
  accepted -> queued -> started -> tool_running -> streaming -> ended
                                      |
                                      v
                                    error
        |
        v
Reply Delivery
  shape -> dedupe -> format -> chunk -> retry -> transport
```

## Assistant Turn Sequence

```text
channel event
  Gateway.receiveChannelMessage()
  prepareRunContext()
  runtime.submit()
  lifecycle: accepted
  lifecycle: queued
  lifecycle: start
  tool: start/end
  assistant: delta...
  lifecycle: end
  deliverRunResult()
```

## Tool Safety Layers

```text
Skill discovery
  -> Prompt exposure
  -> Hook pipeline
  -> Tool policy
  -> Sandbox / workspace boundary
  -> Tool execution
```

## Reply Delivery Data Flow

```text
payloads
  -> filter reasoning/silent
  -> suppress NO_REPLY
  -> preserve channel source fields
  -> chunk long text
  -> retry transport
  -> dead-letter on final failure
```
