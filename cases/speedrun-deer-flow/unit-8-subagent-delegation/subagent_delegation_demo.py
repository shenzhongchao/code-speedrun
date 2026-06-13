from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


CURRENT_DIR = Path(__file__).resolve().parent


@dataclass
class ParentContext:
    thread_id: str
    sandbox_id: str
    workspace_path: str
    uploads_path: str
    outputs_path: str
    parent_model: str
    trace_id: str


@dataclass
class SubagentConfig:
    name: str
    description: str
    system_prompt: str
    tools: list[str] | None
    disallowed_tools: list[str]
    model: str
    max_turns: int
    timeout_seconds: int


@dataclass
class TaskCall:
    description: str
    prompt: str
    subagent_type: str
    tool_call_id: str


@dataclass
class TaskEvent:
    type: str
    task_id: str
    message: object


class SubagentExecutor:
    def __init__(self, *, config: SubagentConfig, available_tools: list[str], parent_context: ParentContext):
        self.config = config
        self.available_tools = available_tools
        self.parent_context = parent_context
        self.background_tasks: dict[str, dict[str, object]] = {}

    @property
    def subagent_tools(self) -> list[str]:
        tools = self.available_tools
        if self.config.tools is not None:
            allowed = set(self.config.tools)
            tools = [tool for tool in tools if tool in allowed]
        disallowed = set(self.config.disallowed_tools)
        # LEARN: A subagent inherits useful tools, but not `task`; otherwise a
        # delegated worker could recursively launch more workers without bound.
        return [tool for tool in tools if tool not in disallowed]

    def build_runtime_snapshot(self, task_call: TaskCall) -> dict[str, object]:
        return {
            "thread_id": self.parent_context.thread_id,
            "sandbox_id": self.parent_context.sandbox_id,
            "workspace_path": self.parent_context.workspace_path,
            "parent_model": self.parent_context.parent_model,
            "trace_id": self.parent_context.trace_id,
            "subagent_type": task_call.subagent_type,
            "tool_call_id": task_call.tool_call_id,
        }

    def build_initial_state(self, task_call: TaskCall) -> dict[str, object]:
        # LEARN: The child agent starts with one HumanMessage: the delegated
        # prompt. It gets thread_data/sandbox handles, not the parent's whole
        # chat transcript. That is the context isolation benefit.
        return {
            "messages": [{"role": "human", "content": task_call.prompt}],
            "sandbox": {"sandbox_id": self.parent_context.sandbox_id},
            "thread_data": {
                "workspace_path": "/mnt/user-data/workspace",
                "uploads_path": "/mnt/user-data/uploads",
                "outputs_path": "/mnt/user-data/outputs",
            },
        }

    def execute_async(self, task_call: TaskCall) -> str:
        task_id = task_call.tool_call_id
        self.background_tasks[task_id] = {
            "status": "pending",
            "result": None,
            "events": [],
            "tools": self.subagent_tools,
            "initial_state": self.build_initial_state(task_call),
        }
        return task_id

    def poll_until_done(self, task_id: str, task_call: TaskCall) -> str:
        # LEARN: The real task tool starts execution in a background pool, then
        # polls the background store and streams events to the frontend. This
        # demo advances those states deterministically so each transition is visible.
        task = self.background_tasks[task_id]
        events: list[TaskEvent] = [
            TaskEvent("task_started", task_id, {"description": task_call.description}),
        ]
        task["status"] = "running"
        events.append(
            TaskEvent(
                "task_running",
                task_id,
                {
                    "message_index": 1,
                    "content": "Reading /mnt/user-data/workspace and ignoring parent-only chatter.",
                },
            )
        )
        task["status"] = "completed"
        workspace_files = self.inspect_workspace_files()
        result = f"Workspace contains {', '.join(workspace_files)}. The useful handoff is to summarize /mnt/user-data/workspace/notes/research.md for the parent."
        events.append(TaskEvent("task_completed", task_id, {"result": result}))
        task["result"] = result
        task["events"] = events
        return f"Task Succeeded. Result: {result}"

    def inspect_workspace_files(self) -> list[str]:
        # LEARN: Real subagents read `/mnt/user-data/workspace` through sandbox
        # tools. This demo reads the mounted host directory and reports virtual
        # relative paths so the visible contract stays the same.
        workspace = Path(self.parent_context.workspace_path)
        files = []
        for path in workspace.rglob("*"):
            relative_path = path.relative_to(workspace)
            if not path.is_file() or any(part.startswith(".") for part in relative_path.parts):
                continue
            files.append(relative_path.as_posix())
        return sorted(files)

    def execute(self, prompt: str) -> str:
        task_call = TaskCall(
            description="manual task",
            prompt=prompt,
            subagent_type=self.config.name,
            tool_call_id=f"task-{len(self.background_tasks) + 1}",
        )
        task_id = self.execute_async(task_call)
        self.poll_until_done(task_id, task_call)
        return task_id

    def delegate(self, task_call: TaskCall) -> dict[str, object]:
        runtime_snapshot = self.build_runtime_snapshot(task_call)
        task_id = self.execute_async(task_call)
        initial_state = self.background_tasks[task_id]["initial_state"]
        tool_result = self.poll_until_done(task_id, task_call)
        self.background_tasks[task_id] = {
            **self.background_tasks[task_id],
            "status": "completed",
        }
        return {
            "task_id": task_id,
            "runtime_snapshot": runtime_snapshot,
            "initial_state": initial_state,
            "tool_result": tool_result,
        }

    def cleanup_terminal_tasks(self) -> None:
        # LEARN: Completed background records must be removed; otherwise a long
        # running server accumulates per-task state forever.
        terminal = {"completed", "failed", "timed_out"}
        for task_id, task in list(self.background_tasks.items()):
            if task["status"] in terminal:
                del self.background_tasks[task_id]

    def events_for(self, task_id: str) -> list[TaskEvent]:
        return list(self.background_tasks[task_id]["events"])


