from __future__ import annotations

import argparse
import json

from tools_sandbox_demo import run_demo


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--live",
        action="store_true",
        help="Use a real OpenAI-compatible LLM and Docker sandbox.",
    )
    args = parser.parse_args()
    print(json.dumps(run_demo(live=args.live), indent=2))
