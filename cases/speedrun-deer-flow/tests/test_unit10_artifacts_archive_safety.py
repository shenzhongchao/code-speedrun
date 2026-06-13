from __future__ import annotations

import importlib.util
import stat
import sys
import zipfile
from pathlib import Path

import pytest


SPEEDRUN_ROOT = Path(__file__).resolve().parents[1]


def load_unit10():
    path = SPEEDRUN_ROOT / "unit-10-artifacts-archive-safety" / "artifacts_archive_safety_demo.py"
    spec = importlib.util.spec_from_file_location("unit10_artifacts_archive_safety_demo", path)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_artifact_path_traversal_is_rejected(tmp_path):
    unit10 = load_unit10()

    with pytest.raises(ValueError):
        unit10.resolve_demo_artifact(
            thread_id="thread-artifact",
            virtual_path="/mnt/user-data/outputs/../secrets.txt",
            threads_root=tmp_path,
        )


def test_skill_archive_internal_skill_file_can_be_read(tmp_path):
    unit10 = load_unit10()
    archive_path = tmp_path / "demo.skill"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr(
            "demo/SKILL.md",
            "---\nname: demo\ndescription: Demo skill\n---\n\n# Demo\n",
        )

    result = unit10.inspect_skill_archive(archive_path, "SKILL.md")

    assert result["found"] is True
    assert "name: demo" in result["text"]


def test_unsafe_zip_members_are_rejected(tmp_path):
    unit10 = load_unit10()
    archive_path = tmp_path / "unsafe.skill"
    with zipfile.ZipFile(archive_path, "w") as archive:
        archive.writestr("../evil.txt", "bad")

    with pytest.raises(ValueError):
        unit10.validate_archive_members(archive_path)

    symlink_archive = tmp_path / "symlink.skill"
    with zipfile.ZipFile(symlink_archive, "w") as archive:
        info = zipfile.ZipInfo("link")
        info.external_attr = (stat.S_IFLNK | 0o777) << 16
        archive.writestr(info, "target")

    with pytest.raises(ValueError):
        unit10.validate_archive_members(symlink_archive)
