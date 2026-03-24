from __future__ import annotations

import json
from dataclasses import asdict, dataclass, replace
from pathlib import Path


@dataclass
class ThreadRuntime:
    thread_id: str
    workspace_path: str
    uploads_path: str
    outputs_path: str
    sandbox_id: str | None = None


class ThreadRuntimeManager:
    """A small copy of DeerFlow's idea that each thread owns its own file system slice."""

    def __init__(self, base_dir: Path, lazy_init: bool = True):
        self.base_dir = base_dir
        self.lazy_init = lazy_init

    def before_agent(self, thread_id: str) -> ThreadRuntime:
        runtime = self.plan(thread_id)
        # LEARN: "lazy_init" means "label the boxes first, open them later."
        # Some runs only need the planned paths, so DeerFlow can defer actual directory creation
        # until a tool truly needs the file system.
        if not self.lazy_init:
            self.ensure_thread_dirs(runtime)
        return runtime

    def plan(self, thread_id: str) -> ThreadRuntime:
        # LEARN: One thread id turns into one private file-system slice.
        # This is how DeerFlow prevents one conversation's uploads and outputs from bleeding into another.
        thread_root = self.base_dir / "threads" / thread_id / "user-data"
        return ThreadRuntime(
            thread_id=thread_id,
            workspace_path=str(thread_root / "workspace"),
            uploads_path=str(thread_root / "uploads"),
            outputs_path=str(thread_root / "outputs"),
        )

    def ensure_thread_dirs(self, runtime: ThreadRuntime) -> ThreadRuntime:
        for path in (runtime.workspace_path, runtime.uploads_path, runtime.outputs_path):
            Path(path).mkdir(parents=True, exist_ok=True)
        return runtime

    def attach_sandbox(self, runtime: ThreadRuntime, sandbox_id: str = "local") -> ThreadRuntime:
        return replace(runtime, sandbox_id=sandbox_id)

    def snapshot(self, runtime: ThreadRuntime) -> dict[str, object]:
        return {
            **asdict(runtime),
            "workspace_exists": Path(runtime.workspace_path).exists(),
            "uploads_exists": Path(runtime.uploads_path).exists(),
            "outputs_exists": Path(runtime.outputs_path).exists(),
        }


def tool_error_boundary(tool_name: str, callback) -> dict[str, str]:
    try:
        return {"status": "ok", "tool": tool_name, "content": str(callback())}
    except Exception as exc:  # noqa: BLE001 - this is a teaching copy of the middleware boundary
        # LEARN: Tool failures become data, not a full crash.
        # The real backend wraps exceptions into a structured tool message so the agent can
        # continue reasoning with the failure in context instead of losing the whole run.
        detail = str(exc).strip() or exc.__class__.__name__
        return {
            "status": "error",
            "tool": tool_name,
            "content": (
                f"Error: Tool '{tool_name}' failed with {exc.__class__.__name__}: {detail}. "
                "Continue with available context, or choose an alternative tool."
            ),
        }


def run_demo() -> dict[str, object]:
    base_dir = Path(__file__).resolve().parent / "_demo_data"

    # LEARN: Show both runtime modes side by side.
    # Comparing lazy and eager setup makes the file-system contract visible in one output.
    lazy_manager = ThreadRuntimeManager(base_dir=base_dir, lazy_init=True)
    eager_manager = ThreadRuntimeManager(base_dir=base_dir, lazy_init=False)

    lazy_runtime = lazy_manager.before_agent("thread-lazy")
    eager_runtime = eager_manager.before_agent("thread-eager")
    eager_runtime = eager_manager.attach_sandbox(eager_runtime)

    return {
        "lazy_runtime": lazy_manager.snapshot(lazy_runtime),
        "eager_runtime": eager_manager.snapshot(eager_runtime),
        "error_boundary": tool_error_boundary("read_file", lambda: 1 / 0),
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
