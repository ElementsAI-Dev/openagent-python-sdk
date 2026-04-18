from __future__ import annotations

import os
from unittest.mock import AsyncMock

import pytest

from examples.pptx_generator.cli import _load_env_files, build_parser, main


def test_load_env_files_loads_user_dotenv(tmp_path, monkeypatch):
    """_load_env_files should load vars from user-level .env if dotenv is available."""
    pytest.importorskip("dotenv")

    user_env_dir = tmp_path / "config" / "pptx-agent"
    user_env_dir.mkdir(parents=True)
    env_file = user_env_dir / ".env"
    env_file.write_text("TEST_PPTX_LOAD_ENV=hello_dotenv\n", encoding="utf-8")

    import examples.pptx_generator.cli as cli_mod

    original_expanduser = cli_mod.Path.expanduser

    def fake_expanduser(self):
        if "pptx-agent" in str(self):
            return env_file
        return original_expanduser(self)

    monkeypatch.setattr(cli_mod.Path, "expanduser", fake_expanduser)
    monkeypatch.delenv("TEST_PPTX_LOAD_ENV", raising=False)

    _load_env_files()
    assert os.environ.get("TEST_PPTX_LOAD_ENV") == "hello_dotenv"


def test_parser_has_new_and_resume():
    parser = build_parser()
    args = parser.parse_args(["new", "--topic", "hello"])
    assert args.command == "new"
    args2 = parser.parse_args(["resume", "my-slug"])
    assert args2.command == "resume"
    assert args2.slug == "my-slug"


def test_parser_memory():
    parser = build_parser()
    args = parser.parse_args(["memory"])
    assert args.command == "memory"
    args2 = parser.parse_args(["memory", "--section", "user_goals"])
    assert args2.section == "user_goals"


@pytest.mark.asyncio
async def test_main_dispatches_new(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_AGENT_OUTPUTS", str(tmp_path))
    fake = AsyncMock(return_value=0)
    monkeypatch.setattr("examples.pptx_generator.cli.run_wizard", fake)
    rc = await main(["new", "--topic", "demo"])
    assert rc == 0
    fake.assert_awaited_once()


@pytest.mark.asyncio
async def test_main_dispatches_resume_loads_existing(monkeypatch, tmp_path):
    from datetime import datetime, timezone
    from examples.pptx_generator.persistence import save_project
    from examples.pptx_generator.state import DeckProject

    monkeypatch.setenv("PPTX_AGENT_OUTPUTS", str(tmp_path))
    existing = DeckProject(slug="abc", created_at=datetime.now(timezone.utc), stage="env")
    save_project(existing, root=tmp_path)

    captured = {}
    async def fake_wizard(project, *, resume=False, **kw):
        captured["slug"] = project.slug
        captured["resume"] = resume
        return 0
    monkeypatch.setattr("examples.pptx_generator.cli.run_wizard", fake_wizard)

    rc = await main(["resume", "abc"])
    assert rc == 0
    assert captured["slug"] == "abc"
    assert captured["resume"] is True


@pytest.mark.asyncio
async def test_resume_on_done_project_exits_cleanly(tmp_path, monkeypatch, capsys):
    from datetime import datetime, timezone

    from examples.pptx_generator.persistence import save_project
    from examples.pptx_generator.state import DeckProject

    monkeypatch.setenv("PPTX_AGENT_OUTPUTS", str(tmp_path))
    done = DeckProject(slug="finished", created_at=datetime.now(timezone.utc), stage="done")
    save_project(done, root=tmp_path)

    rc = await main(["resume", "finished"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "already complete" in captured.out.lower()


@pytest.mark.asyncio
async def test_slugify_from_topic_creates_unique_slug(monkeypatch, tmp_path):
    monkeypatch.setenv("PPTX_AGENT_OUTPUTS", str(tmp_path))
    captured = {}
    async def fake_wizard(project, **kw):
        captured["slug"] = project.slug
        return 0
    monkeypatch.setattr("examples.pptx_generator.cli.run_wizard", fake_wizard)
    rc = await main(["new", "--topic", "My Awesome Deck"])
    assert rc == 0
    # Slug should be lowercased, dashed, match SLUG_RE regex (a-z0-9 _ -)
    slug = captured["slug"]
    assert slug.startswith("my-awesome-deck-")
    assert all(c.isalnum() or c in "-_" for c in slug)
