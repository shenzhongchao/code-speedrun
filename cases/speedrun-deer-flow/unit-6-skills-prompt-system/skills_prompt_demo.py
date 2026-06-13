from __future__ import annotations

import json
import shutil
import tempfile
import zipfile
from dataclasses import asdict, dataclass
from pathlib import Path, PurePosixPath


CURRENT_DIR = Path(__file__).resolve().parent
DEFAULT_SKILLS_ROOT = CURRENT_DIR / "_demo_data" / "skills"
DEFAULT_EXTENSIONS_CONFIG = CURRENT_DIR / "_demo_data" / "extensions_config.json"


@dataclass
class DemoSkill:
    name: str
    description: str
    category: str
    relative_path: Path
    skill_file: Path
    enabled: bool = True
    license: str | None = None

    @property
    def sandbox_skill_file(self) -> str:
        path = PurePosixPath("/mnt/skills") / self.category / self.relative_path.as_posix() / "SKILL.md"
        return path.as_posix()


def parse_skill_file(skill_file: Path, *, category: str, relative_path: Path) -> DemoSkill | None:
    if not skill_file.exists() or skill_file.name != "SKILL.md":
        return None
    content = skill_file.read_text(encoding="utf-8")
    if not content.startswith("---"):
        return None

    parts = content.split("---", 2)
    if len(parts) < 3:
        return None

    metadata: dict[str, str] = {}
    for line in parts[1].splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        metadata[key.strip()] = value.strip().strip('"')

    # LEARN: Front matter is only the prompt index. The full SKILL.md stays on
    # disk until the agent decides it needs that workflow.
    name = metadata.get("name")
    description = metadata.get("description")
    if not name or not description:
        return None

    return DemoSkill(
        name=name,
        description=description,
        license=metadata.get("license"),
        category=category,
        relative_path=relative_path,
        skill_file=skill_file,
    )


def _load_enabled_state(config_path: Path) -> dict[str, bool]:
    if not config_path.exists():
        return {}
    data = json.loads(config_path.read_text(encoding="utf-8"))
    raw_skills = data.get("skills", {})
    states: dict[str, bool] = {}
    for key, value in raw_skills.items():
        if isinstance(value, dict) and "enabled" in value:
            states[key] = bool(value["enabled"])
        elif isinstance(value, bool):
            states[key] = value
    return states


def list_demo_skills(
    *,
    skills_root: Path | None = None,
    extensions_config_path: Path | None = None,
    enabled_only: bool = False,
) -> list[DemoSkill]:
    skills_root = skills_root or DEFAULT_SKILLS_ROOT
    extensions_config_path = extensions_config_path or DEFAULT_EXTENSIONS_CONFIG
    if not skills_root.exists():
        return []

    enabled_state = _load_enabled_state(extensions_config_path)
    skills: list[DemoSkill] = []
    for category in ("public", "custom"):
        category_path = skills_root / category
        if not category_path.exists():
            continue
        for skill_file in sorted(category_path.rglob("SKILL.md")):
            relative_path = skill_file.parent.relative_to(category_path)
            skill = parse_skill_file(skill_file, category=category, relative_path=relative_path)
            if skill is None:
                continue
            # LEARN: Gateway and LangGraph run in separate processes, so enabled
            # state is reread from a file instead of trusted from an in-memory singleton.
            skill.enabled = enabled_state.get(f"{category}:{skill.name}", enabled_state.get(skill.name, True))
            if not enabled_only or skill.enabled:
                skills.append(skill)

    return sorted(skills, key=lambda item: (item.category, item.name))


def build_skills_prompt_section(
    *,
    skills_root: Path | None = None,
    extensions_config_path: Path | None = None,
) -> str:
    skills = list_demo_skills(
        skills_root=skills_root,
        extensions_config_path=extensions_config_path,
        enabled_only=True,
    )
    if not skills:
        return ""

    lines = [
        "<skill_system>",
        "Available skills are workflow recipes. Open a listed SKILL.md only when the task needs it.",
    ]
    for skill in skills:
        # LEARN: The prompt uses progressive loading: names and descriptions are
        # cheap context, while the full recipe is loaded from /mnt/skills on demand.
        lines.append(f"- {skill.name}: {skill.description} ({skill.sandbox_skill_file})")
    lines.append("</skill_system>")
    return "\n".join(lines)


