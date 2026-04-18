from __future__ import annotations

from datetime import datetime, timezone

import pytest

from examples.pptx_generator.persistence import (
    load_project,
    save_project,
    project_path,
    backup_path,
)
from examples.pptx_generator.state import DeckProject


def _mk(slug: str) -> DeckProject:
    return DeckProject(slug=slug, created_at=datetime.now(timezone.utc), stage="intent")


def test_save_and_load_roundtrip(tmp_path):
    p = _mk("demo")
    save_project(p, root=tmp_path)
    loaded = load_project("demo", root=tmp_path)
    assert loaded.slug == "demo"
    assert loaded.stage == "intent"


def test_save_creates_backup(tmp_path):
    p = _mk("demo")
    save_project(p, root=tmp_path)
    p.stage = "env"
    save_project(p, root=tmp_path)
    assert backup_path("demo", root=tmp_path).exists()


def test_corrupt_load_raises(tmp_path):
    path = project_path("demo", root=tmp_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("not json", encoding="utf-8")
    with pytest.raises(ValueError):
        load_project("demo", root=tmp_path)


def test_atomic_write_on_crash(tmp_path, monkeypatch):
    # simulate os.replace failure mid-write by patching os.replace
    import os
    original_replace = os.replace
    calls = {"n": 0}
    def fake_replace(src, dst):
        calls["n"] += 1
        raise OSError("boom")
    monkeypatch.setattr(os, "replace", fake_replace)
    p = _mk("demo")
    with pytest.raises(OSError):
        save_project(p, root=tmp_path)
    monkeypatch.setattr(os, "replace", original_replace)
    assert not project_path("demo", root=tmp_path).exists()