def build_parent_context(base_dir: Path) -> ParentContext:
    thread_root = base_dir / "thread-subagent" / "user-data"
    workspace = thread_root / "workspace"
    uploads = thread_root / "uploads"
    outputs = thread_root / "outputs"
    workspace.mkdir(parents=True, exist_ok=True)
    uploads.mkdir(parents=True, exist_ok=True)
    outputs.mkdir(parents=True, exist_ok=True)
    (workspace / "README.md").write_text("# Demo workspace\n\nThis file is visible to both parent and subagent.\n", encoding="utf-8")
    notes_dir = workspace / "notes"
    notes_dir.mkdir(exist_ok=True)
    (notes_dir / "research.md").write_text("Research notes that should be summarized by the parent.\n", encoding="utf-8")
    # LEARN: The child shares thread/sandbox state, but receives a clean task
    # prompt instead of the parent's full conversation history.
    return ParentContext(
        thread_id="thread-subagent",
        sandbox_id="sandbox-thread-subagent",
        workspace_path=str(workspace),
        uploads_path=str(uploads),
        outputs_path=str(outputs),
        parent_model="gpt-5-responses",
        trace_id="trace-subagent",
    )


def build_general_purpose_config() -> SubagentConfig:
    return SubagentConfig(
        name="general-purpose",
        description="Use for multi-step work that benefits from isolated context.",
        system_prompt=(
            "You are a delegated subagent. Complete the focused task and return "
            "a concise result with useful file paths."
        ),
        tools=None,
        disallowed_tools=["task", "ask_clarification", "present_files"],
        model="inherit",
        max_turns=50,
        timeout_seconds=900,
    )


def plan_parent_delegation(user_request: str, *, max_concurrent_subagents: int = 3) -> dict[str, Any]:
    # LEARN: The parent agent should only delegate when work can be separated
    # into focused subtasks. This example has one delegated exploration task and
    # leaves final synthesis with the parent.
    task_calls = [
        TaskCall(
            description="inspect workspace",
            prompt=(
                "Inspect /mnt/user-data/workspace for useful project files. "
                "Return concise findings and mention only paths the parent can use."
            ),
            subagent_type="general-purpose",
            tool_call_id="call-inspect-workspace",
        )
    ]
    return {
        "user_request": user_request,
        "reason": "Workspace inspection may produce noisy file-reading context, so delegate it.",
        "max_concurrent_subagents": max_concurrent_subagents,
        "task_calls": [asdict(task_call) for task_call in task_calls],
        "_task_call_objects": task_calls,
    }


def synthesize_parent_answer(user_request: str, tool_result: str) -> str:
    # LEARN: The parent keeps responsibility for the final answer. The subagent
    # result is evidence it can use, not a replacement for parent reasoning.
    return f"Parent answer: For '{user_request}', I used the workspace subagent result: {tool_result}"


def run_subagent_demo(*, base_dir: Path | None = None) -> dict[str, object]:
    base_dir = base_dir or (CURRENT_DIR / "_demo_data")
    parent_context = build_parent_context(base_dir)
    parent_decision = plan_parent_delegation("Summarize what is useful in this workspace.")
    task_call = parent_decision["_task_call_objects"][0]
    executor = SubagentExecutor(
        config=build_general_purpose_config(),
        available_tools=["bash", "read_file", "write_file", "task"],
        parent_context=parent_context,
    )
    delegation = executor.delegate(task_call)
    task_id = delegation["task_id"]
    events = [asdict(event) for event in executor.events_for(task_id)]
    tool_result = str(delegation["tool_result"])
    parent_final_answer = synthesize_parent_answer(parent_decision["user_request"], tool_result)
    executor.cleanup_terminal_tasks()
    visible_parent_decision = {key: value for key, value in parent_decision.items() if not key.startswith("_")}
    return {
        "parent_context": asdict(parent_context),
        "parent_decision": visible_parent_decision,
        "runtime_snapshot": delegation["runtime_snapshot"],
        "subagent_tools": executor.subagent_tools,
        "subagent_initial_state": delegation["initial_state"],
        "events": events,
        "tool_result_for_parent": tool_result,
        "parent_final_answer": parent_final_answer,
        "background_tasks_after_cleanup": list(executor.background_tasks),
    }


def run_demo() -> dict[str, object]:
    return run_subagent_demo()
