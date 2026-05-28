# Unit 3: Setup & Config

> **Motto**: *Install the working layer*

## In Plain Language
This unit shows why `omx setup` matters. OMX is useful only after it lays out prompts, skills, hooks, config, and `AGENTS.md` in places Codex can actually find.

## Background Knowledge
- **Installer as a moving crew**: The crew does not invent your furniture; it puts every item where it belongs. In technical terms, setup writes assets into a filesystem layout that later commands depend on.
- **Managed config as a reserved shelf**: You can keep your own books, but one shelf is reserved for house rules. In technical terms, OMX manages a few TOML keys while trying not to overwrite unrelated user settings.

## Key Terminology
- **Managed config**: The part of `config.toml` that OMX considers its responsibility.
- **Scope**: Whether setup writes into a project-local `.codex/` or a broader user location.
- **Asset**: A prompt, skill, template, or hook file copied into the target workspace.

## What This Unit Does
The unit builds a small managed TOML block, plans where setup should write files, and then writes a demo workspace that looks like a tiny OMX install. The output lets you inspect the exact files later commands expect.

## Key Code Walkthrough
`index.js:51-76` builds the managed TOML block. Notice the rule at `index.js:56`: the existing `model` is preserved unless an explicit override is provided. That mirrors the real repository's "edit only what OMX owns" approach.

`index.js:78-93` converts a logical setup scope into concrete filesystem paths. `index.js:100-140` then writes the config file, prompt files, skill files, hook file, and `AGENTS.md`. The comment at `index.js:124-126` is the key lesson: setup is a layout problem, not just a config problem.

The runnable demo at `index.js:143-157` wipes a local demo directory, performs setup, and prints the written files plus a config preview.

## How to Run
```bash
cd /root/key_projects/learn-codebase/speedrun-oh-my-codex
node unit-3-setup-config/index.js
```

## Expected Output
You should see a JSON object with `workspaceRoot`, `configPreview`, and `written`. The `written` array should include `.codex/config.toml`, at least two prompt files, two skill files, `.omx/hooks/notify-hook.js`, and `AGENTS.md`.

## Exercises
### Explain It Back
Explain why writing only `config.toml` would not be enough to make OMX feel installed.

### Modify It
- Add a third sample skill to `SAMPLE_SKILLS` and confirm the new `SKILL.md` appears in the output.
- Pass a custom `modelOverride` into `buildManagedConfig()` and verify the model line changes.

## Debug Guide
### Observation Points
File: `index.js:51`
What to observe: How OMX decides which `model` line to emit.
Breakpoint or log: Inspect `existingConfig`, `modelOverride`, and the final `model` value.

File: `index.js:78`
What to observe: The path planning step that decides where assets will land.
Breakpoint or log: Inspect the object returned by `planSetupInstall()`.

File: `index.js:100`
What to observe: The order in which files are written into the demo workspace.
Breakpoint or log: Step through `applySetup()` and inspect `written` after each push.

### Common Failures
Symptom: The config file is written to an unexpected path.
Cause: The setup scope changed from `project` to another value.
Fix: Pass `scope: "project"` when calling `applySetup()`.
Verify: Re-run and confirm the config path is under `.codex/config.toml`.

Symptom: The model line is missing.
Cause: `buildManagedConfig()` was changed so it no longer emits the `model` key.
Fix: Restore the `model = "${model}"` line in the managed config output.
Verify: Open the generated config file and confirm the key is present.

Symptom: `AGENTS.md` never appears.
Cause: The setup code stopped writing the template file.
Fix: Restore the `ensureTextFile(plan.agentsFile, SAMPLE_TEMPLATE_AGENTS)` call.
Verify: Re-run and confirm `AGENTS.md` is listed in `written`.

### State Inspection
- Inspect the config: `cat unit-3-setup-config/demo-workspace/.codex/config.toml`
- Inspect the installed assets: `find unit-3-setup-config/demo-workspace -maxdepth 4 -type f | sort`
- Inspect the setup summary: `cat unit-3-setup-config/demo-workspace/.omx/setup-summary.json`

### Isolation Testing
- Run `node --input-type=module -e "import { buildManagedConfig } from './unit-3-setup-config/index.js'; console.log(buildManagedConfig({ existingConfig: 'model = \"gpt-4.1\"' }))"` from the speedrun root.
- Delete one prompt entry from `SAMPLE_PROMPTS` and confirm the written file count changes.
- Use the `Unit 3: Setup & Config` VS Code launcher and stop inside `applySetup()`.
