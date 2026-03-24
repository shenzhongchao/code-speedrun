from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from pathlib import Path


CONVERTIBLE_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx"}


@dataclass
class ModelInfo:
    name: str
    model: str
    display_name: str
    description: str
    supports_thinking: bool
    supports_reasoning_effort: bool
    supports_vision: bool


@dataclass
class ToolInfo:
    name: str
    group: str


@dataclass
class DemoAppConfig:
    models: list[ModelInfo]
    tools: list[ToolInfo]

    def get_model(self, name: str | None) -> ModelInfo | None:
        if name is None:
            return None
        return next((model for model in self.models if model.name == name), None)


@dataclass
class UploadedFile:
    filename: str
    content: str


def build_demo_config() -> DemoAppConfig:
    # LEARN: Keep config separate from request handling.
    # The gateway's job is to expose safe slices of configuration to the UI, not to decide
    # how the lead agent thinks. That separation mirrors the real DeerFlow backend.
    return DemoAppConfig(
        models=[
            ModelInfo(
                name="gpt-5-responses",
                model="gpt-5",
                display_name="GPT-5 (Responses API)",
                description="Default high-capability model for the lead agent",
                supports_thinking=True,
                supports_reasoning_effort=True,
                supports_vision=True,
            ),
            ModelInfo(
                name="claude-sonnet-4.6",
                model="claude-sonnet-4-6",
                display_name="Claude Sonnet 4.6",
                description="Alternate thinking model",
                supports_thinking=True,
                supports_reasoning_effort=False,
                supports_vision=True,
            ),
            ModelInfo(
                name="gemini-2.5-flash",
                model="gemini-2.5-flash",
                display_name="Gemini 2.5 Flash",
                description="Cheap summarization model",
                supports_thinking=False,
                supports_reasoning_effort=False,
                supports_vision=False,
            ),
        ],
        tools=[
            ToolInfo(name="bash", group="sandbox"),
            ToolInfo(name="read_file", group="sandbox"),
            ToolInfo(name="write_file", group="sandbox"),
            ToolInfo(name="web_search", group="research"),
            ToolInfo(name="web_fetch", group="research"),
        ],
    )


class GatewayAPI:
    """A tiny FastAPI-like surface for the two backend ideas worth learning first."""

    def __init__(self, config: DemoAppConfig, storage_root: Path):
        self.config = config
        self.storage_root = storage_root

    def get_health(self) -> dict[str, str]:
        return {"status": "healthy", "service": "deer-flow-gateway-demo"}

    def list_models(self) -> dict[str, list[dict[str, object]]]:
        # LEARN: The gateway returns model metadata, not secrets.
        # Think of this as a restaurant menu: users need the names and capabilities,
        # but not the kitchen's internal supply details such as API keys.
        return {
            "models": [
                {
                    "name": model.name,
                    "model": model.model,
                    "display_name": model.display_name,
                    "description": model.description,
                    "supports_thinking": model.supports_thinking,
                    "supports_reasoning_effort": model.supports_reasoning_effort,
                }
                for model in self.config.models
            ]
        }

    def upload_files(self, thread_id: str, files: list[UploadedFile]) -> dict[str, object]:
        upload_dir = self._uploads_dir(thread_id)
        upload_dir.mkdir(parents=True, exist_ok=True)

        uploaded_files: list[dict[str, str]] = []
        for file in files:
            safe_name = Path(file.filename).name
            # LEARN: Normalize the filename before writing anything.
            # This blocks path tricks such as "../../secret.txt" and keeps uploads inside
            # the thread-scoped directory even if the incoming filename is malicious.
            if safe_name in {"", ".", ".."}:
                continue

            file_path = upload_dir / safe_name
            file_path.write_text(file.content, encoding="utf-8")
            # LEARN: DeerFlow keeps two views of the same file:
            # a host-side physical path for the backend, and a virtual sandbox path for the agent.
            # That indirection lets the runtime swap sandbox implementations without changing prompts.
            record = {
                "filename": safe_name,
                "size": str(len(file.content.encode("utf-8"))),
                "path": str(file_path),
                "virtual_path": f"/mnt/user-data/uploads/{safe_name}",
                "artifact_url": f"/api/threads/{thread_id}/artifacts/mnt/user-data/uploads/{safe_name}",
            }

            if file_path.suffix.lower() in CONVERTIBLE_EXTENSIONS:
                # LEARN: Some uploads get a second, easier-to-read form.
                # The real backend converts rich documents to Markdown so the agent can inspect them
                # without needing a binary parser in the prompt loop.
                markdown_path = file_path.with_suffix(".md")
                markdown_path.write_text(self._markdown_preview(file), encoding="utf-8")
                record["markdown_file"] = markdown_path.name
                record["markdown_path"] = str(markdown_path)
                record["markdown_virtual_path"] = f"/mnt/user-data/uploads/{markdown_path.name}"
            uploaded_files.append(record)

        return {
            "success": True,
            "files": uploaded_files,
            "message": f"Successfully uploaded {len(uploaded_files)} file(s)",
        }

    def reset_demo_state(self) -> None:
        shutil.rmtree(self.storage_root, ignore_errors=True)

    def _uploads_dir(self, thread_id: str) -> Path:
        return self.storage_root / "threads" / thread_id / "user-data" / "uploads"

    @staticmethod
    def _markdown_preview(file: UploadedFile) -> str:
        return "\n".join(
            [
                f"# Converted preview for {file.filename}",
                "",
                "This stands in for DeerFlow's markitdown conversion step.",
                "",
                file.content[:120],
            ]
        )


def run_demo() -> dict[str, object]:
    demo_root = Path(__file__).resolve().parent / "_demo_data"
    config = build_demo_config()
    gateway = GatewayAPI(config=config, storage_root=demo_root)
    # LEARN: Reset the demo storage so the learner can trust that every file shown
    # in the output came from this run, not from a leftover previous attempt.
    gateway.reset_demo_state()

    uploads = gateway.upload_files(
        thread_id="thread-gateway",
        files=[
            UploadedFile(
                filename="roadmap.docx",
                content="Need a two-step plan: audit the repo, then summarize the agent flow.",
            ),
            UploadedFile(
                filename="notes.txt",
                content="The frontend is not part of this speedrun. Keep focus on the backend.",
            ),
        ],
    )

    return {
        "health": gateway.get_health(),
        "models": gateway.list_models(),
        "uploads": uploads,
    }


if __name__ == "__main__":
    print(json.dumps(run_demo(), indent=2))
