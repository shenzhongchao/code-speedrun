from __future__ import annotations

import json
import os
import shutil
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Annotated, Any, Callable, TypedDict

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages


VIRTUAL_USER_DATA_ROOT = "/mnt/user-data"


@dataclass
class ResolvedTool:
    name: str
    source: str


@dataclass
class CompletedSandboxProcess:
    stdout: str
    stderr: str
    returncode: int


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
        docker_command = [
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
        # LEARN: The model asks for "bash", but Docker is the safety boundary.
        # The tool converts a plain shell string into `docker run -v <host>:/mnt/user-data ...`.
        # That makes DeerFlow's virtual paths point at the same files inside and outside Docker.
        return _format_process_result(self._runner(docker_command))

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


def build_openai_compatible_model(config: OpenAICompatibleConfig):
    from langchain_openai import ChatOpenAI

    return ChatOpenAI(**config.to_chat_openai_kwargs())


def run_langgraph_sandbox_demo(
    *,
    prompt: str,
    sandbox: DockerSandbox | LocalSandbox,
    model: object,
) -> dict[str, object]:
    tools = _make_sandbox_tools(sandbox)
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
            result = _dispatch_sandbox_tool(sandbox, tool_call["name"], tool_call["args"])
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
    return run_langgraph_sandbox_demo(prompt=prompt, sandbox=sandbox, model=model)


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
        sandbox = LocalSandbox("local-scripted")
        model = ScriptedToolCallingModel(
            tool_name="bash",
            tool_args={"command": "printf 'LANGGRAPH_SANDBOX_OK\\n'"},
            final_text="LANGGRAPH_SANDBOX_OK",
        )
        agent_result = run_langgraph_sandbox_demo(
            prompt="Write and verify a tiny result inside the sandbox.",
            sandbox=sandbox,
            model=model,
        )
        mode = "offline-scripted-langgraph"

    return {
        "mode": mode,
        "tools": [asdict(tool) for tool in registry.resolve_tools(model_supports_vision=True, subagent_enabled=True)],
        "agent": agent_result,
    }


def _make_sandbox_tools(sandbox: DockerSandbox | LocalSandbox) -> list[object]:
    @tool
    def bash(command: str) -> str:
        """Run a shell command inside the sandbox."""
        return sandbox.execute_command(command)

    @tool
    def read_file(path: str) -> str:
        """Read a text file from the sandbox workspace."""
        return sandbox.read_file(path)

    @tool
    def write_file(path: str, content: str, append: bool = False) -> str:
        """Write text into a sandbox file."""
        sandbox.write_file(path, content, append=append)
        return f"Wrote {path}"

    return [bash, read_file, write_file]


def _dispatch_sandbox_tool(sandbox: DockerSandbox | LocalSandbox, name: str, args: dict[str, Any]) -> str:
    if name == "bash":
        return sandbox.execute_command(str(args["command"]))
    if name == "read_file":
        return sandbox.read_file(str(args["path"]))
    if name == "write_file":
        sandbox.write_file(
            str(args["path"]),
            str(args["content"]),
            append=bool(args.get("append", False)),
        )
        return f"Wrote {args['path']}"
    return f"Unknown tool: {name}"


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
