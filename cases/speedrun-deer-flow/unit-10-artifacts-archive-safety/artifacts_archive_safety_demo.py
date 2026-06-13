from __future__ import annotations

import mimetypes
import shutil
import stat
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath
from urllib.parse import quote


CURRENT_DIR = Path(__file__).resolve().parent
DEFAULT_THREADS_ROOT = CURRENT_DIR / "_demo_data" / "threads"


@dataclass
class ArtifactResponse:
    thread_id: str
    virtual_path: str
    host_path: str
    media_type: str
    response_kind: str
    preview: str | None = None
    bytes_length: int | None = None


def _resolve_virtual_path(thread_id: str, virtual_path: str, threads_root: Path) -> Path:
    normalized = virtual_path.replace("\\", "/")
    if normalized.startswith("/"):
        normalized = normalized[1:]
    prefix = "mnt/user-data/"
    if not normalized.startswith(prefix):
        raise ValueError("Artifact path must start with /mnt/user-data/.")
    relative = PurePosixPath(normalized[len(prefix) :])
    # LEARN: The artifact endpoint resolves a thread-scoped virtual path. It
    # never accepts an arbitrary host filesystem path from the request.
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError("Artifact path traversal is not allowed.")
    root = (threads_root / thread_id / "user-data").resolve()
    actual_path = (root / Path(*relative.parts)).resolve()
    try:
        actual_path.relative_to(root)
    except ValueError as exc:
        raise ValueError("Artifact path escaped the thread user-data root.") from exc
    return actual_path


def _is_text_file(path: Path, sample_size: int = 8192) -> bool:
    chunk = path.read_bytes()[:sample_size]
    return b"\x00" not in chunk


def resolve_demo_artifact(
    *,
    thread_id: str,
    virtual_path: str,
    threads_root: Path | None = None,
) -> dict[str, object]:
    threads_root = threads_root or DEFAULT_THREADS_ROOT
    actual_path = _resolve_virtual_path(thread_id, virtual_path, threads_root)
    if not actual_path.exists() or not actual_path.is_file():
        raise FileNotFoundError(str(actual_path))

    media_type, _ = mimetypes.guess_type(actual_path)
    media_type = media_type or "application/octet-stream"
    # LEARN: Response shape follows MIME/content detection: HTML renders as
    # HTML, text returns plain content, and binary files return bytes metadata.
    if media_type == "text/html":
        response = ArtifactResponse(
            thread_id=thread_id,
            virtual_path=virtual_path,
            host_path=str(actual_path),
            media_type=media_type,
            response_kind="html",
            preview=actual_path.read_text(encoding="utf-8")[:120],
        )
    elif media_type.startswith("text/") or _is_text_file(actual_path):
        response = ArtifactResponse(
            thread_id=thread_id,
            virtual_path=virtual_path,
            host_path=str(actual_path),
            media_type=media_type,
            response_kind="text",
            preview=actual_path.read_text(encoding="utf-8")[:120],
        )
    else:
        response = ArtifactResponse(
            thread_id=thread_id,
            virtual_path=virtual_path,
            host_path=str(actual_path),
            media_type=media_type,
            response_kind="binary",
            bytes_length=actual_path.stat().st_size,
        )
    return asdict(response) | {"encoded_filename": quote(actual_path.name)}


def _is_symlink_member(info: zipfile.ZipInfo) -> bool:
    mode = info.external_attr >> 16
    return stat.S_ISLNK(mode)


def validate_archive_members(
    archive_path: Path,
    *,
    max_total_uncompressed_size: int = 50 * 1024 * 1024,
) -> list[str]:
    total_size = 0
    safe_members: list[str] = []
    with zipfile.ZipFile(archive_path, "r") as archive:
        for info in archive.infolist():
            name = info.filename.replace("\\", "/")
            path = PurePosixPath(name)
            # LEARN: ZIP member paths are request data too. They can attempt
            # traversal even though they live inside an archive.
            if path.is_absolute() or ".." in path.parts:
                raise ValueError(f"Unsafe archive member path: {info.filename!r}")
            if _is_symlink_member(info):
                raise ValueError(f"Unsafe archive symlink member: {info.filename!r}")
            # LEARN: Zip-bomb protection counts uncompressed size, not just the
            # compressed archive size on disk.
            total_size += max(info.file_size, 0)
            if total_size > max_total_uncompressed_size:
                raise ValueError("Archive exceeds the maximum uncompressed size.")
            safe_members.append(info.filename)
    return safe_members


def inspect_skill_archive(archive_path: Path, internal_path: str = "SKILL.md") -> dict[str, object]:
    validate_archive_members(archive_path)
    with zipfile.ZipFile(archive_path, "r") as archive:
        names = archive.namelist()
        selected = internal_path if internal_path in names else None
        if selected is None:
            suffix = "/" + internal_path
            selected = next((name for name in names if name.endswith(suffix)), None)
        if selected is None:
            return {"found": False, "internal_path": internal_path}
        data = archive.read(selected)
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = None
    return {
        "found": True,
        "internal_path": selected,
        "text": text,
        "bytes_length": len(data),
    }


def _prepare_runtime_archives(runtime_root: Path) -> tuple[Path, Path]:
    if runtime_root.exists():
        shutil.rmtree(runtime_root)
    runtime_root.mkdir(parents=True)
    safe_archive = runtime_root / "safe.skill"
    unsafe_archive = runtime_root / "unsafe.skill"
    with zipfile.ZipFile(safe_archive, "w") as archive:
        archive.writestr("safe/SKILL.md", "---\nname: safe\ndescription: Safe archive\n---\n")
    with zipfile.ZipFile(unsafe_archive, "w") as archive:
        archive.writestr("../evil.txt", "bad")
    return safe_archive, unsafe_archive


def run_demo() -> dict[str, object]:
    safe_archive, unsafe_archive = _prepare_runtime_archives(CURRENT_DIR / "_demo_data" / "_runtime")
    unsafe_error = None
    try:
        validate_archive_members(unsafe_archive)
    except ValueError as exc:
        unsafe_error = str(exc)
    return {
        "html_artifact": resolve_demo_artifact(
            thread_id="thread-artifact",
            virtual_path="/mnt/user-data/outputs/report.html",
        ),
        "text_artifact": resolve_demo_artifact(
            thread_id="thread-artifact",
            virtual_path="/mnt/user-data/outputs/notes.txt",
        ),
        "skill_archive": inspect_skill_archive(safe_archive, "SKILL.md"),
        "unsafe_archive_error": unsafe_error,
    }