def _validate_archive_members(zip_ref: zipfile.ZipFile, max_total_size: int = 50 * 1024 * 1024) -> None:
    total_size = 0
    for info in zip_ref.infolist():
        name = info.filename.replace("\\", "/")
        path = PurePosixPath(name)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"Archive contains unsafe member path: {info.filename!r}")
        total_size += max(info.file_size, 0)
        if total_size > max_total_size:
            raise ValueError("Skill archive is too large.")


def _find_extracted_skill_dir(temp_path: Path) -> Path:
    if (temp_path / "SKILL.md").exists():
        return temp_path
    candidates = [path for path in temp_path.iterdir() if path.is_dir() and not path.name.startswith(".")]
    if len(candidates) == 1 and (candidates[0] / "SKILL.md").exists():
        return candidates[0]
    raise ValueError("Skill archive must contain exactly one SKILL.md root.")


def install_demo_skill_archive(archive_path: Path, *, skills_root: Path | None = None) -> dict[str, str]:
    skills_root = skills_root or DEFAULT_SKILLS_ROOT
    custom_root = skills_root / "custom"
    custom_root.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="deerflow-skill-") as temp_dir:
        temp_path = Path(temp_dir)
        with zipfile.ZipFile(archive_path, "r") as zip_ref:
            _validate_archive_members(zip_ref)
            # LEARN: Installation extracts to a temporary directory first, then
            # validates the skill root before copying anything into custom skills.
            zip_ref.extractall(temp_path)

        source_skill_dir = _find_extracted_skill_dir(temp_path)
        parsed = parse_skill_file(
            source_skill_dir / "SKILL.md",
            category="custom",
            relative_path=Path(source_skill_dir.name),
        )
        if parsed is None:
            raise ValueError("Archive SKILL.md is missing required metadata.")

        target_dir = custom_root / parsed.name
        if target_dir.exists():
            shutil.rmtree(target_dir)
        shutil.copytree(source_skill_dir, target_dir)

    return {
        "skill_name": parsed.name,
        "installed_path": str(target_dir),
        "category": "custom",
    }


def _copy_default_skills_to_runtime(runtime_root: Path) -> Path:
    runtime_skills_root = runtime_root / "skills"
    if runtime_skills_root.exists():
        shutil.rmtree(runtime_skills_root)
    shutil.copytree(DEFAULT_SKILLS_ROOT, runtime_skills_root)
    return runtime_skills_root


def run_demo() -> dict[str, object]:
    runtime_root = CURRENT_DIR / "_demo_data" / "_runtime"
    runtime_root.mkdir(parents=True, exist_ok=True)
    runtime_skills_root = _copy_default_skills_to_runtime(runtime_root)
    archive_path = runtime_root / "table-maker.skill"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "table-maker/SKILL.md",
            "---\nname: table-maker\ndescription: Build compact comparison tables\n---\n\n# Table Maker\n",
        )

    before_install = list_demo_skills(
        skills_root=runtime_skills_root,
        extensions_config_path=DEFAULT_EXTENSIONS_CONFIG,
    )
    prompt = build_skills_prompt_section(
        skills_root=runtime_skills_root,
        extensions_config_path=DEFAULT_EXTENSIONS_CONFIG,
    )
    install_result = install_demo_skill_archive(archive_path, skills_root=runtime_skills_root)
    after_install = list_demo_skills(
        skills_root=runtime_skills_root,
        extensions_config_path=DEFAULT_EXTENSIONS_CONFIG,
    )
    return {
        "skills_before_install": [asdict(skill) | {"skill_file": str(skill.skill_file), "relative_path": str(skill.relative_path)} for skill in before_install],
        "prompt_section": prompt,
        "install_result": install_result,
        "skills_after_install": [skill.name for skill in after_install],
    }
