#!/usr/bin/env python3

import argparse
import json
import re
import sys
from pathlib import Path


UNIT_PATTERN = re.compile(r"unit-(\d+)-(.+)")


def load_launch_json(path: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        errors.append("Missing .vscode/launch.json")
        return errors, warnings
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid .vscode/launch.json: {exc}")
        return errors, warnings

    if not isinstance(data.get("configurations"), list) or not data["configurations"]:
        errors.append(".vscode/launch.json has no configurations")
    return errors, warnings


def collect_units(root: Path) -> list[Path]:
    return sorted(
        [
            path
            for path in root.iterdir()
            if path.is_dir() and UNIT_PATTERN.fullmatch(path.name)
        ]
    )


def unit_has_code(unit_dir: Path) -> bool:
    for path in unit_dir.rglob("*"):
        if not path.is_file():
            continue
        if path.name == "README.md":
            continue
        return True
    return False


def unit_contains_sibling_references(unit_dir: Path, siblings: list[Path]) -> bool:
    searchable = []
    for path in unit_dir.rglob("*"):
        if path.is_file() and path.suffix in {
            ".ts",
            ".tsx",
            ".js",
            ".jsx",
            ".py",
            ".go",
            ".rs",
            ".java",
            ".kt",
            ".md",
        }:
            searchable.append(path)
    blob = "\n".join(path.read_text(encoding="utf-8", errors="ignore") for path in searchable)
    return any(sibling.name in blob for sibling in siblings)


def main() -> int:
    parser = argparse.ArgumentParser(description="Verify a generated speedrun directory.")
    parser.add_argument("speedrun_dir", help="Path to speedrun-<repo-name>")
    args = parser.parse_args()

    root = Path(args.speedrun_dir)
    errors: list[str] = []
    warnings: list[str] = []

    if not root.is_dir():
        print(f"ERROR: {root} is not a directory")
        return 1

    for required in ["README.md", "SIMPLIFICATIONS.md"]:
        if not (root / required).is_file():
            errors.append(f"Missing {required}")

    launch_errors, launch_warnings = load_launch_json(root / ".vscode" / "launch.json")
    errors.extend(launch_errors)
    warnings.extend(launch_warnings)

    units = collect_units(root)
    if not units:
        errors.append("No unit directories found")

    simplifications_text = ""
    simplifications_path = root / "SIMPLIFICATIONS.md"
    if simplifications_path.is_file():
        simplifications_text = simplifications_path.read_text(encoding="utf-8", errors="ignore")

    for unit in units:
        match = UNIT_PATTERN.fullmatch(unit.name)
        assert match is not None
        number = match.group(1)
        if not (unit / "README.md").is_file():
            errors.append(f"Missing README.md in {unit.name}")
        if not unit_has_code(unit):
            warnings.append(f"No code files found in {unit.name}")
        if f"## Unit {number}:" not in simplifications_text:
            warnings.append(f"SIMPLIFICATIONS.md has no section for {unit.name}")

    unit_one = next((unit for unit in units if unit.name.startswith("unit-1-")), None)
    if unit_one and len(units) > 1:
        siblings = [unit for unit in units if unit != unit_one]
        if not unit_contains_sibling_references(unit_one, siblings):
            warnings.append("Unit 1 does not appear to reference sibling units")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        for warning in warnings:
            print(f"WARNING: {warning}")
        return 1

    print("Speedrun structure looks valid.")
    for warning in warnings:
        print(f"WARNING: {warning}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
