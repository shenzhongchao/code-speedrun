# Verification Checklist

Apply this checklist after structural verification and before handoff.

## Execution

- Every unit runs from the command written in its `README.md`.
- The root quick-start commands run from the documented working directory.
- Stubbed services or fixtures produce deterministic output.

## Architecture Integrity

- Unit 1 imports and orchestrates Units 2+ through real public APIs.
- Unit 1 does not fake subsystem flow with narration-only logging.
- Unit boundaries match the promised concepts in the learning-path table.

## Documentation Integrity

- Each unit `README.md` explains the extracted code, not the original codebase at full complexity.
- Every unit includes Key Terminology, runnable commands, expected output, exercises, and a Debug Guide.
- Cross-references between related units are accurate.

## Debugging

- `.vscode/launch.json` or the runtime-equivalent debug config points at real unit entry points.
- The debug instructions mention concrete files, commands, or breakpoints the learner can use.

## Simplifications

- `SIMPLIFICATIONS.md` covers every important stub, omitted dependency, removed layer, or simplified branch.
- Each simplification points back to the real implementation path in the original repo.

## Scope

- The chosen unit count is justified if it falls outside the default 4-8 range.
- Monorepo or partial-repo scope is stated explicitly in the root README.
