"""Import helpers for loading modules from unit directories."""

from __future__ import annotations

import importlib.util
import sys
from functools import lru_cache
from pathlib import Path
from types import ModuleType

ROOT = Path(__file__).resolve().parent


@lru_cache(maxsize=None)
def load_unit_module(relative_path: str, module_name: str) -> ModuleType:
    """Load and cache a module from a file path relative to speedrun root."""
    file_path = ROOT / relative_path
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Cannot load module from {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module
