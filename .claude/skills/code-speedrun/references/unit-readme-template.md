# Unit README Template

Use this template when writing `unit-N-<slug>/README.md`. Keep the final README specific to the actual unit; do not leave placeholder language in place.

```markdown
# Unit N: [Title]

> **Motto**: *[Short memorable phrase]*

## In Plain Language
[Explain the concept in 1-2 sentences a non-specialist could follow.]

## Background Knowledge
[List only the minimum concepts needed for this unit.
Start each concept with a plain-language analogy, then add technical precision.]

## Key Terminology
- **Term**: Plain-language definition and why it matters here.
- **Abbreviation (Full Name)**: Meaning and role in this unit.

## What This Unit Does
[Explain what this slice accomplishes and why it exists.]

## Key Code Walkthrough
[Walk the learner through the important files and code paths.
Reference concrete files and lines inside the speedrun unit.
Explain non-obvious tradeoffs.]

## How to Run
[Exact commands.]

## Expected Output
[Show what success looks like.]

## Exercises
### Explain It Back
[Ask the learner to explain the concept in their own words.]

### Modify It
- [Small targeted modification.]
- [Second targeted modification.]

## Debug Guide
[Use references/debug-guide.md to fill this section.]
```

Checklist before finishing the README:

- Open with plain language before jargon.
- Define every specialized term before using it.
- Keep the walkthrough anchored to the extracted code, not the original repository.
- Include exact commands, not vague instructions.
- Include at least one Explain-It-Back exercise.
