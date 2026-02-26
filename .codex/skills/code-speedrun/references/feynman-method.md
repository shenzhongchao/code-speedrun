# Feynman Method for Code Explanation

Apply the Feynman learning technique when writing unit explanations, `// LEARN:` comments, and README walkthroughs. The core loop: explain simply → find gaps → simplify further.

## 1. Plain-Language-First Rule

Every concept explanation must start with a sentence a non-specialist can understand. Technical precision comes second.

**Bad:**
```
// LEARN: This implements the observer pattern via an event emitter
// that decouples producers from consumers using pub/sub semantics.
```

**Good:**
```
// LEARN: This is a notification system. When something interesting happens
// (e.g., a new message arrives), everyone who signed up to hear about it
// gets notified automatically — without the sender knowing who's listening.
// Pattern name: Observer / Pub-Sub.
```

## 2. Analogy Anchoring

Map abstract code concepts to concrete, everyday analogies. Place the analogy before the technical explanation.

Patterns:

| Code Concept | Analogy Style |
|---|---|
| Middleware pipeline | Assembly line — each station inspects/modifies the item, then passes it on |
| Event loop | A single waiter serving many tables — takes orders, delivers food, never idle |
| Connection pool | A taxi stand — reuse available cars instead of buying a new one per ride |
| Cache layer | A sticky note on your monitor — faster than opening the filing cabinet |
| Message queue | A post office — senders drop off letters, recipients pick up when ready |
| Dependency injection | A power outlet — the device doesn't care how electricity is generated, it just plugs in |
| State machine | A traffic light — fixed set of states, clear rules for transitions |

When no standard analogy fits, invent one. The analogy must:
- Map to something physical or experiential
- Preserve the key structural relationship (1:1, 1:many, sequential, etc.)
- Be stated in one sentence, with the mapping made explicit

Format: `"Think of X as Y — [mapping]. In code, this means Z."`

## 3. Gap Detection Prompts

In the **Exercises** section of each unit README, include at least one "Explain It Back" exercise:

```markdown
### Explain It Back
Explain [concept] to an imaginary colleague who has never seen this codebase.
Write 3–5 sentences in plain language. If you get stuck or resort to
hand-waving ("it just works"), that's a gap — re-read the relevant code
section and try again.
```

Variations:
- "Draw a diagram (boxes and arrows) of how data flows through this unit. Label each arrow with what gets passed."
- "Explain why [design decision] was chosen over [alternative]. If you can't articulate the trade-off, re-read [specific file]."
- "Describe what would break if you removed [component]. Trace the failure path."

## 4. Simplification Checkpoints

When writing the **Key Code Walkthrough** section, apply this self-test after each paragraph:

1. Could a junior developer follow this without Googling?
2. Did I use any term I haven't defined yet?
3. Can I cut this paragraph in half and keep the meaning?

If any answer is "no", rewrite before moving on.

## 5. `// LEARN:` Comment Structure

Use this three-layer format for inline comments at key code points:

```
// LEARN: [Analogy — one sentence, plain language]
// [What the code actually does — technical but concise]
// [Why — the design reason or trade-off]
```

Example:
```python
# LEARN: Think of this as a bouncer at a club — it checks every request
# before letting it through to the actual handler.
# Validates the auth token and attaches the user object to the request context.
# Why: Centralizes auth so individual routes don't repeat validation logic.
def auth_middleware(request, next_handler):
    ...
```

Not every `// LEARN:` comment needs all three layers. Use judgment:
- Simple lines: analogy + what (2 layers)
- Critical design decisions: all 3 layers
- Obvious code: skip the comment entirely
