"""DeckProject persistence.

Single-slot backup: each save overwrites the immediately previous
``project.json.bak``. Earlier history is not retained.

Crash safety: save writes to ``project.json.tmp`` then atomically replaces
the target via ``os.replace``. On failure between write and replace, the
``.tmp`` file remains on disk and is overwritten by the next successful
save — no cleanup loop is needed because paths are deterministic.

Missing-file behavior: ``load_project`` lets ``FileNotFoundError`` propagate
unchanged (distinct from corrupt JSON, which is wrapped as ``ValueError``).
"""

from __future__ import annotations

import json
import os
import shutil
from pathlib import Path

from .state import DeckProject


def project_path(slug: str, *, root: Path) -> Path:
    return Path(root) / slug / "project.json"


def backup_path(slug: str, *, root: Path) -> Path:
    return Path(root) / slug / "project.json.bak"


def load_project(slug: str, *, root: Path) -> DeckProject:
    path = project_path(slug, root=root)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"project.json at {path} is corrupt: {exc}") from exc
    return DeckProject.model_validate(data)


def save_project(project: DeckProject, *, root: Path) -> Path:
    path = project_path(project.slug, root=root)
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        shutil.copy2(path, backup_path(project.slug, root=root))
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(project.model_dump_json(indent=2), encoding="utf-8")
    os.replace(tmp, path)
    return path
