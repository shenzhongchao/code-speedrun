#!/usr/bin/env python3

import argparse
import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Unit:
    number: int
    slug: str
    title: str
    motto: str
    concept: str


def parse_unit(raw: str) -> Unit:
    parts = raw.split("|")
    if len(parts) != 5:
        raise argparse.ArgumentTypeError(
            "--unit must be formatted as number|slug|title|motto|concept"
        )
    number = int(parts[0])
    return Unit(number=number, slug=parts[1], title=parts[2], motto=parts[3], concept=parts[4])


def launcher_for(runtime: str, unit: Unit) -> dict:
    if runtime == "python":
        return {
            "name": f"Unit {unit.number}: {unit.title}",
            "type": "debugpy",
            "request": "launch",
            "program": f"${{workspaceFolder}}/unit-{unit.number}-{unit.slug}/main.py",
            "console": "integratedTerminal",
            "justMyCode": True,
        }
    if runtime == "go":
        return {
            "name": f"Unit {unit.number}: {unit.title}",
            "type": "go",
            "request": "launch",
            "program": f"${{workspaceFolder}}/unit-{unit.number}-{unit.slug}",
        }
    if runtime == "rust":
        return {
            "name": f"Unit {unit.number}: {unit.title}",
            "type": "lldb",
            "request": "launch",
            "cargo": {
                "args": ["run", "--bin", f"unit-{unit.number}-{unit.slug}"],
                "filter": {"name": f"unit-{unit.number}-{unit.slug}", "kind": "bin"},
            },
            "cwd": "${workspaceFolder}",
        }
    return {
        "name": f"Unit {unit.number}: {unit.title}",
        "type": "node",
        "request": "launch",
        "program": f"${{workspaceFolder}}/unit-{unit.number}-{unit.slug}/index.ts",
        "runtimeArgs": ["-r", "ts-node/register"],
        "console": "integratedTerminal",
        "skipFiles": ["<node_internals>/**"],
    }


def current_file_launcher(runtime: str) -> dict:
    if runtime == "python":
        return {
            "name": "Run Current File",
            "type": "debugpy",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "justMyCode": True,
        }
    if runtime == "go":
        return {
            "name": "Run Current Package",
            "type": "go",
            "request": "launch",
            "program": "${fileDirname}",
        }
    if runtime == "rust":
        return {
            "name": "Run Current File",
            "type": "lldb",
            "request": "launch",
            "program": "${file}",
            "cwd": "${workspaceFolder}",
        }
    return {
        "name": "Run Current File",
        "type": "node",
        "request": "launch",
        "program": "${file}",
        "runtimeArgs": ["-r", "ts-node/register"],
        "console": "integratedTerminal",
        "skipFiles": ["<node_internals>/**"],
    }


def entry_filename(runtime: str) -> str:
    return {
        "python": "main.py",
        "go": "main.go",
        "rust": "main.rs",
    }.get(runtime, "index.ts")


def write_root_readme(path: Path, repo_name: str, units: list[Unit], source_url: str | None) -> None:
    lines = [f"# Speedrun: {repo_name}", ""]
    if source_url:
        lines.extend([f"> **Source**: [{repo_name}]({source_url})", ""])
    lines.extend(
        [
            "## What This Speedrun Covers",
            "[Describe the chosen scope here.]",
            "",
            "## Quick Start",
            "[Install command]",
            "[Run Unit 1]",
            "",
            "## Learning Path",
            "",
            "| Unit | Title | Motto | Concept |",
            "|------|-------|-------|---------|",
        ]
    )
    for unit in units:
        lines.append(
            f"| {unit.number} | {unit.title} | *{unit.motto}* | {unit.concept} |"
        )
    lines.extend(
        [
            "",
            "## Architecture At A Glance",
            "[Short diagram or bullets.]",
            "",
            "## Debugging",
            "[Explain how to use the root debug configuration.]",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_simplifications(path: Path, units: list[Unit]) -> None:
    lines = [
        "# Simplifications",
        "",
        "What was simplified or stubbed compared to the original codebase.",
        "",
    ]
    for unit in units:
        lines.extend(
            [
                f"## Unit {unit.number}: {unit.title}",
                "- [ ] [Describe a meaningful simplification and point to the original path]",
                "",
            ]
        )
    path.write_text("\n".join(lines), encoding="utf-8")


def write_unit_readme(path: Path, unit: Unit, entry_file: str) -> None:
    content = f"""# Unit {unit.number}: {unit.title}

> **Motto**: *{unit.motto}*

## In Plain Language
[Explain the concept in plain language.]

## Background Knowledge
[List the minimum concepts needed for this unit.]

## Key Terminology
- **Term**: [Definition]

## What This Unit Does
[Explain what this slice accomplishes.]

## Key Code Walkthrough
[Reference specific files and lines in this unit.]

## How to Run
[Exact command to run `{entry_file}`.]

## Expected Output
[Show what success looks like.]

## Exercises
### Explain It Back
[Ask the learner to explain the concept.]

### Modify It
- [Modification 1]
- [Modification 2]

## Debug Guide
[Fill this section using references/debug-guide.md.]
"""
    path.write_text(content, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Scaffold a speedrun directory skeleton.")
    parser.add_argument("output_dir", help="Directory to create, e.g. speedrun-my-repo")
    parser.add_argument("--repo-name", required=True, help="Source repository or project name")
    parser.add_argument(
        "--runtime",
        default="node",
        choices=["node", "python", "go", "rust"],
        help="Primary runtime used for entry files and launch.json",
    )
    parser.add_argument("--source-url", help="Optional remote source URL")
    parser.add_argument(
        "--unit",
        action="append",
        type=parse_unit,
        required=True,
        help="Unit metadata as number|slug|title|motto|concept",
    )
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    units = sorted(args.unit, key=lambda unit: unit.number)
    entry_file = entry_filename(args.runtime)

    vscode_dir = output_dir / ".vscode"
    vscode_dir.mkdir(exist_ok=True)
    launch = {
        "version": "0.2.0",
        "configurations": [launcher_for(args.runtime, unit) for unit in units]
        + [current_file_launcher(args.runtime)],
    }
    (vscode_dir / "launch.json").write_text(
        json.dumps(launch, indent=2) + "\n", encoding="utf-8"
    )

    write_root_readme(output_dir / "README.md", args.repo_name, units, args.source_url)
    write_simplifications(output_dir / "SIMPLIFICATIONS.md", units)

    for unit in units:
        unit_dir = output_dir / f"unit-{unit.number}-{unit.slug}"
        unit_dir.mkdir(exist_ok=True)
        write_unit_readme(unit_dir / "README.md", unit, entry_file)

    print(f"Scaffolded {output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
