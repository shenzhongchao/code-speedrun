from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Annotated, Any, Callable, Protocol, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


VIRTUAL_USER_DATA_ROOT = "/mnt/user-data"
VIRTUAL_SKILLS_ROOT = "/mnt/skills"
SYSTEM_PATH_PREFIXES = ("/bin/", "/usr/bin/", "/usr/sbin/", "/sbin/", "/dev/")
ABSOLUTE_PATH_PATTERN = re.compile(r"(?<![:\w])/(?:[^\s\"'`;&|<>()]+)")


@dataclass
class ResolvedTool:
    name: str
    source: str


@dataclass
class CompletedSandboxProcess:
    stdout: str
    stderr: str
    returncode: int


class SandboxProtocol(Protocol):
    id: str

    def execute_command(self, command: str) -> str:
        ...

    def read_file(self, path: str) -> str:
        ...

    def write_file(self, path: str, content: str, append: bool = False) -> None:
        ...


@dataclass
class ThreadData:
    workspace_path: str
    uploads_path: str
    outputs_path: str


@dataclass
class TeachingToolRuntime:
    """Small stand-in for LangChain ToolRuntime + DeerFlow ThreadState."""

    context: dict[str, Any]
    state: dict[str, Any]
    provider: "TeachingSandboxProvider"


@dataclass
class TeachingSandboxProvider:
    sandboxes: dict[str, SandboxProtocol] = field(default_factory=dict)

    def register(self, sandbox: SandboxProtocol) -> None:
        self.sandboxes[sandbox.id] = sandbox

    def get(self, sandbox_id: str) -> SandboxProtocol | None:
        return self.sandboxes.get(sandbox_id)

    def acquire(self, thread_id: str) -> str:
        # LEARN: The real provider can start/reuse containers. This teaching
        # provider keeps that same acquire/get shape without managing processes.
        sandbox_id = f"local-{thread_id}"
        if sandbox_id not in self.sandboxes:
            self.register(LocalSandbox(sandbox_id))
        return sandbox_id


@dataclass
class OpenAICompatibleConfig:
    model: str
    base_url: str
    api_key: str
    temperature: float = 0

    @classmethod
    def from_env(cls) -> "OpenAICompatibleConfig":
        missing = [
            name
            for name in ("OPENAI_API_KEY", "OPENAI_BASE_URL", "OPENAI_MODEL")
            if not os.environ.get(name)
        ]
        if missing:
            raise RuntimeError(
                "Live LLM mode needs these environment variables: "
                + ", ".join(missing)
            )
        return cls(
            model=os.environ["OPENAI_MODEL"],
            base_url=os.environ["OPENAI_BASE_URL"],
            api_key=os.environ["OPENAI_API_KEY"],
            temperature=float(os.environ.get("OPENAI_TEMPERATURE", "0")),
        )

    def to_chat_openai_kwargs(self) -> dict[str, object]:
        # LEARN: OpenAI-compatible providers are mostly "OpenAI shape + different URL".
        # DeerFlow's real model factory keeps `base_url`, `api_key`, and provider model id
        # in config, then passes them into ChatOpenAI.
        return {
            "model": self.model,
            "base_url": self.base_url,
            "api_key": self.api_key,
            "temperature": self.temperature,
        }


