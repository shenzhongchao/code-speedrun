"""Run all learning units in order."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

UNITS = [
    "unit-2-message-bus/index.py",
    "unit-3-context-prompt/index.py",
    "unit-4-tool-execution-loop/index.py",
    "unit-5-cron-heartbeat/index.py",
    "unit-6-provider-tools/index.py",
    "unit-1-overall/index.py",
]


def main() -> int:
    for target in UNITS:
        print(f"\\n=== Running {target} ===")
        cmd = [sys.executable, str(ROOT / target)]
        result = subprocess.run(cmd, check=False)
        if result.returncode != 0:
            print(f"FAILED: {target}")
            return result.returncode
    print("\\nAll units completed successfully.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
