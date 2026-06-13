from __future__ import annotations

import json

from memory_lifecycle_demo import run_demo


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