class LocalSandbox:
    """A tiny local sandbox matching DeerFlow's main teaching shape."""

    def __init__(self, sandbox_id: str):
        self.id = sandbox_id

    @staticmethod
    def _get_shell() -> str:
        # LEARN: The sandbox chooses the first usable shell instead of assuming one exists.
        # That fallback chain makes command execution more portable across environments.
        for shell in ("/bin/zsh", "/bin/bash", "/bin/sh"):
            if os.path.isfile(shell) and os.access(shell, os.X_OK):
                return shell
        shell_from_path = shutil.which("sh")
        if shell_from_path is None:
            raise RuntimeError("No suitable shell executable found.")
        return shell_from_path

    def execute_command(self, command: str) -> str:
        result = subprocess.run(
            command,
            executable=self._get_shell(),
            shell=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        # LEARN: Turn raw process results into one text payload.
        # This mirrors the real sandbox boundary: the agent receives stdout/stderr/exit status
        # in a single readable result instead of juggling subprocess objects.
        return _format_process_result(
            CompletedSandboxProcess(
                stdout=result.stdout,
                stderr=result.stderr,
                returncode=result.returncode,
            )
        )

    def read_file(self, path: str) -> str:
        return Path(path).read_text(encoding="utf-8")

    def write_file(self, path: str, content: str, append: bool = False) -> None:
        target = Path(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with target.open(mode, encoding="utf-8") as handle:
            handle.write(content)


class DockerSandbox:
    """Run tool commands in a short-lived Docker container."""

    def __init__(
        self,
        sandbox_id: str,
        user_data_root: str | Path,
        *,
        image: str = "python:3.12-slim",
        runner: Callable[..., CompletedSandboxProcess] | None = None,
    ):
        self.id = sandbox_id
        self.user_data_root = Path(user_data_root)
        self.image = image
        self._runner = runner or self._subprocess_runner
        for dirname in ("workspace", "uploads", "outputs"):
            (self.user_data_root / dirname).mkdir(parents=True, exist_ok=True)

    @staticmethod
    def _subprocess_runner(command: list[str], **kwargs: object) -> CompletedSandboxProcess:
        result = subprocess.run(command, capture_output=True, text=True, timeout=60, **kwargs)
        return CompletedSandboxProcess(
            stdout=result.stdout,
            stderr=result.stderr,
            returncode=result.returncode,
        )

    def execute_command(self, command: str) -> str:
        docker_command = self._docker_command(command)
        # LEARN: The model asks for "bash", but Docker is the safety boundary.
        # The tool converts a plain shell string into `docker run -v <host>:/mnt/user-data ...`.
        # That makes DeerFlow's virtual paths point at the same files inside and outside Docker.
        return _format_process_result(self._runner(docker_command))

    def _docker_command(self, command: str) -> list[str]:
        return [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{self.user_data_root}:/mnt/user-data",
            "-w",
            "/mnt/user-data/workspace",
            self.image,
            "/bin/sh",
            "-lc",
            command,
        ]

    def read_file(self, path: str) -> str:
        return self.virtual_to_host(path).read_text(encoding="utf-8")

    def write_file(self, path: str, content: str, append: bool = False) -> None:
        target = self.virtual_to_host(path)
        target.parent.mkdir(parents=True, exist_ok=True)
        mode = "a" if append else "w"
        with target.open(mode, encoding="utf-8") as handle:
            handle.write(content)

    def virtual_to_host(self, path: str) -> Path:
        normalized = path.replace("\\", "/")
        if normalized == VIRTUAL_USER_DATA_ROOT:
            return self.user_data_root
        if not normalized.startswith(f"{VIRTUAL_USER_DATA_ROOT}/"):
            raise ValueError(f"Sandbox path must start with {VIRTUAL_USER_DATA_ROOT}: {path}")
        relative = Path(normalized[len(VIRTUAL_USER_DATA_ROOT) :].lstrip("/"))
        if ".." in relative.parts:
            raise ValueError("Sandbox paths may not contain '..'")
        return self.user_data_root / relative


class ToolRegistry:
    def __init__(self, config_tools: list[object]):
        self.config_tools = config_tools
        self.builtin_tools = ["present_file", "ask_clarification"]
        self.subagent_tools = ["task"]
        self.mcp_tools = ["github.search_issues", "filesystem.read_dir"]

    def resolve_tools(
        self,
        *,
        model_supports_vision: bool,
        subagent_enabled: bool,
        include_mcp: bool = True,
        tool_search_enabled: bool = True,
    ) -> list[ResolvedTool]:
        # LEARN: The visible tool list is assembled from several sources.
        # Think of this as packing a toolbox for one job: config tools are the base kit,
        # runtime flags add special attachments such as subagents, vision, and MCP search.
        resolved = [ResolvedTool(name=self._tool_name(tool), source="config") for tool in self.config_tools]
        resolved.extend(ResolvedTool(name=name, source="builtin") for name in self.builtin_tools)
        if subagent_enabled:
            resolved.extend(ResolvedTool(name=name, source="builtin") for name in self.subagent_tools)
        if model_supports_vision:
            resolved.append(ResolvedTool(name="view_image", source="builtin"))
        if include_mcp:
            resolved.extend(ResolvedTool(name=name, source="mcp") for name in self.mcp_tools)
            if tool_search_enabled:
                resolved.append(ResolvedTool(name="tool_search", source="builtin"))
        return resolved

    @staticmethod
    def _tool_name(tool: object) -> str:
        return getattr(tool, "name", str(tool))


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    tool_trace: list[dict[str, object]]


class ScriptedToolCallingModel:
    """A deterministic teaching model used for tests and offline demos."""

    def __init__(self, tool_name: str, tool_args: dict[str, object], final_text: str):
        self.tool_name = tool_name
        self.tool_args = tool_args
        self.final_text = final_text

    def bind_tools(self, tools: list[object]) -> "ScriptedToolCallingModel":
        return self

    def invoke(self, messages: list[BaseMessage]) -> AIMessage:
        # LEARN: Real models decide tool calls from the prompt. This scripted model
        # makes the same shape deterministic: first response is a tool call, second
        # response is the final answer after it sees a ToolMessage.
        if any(isinstance(message, ToolMessage) for message in messages):
            return AIMessage(content=self.final_text)
        return AIMessage(
            content="",
            tool_calls=[
                {
                    "name": self.tool_name,
                    "args": self.tool_args,
                    "id": "call_sandbox_1",
                }
            ],
        )


def build_tool_registry(config_tools: list[object]) -> ToolRegistry:
    return ToolRegistry(config_tools=config_tools)


def build_tool_runtime(
    *,
    thread_id: str,
    sandbox: SandboxProtocol,
    user_data_root: str | Path,
    sandbox_mode: str = "container",
) -> TeachingToolRuntime:
    user_data_root = Path(user_data_root)
    thread_data = ThreadData(
        workspace_path=str(user_data_root / "workspace"),
        uploads_path=str(user_data_root / "uploads"),
        outputs_path=str(user_data_root / "outputs"),
    )
    provider = TeachingSandboxProvider()
    provider.register(sandbox)
    return TeachingToolRuntime(
        context={"thread_id": thread_id, "sandbox_id": sandbox.id},
        state={
            "sandbox": {"sandbox_id": sandbox.id, "mode": sandbox_mode},
            "thread_data": asdict(thread_data),
            "thread_directories_created": False,
        },
        provider=provider,
    )


def build_openai_compatible_model(config: OpenAICompatibleConfig):
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(**config.to_chat_openai_kwargs())


def run_langgraph_sandbox_demo(
    *,
    prompt: str,
    sandbox: SandboxProtocol,
    model: object,
    runtime: TeachingToolRuntime | None = None,
) -> dict[str, object]:
    runtime = runtime or build_tool_runtime(
        thread_id="thread-langgraph",
        sandbox=sandbox,
        user_data_root=getattr(sandbox, "user_data_root", Path.cwd()),
        sandbox_mode="container" if isinstance(sandbox, DockerSandbox) else "local",
    )
    tools = _make_sandbox_tools(runtime)
    model_with_tools = model.bind_tools(tools) if hasattr(model, "bind_tools") else model

    def call_model(state: AgentState) -> dict[str, list[BaseMessage]]:
        # LEARN: This is DeerFlow's lead-agent idea in miniature.
        # A LangGraph node receives conversation state, asks the model what to do next,
        # and stores the AIMessage back into the graph state.
        response = model_with_tools.invoke(state["messages"])
        return {"messages": [response]}

    def call_tools(state: AgentState) -> dict[str, object]:
        last_message = state["messages"][-1]
        tool_messages: list[ToolMessage] = []
        trace = list(state.get("tool_trace", []))
        for tool_call in getattr(last_message, "tool_calls", []):
            result = dispatch_runtime_tool(runtime, tool_call["name"], tool_call["args"])
            trace.append(
                {
                    "tool": tool_call["name"],
                    "args": dict(tool_call["args"]),
                    "output": result,
                }
            )
            tool_messages.append(
                ToolMessage(
                    content=result,
                    name=tool_call["name"],
                    tool_call_id=tool_call["id"],
                )
            )
        # LEARN: Tool output goes back into the message list as a ToolMessage.
        # That is the loop: model proposes an action, tools do the action, model sees the result.
        return {"messages": tool_messages, "tool_trace": trace}

    def next_step(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if getattr(last_message, "tool_calls", []):
            return "tools"
        return END

    graph = StateGraph(AgentState)
    graph.add_node("model", call_model)
    graph.add_node("tools", call_tools)
    graph.add_edge(START, "model")
    graph.add_conditional_edges("model", next_step, {"tools": "tools", END: END})
    graph.add_edge("tools", "model")
    app = graph.compile()

    result = app.invoke({"messages": [HumanMessage(content=prompt)], "tool_trace": []})
    return {
        "final_message": _last_ai_text(result["messages"]),
        "tool_trace": result["tool_trace"],
        "messages": [_message_summary(message) for message in result["messages"]],
    }


def run_live_langgraph_sandbox_demo() -> dict[str, object]:
    base_dir = Path(__file__).resolve().parent / "_demo_data" / "docker-thread" / "user-data"
    shutil.rmtree(base_dir, ignore_errors=True)

    model = build_openai_compatible_model(OpenAICompatibleConfig.from_env())
    sandbox = DockerSandbox(
        sandbox_id="docker-live",
        user_data_root=base_dir,
        image=os.environ.get("DEERFLOW_SPEEDRUN_DOCKER_IMAGE", "python:3.12-slim"),
    )
    prompt = (
        "Use the bash tool exactly once. Create /mnt/user-data/outputs/result.txt with the text "
        "'LANGGRAPH_SANDBOX_OK', then read the file back and answer with the content."
    )
    runtime = build_tool_runtime(
        thread_id="docker-thread",
        sandbox=sandbox,
        user_data_root=base_dir,
        sandbox_mode="container",
    )
    return run_langgraph_sandbox_demo(prompt=prompt, sandbox=sandbox, model=model, runtime=runtime)


def run_demo(*, live: bool = False) -> dict[str, object]:
    registry = build_tool_registry(
        config_tools=[
            type("Tool", (), {"name": "bash"})(),
            type("Tool", (), {"name": "read_file"})(),
            type("Tool", (), {"name": "write_file"})(),
            type("Tool", (), {"name": "web_search"})(),
        ]
    )

    if live:
        agent_result = run_live_langgraph_sandbox_demo()
        mode = "live-openai-compatible-docker"
    else:
        base_dir = Path(__file__).resolve().parent / "_demo_data" / "local-thread" / "user-data"
        shutil.rmtree(base_dir, ignore_errors=True)
        sandbox = LocalSandbox("local-scripted")
        runtime = build_tool_runtime(
            thread_id="local-thread",
            sandbox=sandbox,
            user_data_root=base_dir,
            sandbox_mode="local",
        )
        model = ScriptedToolCallingModel(
            tool_name="bash",
            tool_args={
                "command": (
                    "printf 'LANGGRAPH_SANDBOX_OK\\n' "
                    "> /mnt/user-data/outputs/result.txt && "
                    "cat /mnt/user-data/outputs/result.txt"
                )
            },
            final_text="LANGGRAPH_SANDBOX_OK",
        )
        agent_result = run_langgraph_sandbox_demo(
            prompt="Write and verify a tiny result inside the sandbox.",
            sandbox=sandbox,
            model=model,
            runtime=runtime,
        )
        mode = "offline-scripted-langgraph"

    return {
        "mode": mode,
        "tools": [asdict(tool) for tool in registry.resolve_tools(model_supports_vision=True, subagent_enabled=True)],
        "agent": agent_result,
    }


def _make_sandbox_tools(runtime: TeachingToolRuntime) -> list[object]:
    @tool
    def bash(command: str) -> str:
        """Run a shell command inside the sandbox."""
        return dispatch_runtime_tool(runtime, "bash", {"command": command})

    @tool
    def read_file(path: str) -> str:
        """Read a text file from the sandbox workspace."""
        return dispatch_runtime_tool(runtime, "read_file", {"path": path})

    @tool
    def write_file(path: str, content: str, append: bool = False) -> str:
        """Write text into a sandbox file."""
        return dispatch_runtime_tool(
            runtime,
            "write_file",
            {"path": path, "content": content, "append": append},
        )

    return [bash, read_file, write_file]


def dispatch_runtime_tool(runtime: TeachingToolRuntime, name: str, args: dict[str, Any]) -> str:
    if name == "bash":
        return bash_runtime_tool(runtime, str(args["command"]))
    if name == "read_file":
        return read_file_runtime_tool(runtime, str(args["path"]))
    if name == "write_file":
        return write_file_runtime_tool(
            runtime,
            str(args["path"]),
            str(args["content"]),
            append=bool(args.get("append", False)),
        )
    return f"Unknown tool: {name}"


def bash_runtime_tool(runtime: TeachingToolRuntime, command: str) -> str:
    try:
        sandbox = ensure_sandbox_initialized(runtime)
        ensure_thread_directories_exist(runtime)
        if is_local_sandbox(runtime):
            thread_data = get_thread_data(runtime)
            validate_local_bash_command_paths(command, thread_data)
            command = replace_virtual_paths_in_command(command, thread_data)
            return mask_local_paths_in_output(sandbox.execute_command(command), thread_data)
        return sandbox.execute_command(command)
    except PermissionError as error:
        return f"Error: {error}"
    except Exception as error:
        return f"Error: Unexpected error executing command: {error}"


def read_file_runtime_tool(runtime: TeachingToolRuntime, path: str) -> str:
    requested_path = path
    try:
        sandbox = ensure_sandbox_initialized(runtime)
        ensure_thread_directories_exist(runtime)
        if is_local_sandbox(runtime):
            thread_data = get_thread_data(runtime)
            validate_local_tool_path(path, thread_data, read_only=True)
            if is_skills_path(path):
                path = resolve_skills_path(path)
            else:
                path = resolve_and_validate_user_data_path(path, thread_data)
        content = sandbox.read_file(path)
        return content or "(empty)"
    except FileNotFoundError:
        return f"Error: File not found: {requested_path}"
    except PermissionError:
        return f"Error: Permission denied reading file: {requested_path}"
    except IsADirectoryError:
        return f"Error: Path is a directory, not a file: {requested_path}"
    except Exception as error:
        return f"Error: Unexpected error reading file: {error}"


def write_file_runtime_tool(
    runtime: TeachingToolRuntime,
    path: str,
    content: str,
    append: bool = False,
) -> str:
    requested_path = path
    try:
        sandbox = ensure_sandbox_initialized(runtime)
        ensure_thread_directories_exist(runtime)
        if is_local_sandbox(runtime):
            thread_data = get_thread_data(runtime)
            validate_local_tool_path(path, thread_data)
            path = resolve_and_validate_user_data_path(path, thread_data)
        sandbox.write_file(path, content, append=append)
        return "OK"
    except PermissionError:
        return f"Error: Permission denied writing to file: {requested_path}"
    except IsADirectoryError:
        return f"Error: Path is a directory, not a file: {requested_path}"
    except Exception as error:
        return f"Error: Unexpected error writing file: {error}"


def ensure_sandbox_initialized(runtime: TeachingToolRuntime) -> SandboxProtocol:
    sandbox_state = runtime.state.get("sandbox")
    sandbox_id = sandbox_state.get("sandbox_id") if sandbox_state else None
    if sandbox_id is not None:
        sandbox = runtime.provider.get(sandbox_id)
        if sandbox is not None:
            runtime.context["sandbox_id"] = sandbox_id
            return sandbox
    thread_id = str(runtime.context["thread_id"])
    sandbox_id = runtime.provider.acquire(thread_id)
    runtime.state["sandbox"] = {"sandbox_id": sandbox_id, "mode": "local"}
    runtime.context["sandbox_id"] = sandbox_id
    sandbox = runtime.provider.get(sandbox_id)
    if sandbox is None:
        raise RuntimeError(f"Sandbox not found after acquire: {sandbox_id}")
    return sandbox


def ensure_thread_directories_exist(runtime: TeachingToolRuntime) -> None:
    if not is_local_sandbox(runtime) or runtime.state.get("thread_directories_created"):
        return
    thread_data = get_thread_data(runtime)
    for key in ("workspace_path", "uploads_path", "outputs_path"):
        Path(thread_data[key]).mkdir(parents=True, exist_ok=True)
    runtime.state["thread_directories_created"] = True


def get_thread_data(runtime: TeachingToolRuntime) -> dict[str, str]:
    thread_data = runtime.state.get("thread_data")
    if not thread_data:
        raise RuntimeError("Thread data not available for local sandbox")
    return thread_data


def is_local_sandbox(runtime: TeachingToolRuntime) -> bool:
    sandbox_state = runtime.state.get("sandbox") or {}
    return sandbox_state.get("mode") == "local" or sandbox_state.get("sandbox_id") == "local"


def validate_local_tool_path(
    path: str,
    thread_data: dict[str, str],
    *,
    read_only: bool = False,
) -> None:
    reject_path_traversal(path)
    if is_skills_path(path):
        if not read_only:
            raise PermissionError(f"Write access to skills path is not allowed: {path}")
        return
    if path == VIRTUAL_USER_DATA_ROOT or path.startswith(f"{VIRTUAL_USER_DATA_ROOT}/"):
        return
    raise PermissionError(f"Only paths under {VIRTUAL_USER_DATA_ROOT}/ are allowed")


def validate_local_bash_command_paths(command: str, thread_data: dict[str, str]) -> None:
    unsafe_paths: list[str] = []
    for absolute_path in ABSOLUTE_PATH_PATTERN.findall(command):
        if absolute_path == VIRTUAL_USER_DATA_ROOT or absolute_path.startswith(f"{VIRTUAL_USER_DATA_ROOT}/"):
            reject_path_traversal(absolute_path)
            continue
        if is_skills_path(absolute_path):
            reject_path_traversal(absolute_path)
            continue
        if any(
            absolute_path == prefix.rstrip("/") or absolute_path.startswith(prefix)
            for prefix in SYSTEM_PATH_PREFIXES
        ):
            continue
        unsafe_paths.append(absolute_path)
    if unsafe_paths:
        unsafe = ", ".join(sorted(dict.fromkeys(unsafe_paths)))
        raise PermissionError(f"Unsafe absolute paths in command: {unsafe}. Use paths under {VIRTUAL_USER_DATA_ROOT}")


def replace_virtual_paths_in_command(command: str, thread_data: dict[str, str]) -> str:
    result = command
    if VIRTUAL_USER_DATA_ROOT in result:
        pattern = re.compile(rf"{re.escape(VIRTUAL_USER_DATA_ROOT)}(/[^\s\"';&|<>()]*)?")

        def replace_match(match: re.Match) -> str:
            return replace_virtual_path(match.group(0), thread_data)

        result = pattern.sub(replace_match, result)
    return result


def replace_virtual_path(path: str, thread_data: dict[str, str]) -> str:
    mappings = thread_virtual_to_actual_mappings(thread_data)
    normalized = path.replace("\\", "/")
    for virtual_base, actual_base in sorted(mappings.items(), key=lambda item: len(item[0]), reverse=True):
        if normalized == virtual_base:
            return actual_base
        if normalized.startswith(f"{virtual_base}/"):
            rest = normalized[len(virtual_base) :].lstrip("/")
            return str(Path(actual_base) / rest)
    return path


def thread_virtual_to_actual_mappings(thread_data: dict[str, str]) -> dict[str, str]:
    mappings = {
        f"{VIRTUAL_USER_DATA_ROOT}/workspace": thread_data["workspace_path"],
        f"{VIRTUAL_USER_DATA_ROOT}/uploads": thread_data["uploads_path"],
        f"{VIRTUAL_USER_DATA_ROOT}/outputs": thread_data["outputs_path"],
    }
    parent = str(Path(thread_data["workspace_path"]).parent)
    if all(str(Path(thread_data[key]).parent) == parent for key in ("uploads_path", "outputs_path")):
        mappings[VIRTUAL_USER_DATA_ROOT] = parent
    return mappings


def resolve_and_validate_user_data_path(path: str, thread_data: dict[str, str]) -> str:
    resolved = Path(replace_virtual_path(path, thread_data)).resolve()
    allowed_roots = [
        Path(thread_data[key]).resolve()
        for key in ("workspace_path", "uploads_path", "outputs_path")
    ]
    for root in allowed_roots:
        try:
            resolved.relative_to(root)
            return str(resolved)
        except ValueError:
            continue
    raise PermissionError("Access denied: path traversal detected")


def reject_path_traversal(path: str) -> None:
    if ".." in Path(path.replace("\\", "/")).parts:
        raise PermissionError("Access denied: path traversal detected")


def is_skills_path(path: str) -> bool:
    return path == VIRTUAL_SKILLS_ROOT or path.startswith(f"{VIRTUAL_SKILLS_ROOT}/")


def resolve_skills_path(path: str) -> str:
    raise FileNotFoundError(f"Skills directory is not mounted in this Unit 5 demo: {path}")


def mask_local_paths_in_output(output: str, thread_data: dict[str, str]) -> str:
    result = output
    for virtual_base, actual_base in sorted(thread_virtual_to_actual_mappings(thread_data).items(), key=lambda item: len(item[1]), reverse=True):
        actual = str(Path(actual_base))
        resolved = str(Path(actual_base).resolve())
        for base in {actual, resolved}:
            if base in result:
                result = result.replace(base, virtual_base)
    return result


def _format_process_result(result: CompletedSandboxProcess) -> str:
    output = result.stdout.strip()
    if result.stderr:
        output = f"{output}\nSTDERR:\n{result.stderr.strip()}".strip()
    if result.returncode != 0:
        output = f"{output}\nExit Code: {result.returncode}".strip()
    return output or "(no output)"


def _last_ai_text(messages: list[BaseMessage]) -> str:
    for message in reversed(messages):
        if isinstance(message, AIMessage) and message.content:
            return str(message.content)
    return ""


def _message_summary(message: BaseMessage) -> dict[str, object]:
    if isinstance(message, HumanMessage):
        return {"type": "human", "content": message.content}
    if isinstance(message, ToolMessage):
        return {"type": "tool", "name": message.name, "content": message.content}
    if isinstance(message, AIMessage):
        summary: dict[str, object] = {"type": "ai", "content": message.content}
        if message.tool_calls:
            summary["tool_calls"] = message.tool_calls
        return summary
    return {"type": message.type, "content": message.content}


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
