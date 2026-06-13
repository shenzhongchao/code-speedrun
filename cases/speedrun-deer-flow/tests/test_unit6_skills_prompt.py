from __future__ import annotations

import importlib.util
import json
import sys
import zipfile
from pathlib import Path


SPEEDRUN_ROOT = Path(__file__).resolve().parents[1]


def load_unit6():
    path = SPEEDRUN_ROOT / "unit-6-skills-prompt-system" / "skills_prompt_demo.py"
    spec = importlib.util.spec_from_file_location("unit6_skills_prompt_demo", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def write_skill(root: Path, category: str, slug: str, name: str, description: str) -> None:
    skill_dir = root / category / slug
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text(
        f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n",
        encoding="utf-8",
    )


def test_disabled_skill_is_not_in_enabled_prompt(tmp_path):
    unit6 = load_unit6()
    skills_root = tmp_path / "skills"
    write_skill(skills_root, "public", "research", "research", "Research workflow")
    write_skill(skills_root, "custom", "charting", "charting", "Chart workflow")
    config_path = tmp_path / "extensions_config.json"
    config_path.write_text(
        json.dumps(
            {
                "skills": {
                    "public:research": {"enabled": True},
                    "custom:charting": {"enabled": False},
                }
            }
        ),
        encoding="utf-8",
    )

    prompt = unit6.build_skills_prompt_section(
        skills_root=skills_root,
        extensions_config_path=config_path,
    )

    assert "research" in prompt
    assert "charting" not in prompt


def test_prompt_uses_sandbox_skill_locations(tmp_path):
    unit6 = load_unit6()
    skills_root = tmp_path / "skills"
    write_skill(skills_root, "public", "research", "research", "Research workflow")

    prompt = unit6.build_skills_prompt_section(skills_root=skills_root)

    assert "/mnt/skills/public/research/SKILL.md" in prompt


def test_install_skill_archive_adds_custom_skill_to_scan(tmp_path):
    unit6 = load_unit6()
    skills_root = tmp_path / "skills"
    archive_path = tmp_path / "table-maker.skill"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "table-maker/SKILL.md",
            "---\nname: table-maker\ndescription: Build comparison tables\n---\n\n# Table Maker\n",
        )

    result = unit6.install_demo_skill_archive(archive_path, skills_root=skills_root)
    skills = unit6.list_demo_skills(skills_root=skills_root)

    assert result["skill_name"] == "table-maker"
    assert result["installed_path"].endswith("custom/table-maker")
    assert [skill.name for skill in skills] == ["table-maker"]
