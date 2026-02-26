# Debug Guide Template

Use this template for the "Debug Guide" section in each learning unit's README.md. Adapt to the unit's language and runtime.

## Structure

### 1. Observation Points

Identify 2–4 locations in the unit's code where the learner should place breakpoints or log statements to observe the core concept in action.

Format:

```
File: <filename>:<line>
What to observe: <what the variable/state reveals about the concept>
Breakpoint or log: <specific instruction>
```

Example (Node.js):

```
File: router.ts:45
What to observe: The incoming message object before routing decisions
Log: console.log('PRE-ROUTE:', JSON.stringify(msg, null, 2))
```

Example (Python):

```
File: handler.py:32
What to observe: The parsed request after middleware processing
Breakpoint: import pdb; pdb.set_trace()
```

### 2. Common Failures

List 3–5 failure modes the learner is likely to hit, with symptoms and fixes.

Format:

```
Symptom:  <what the learner sees>
Cause:    <why it happens>
Fix:      <exact steps to resolve>
Verify:   <how to confirm the fix worked>
```

Example:

```
Symptom:  "ECONNREFUSED 127.0.0.1:3000"
Cause:    The server from Unit 2 isn't running
Fix:      Start the server first: node unit-2-server/index.ts
Verify:   curl http://localhost:3000/health returns {"ok": true}
```

### 3. State Inspection

Show how to examine the runtime state relevant to this unit's concept.

Patterns by runtime:

**Node.js / TypeScript:**
- `node --inspect unit.ts` then open `chrome://inspect`
- Add `debugger;` statements at key points
- Use `console.table()` for array/object state

**Python:**
- `python -m pdb unit.py` for step-through debugging
- `python -i unit.py` for interactive post-run inspection
- `breakpoint()` (Python 3.7+) at key points

**General:**
- Environment variables: `printenv | grep RELEVANT_PREFIX`
- File state: `ls -la data/` or `cat state.json | jq .`
- Network: `curl -v http://localhost:PORT/endpoint`
- Database: show relevant query commands for the DB in use

### 4. Isolation Testing

Show how to test this unit's logic without the rest of the system.

Patterns:

**Mock external calls:**
```
// LEARN: This mock replaces the real API client.
// It returns a fixed response so we can test routing logic in isolation.
const mockClient = { send: async (msg) => ({ status: 'ok', id: '123' }) }
```

**Run a single function:**
```
// Add to bottom of file for quick testing:
if (require.main === module) {
  const result = processMessage({ text: 'hello', from: 'test-user' })
  console.log('Result:', result)
}
```

**Minimal test script:**
```bash
#!/bin/bash
# debug.sh — run this unit in isolation with verbose output
export DEBUG=1
export LOG_LEVEL=trace
node --inspect-brk index.ts
```

## VS Code launch.json Template

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug Unit N",
      "type": "node",
      "request": "launch",
      "program": "${workspaceFolder}/index.ts",
      "runtimeArgs": ["-r", "ts-node/register"],
      "env": { "DEBUG": "1" },
      "console": "integratedTerminal",
      "skipFiles": ["<node_internals>/**"]
    }
  ]
}
```

For Python units:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug Unit N",
      "type": "debugpy",
      "request": "launch",
      "program": "${workspaceFolder}/main.py",
      "console": "integratedTerminal",
      "justMyCode": true
    }
  ]
}
```

Adapt the template to the actual language and toolchain of the codebase being decomposed.
