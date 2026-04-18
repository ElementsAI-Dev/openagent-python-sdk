from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from examples.pptx_generator.state import (
    DeckProject, FontPairing, IntentReport, Palette, ThemeSelection,
)
from examples.pptx_generator.wizard.theme import ThemeWizardStep


def _theme():
    return ThemeSelection(
        palette=Palette(primary="111111", secondary="222222",
                        accent="333333", light="444444", bg="555555"),
        fonts=FontPairing(heading="Arial", body="Arial", cjk="Microsoft YaHei"),
        style="sharp", page_badge_style="circle",
    )


def _project():
    return DeckProject(
        slug="x", created_at=datetime.now(timezone.utc), stage="theme",
        intent=IntentReport(topic="t", audience="a", purpose="pitch", tone="formal",
                            slide_count_hint=5, required_sections=[], visuals_hint=[],
                            research_queries=[], language="zh"),
    )


@pytest.mark.asyncio
async def test_accept(monkeypatch):
    theme = _theme()
    runtime = SimpleNamespace(run=AsyncMock(return_value=SimpleNamespace(
        parsed=theme, state={"theme": theme.model_dump(mode="json")},
    )))
    monkeypatch.setattr(
        "examples.pptx_generator.wizard.theme.Wizard.select",
        AsyncMock(return_value="accept"),
    )
    step = ThemeWizardStep(runtime=runtime)
    project = _project()
    result = await step.render(console=None, project=project)
    assert result.status == "completed"
    assert project.theme is not None
    assert project.stage == "slides"


@pytest.mark.asyncio
async def test_try_another(monkeypatch):
    theme = _theme()
    runtime = SimpleNamespace(run=AsyncMock(return_value=SimpleNamespace(
        parsed=theme, state={"theme": theme.model_dump(mode="json")},
    )))
    monkeypatch.setattr(
        "examples.pptx_generator.wizard.theme.Wizard.select",
        AsyncMock(return_value="try another"),
    )
    step = ThemeWizardStep(runtime=runtime)
    project = _project()
    result = await step.render(console=None, project=project)
    assert result.status == "retry"
    assert project.stage == "theme"


@pytest.mark.asyncio
async def test_abort(monkeypatch):
    theme = _theme()
    runtime = SimpleNamespace(run=AsyncMock(return_value=SimpleNamespace(
        parsed=theme, state={"theme": theme.model_dump(mode="json")},
    )))
    monkeypatch.setattr(
        "examples.pptx_generator.wizard.theme.Wizard.select",
        AsyncMock(return_value="abort"),
    )
    step = ThemeWizardStep(runtime=runtime)
    project = _project()
    result = await step.render(console=None, project=project)
    assert result.status == "aborted"


@pytest.mark.asyncio
async def test_custom_hex(monkeypatch):
    theme = _theme()
    runtime = SimpleNamespace(run=AsyncMock(return_value=SimpleNamespace(
        parsed=theme, state={"theme": theme.model_dump(mode="json")},
    )))
    monkeypatch.setattr(
        "examples.pptx_generator.wizard.theme.Wizard.select",
        AsyncMock(return_value="custom hex"),
    )
    monkeypatch.setattr(
        "examples.pptx_generator.wizard.theme.Wizard.text",
        AsyncMock(return_value="aabbcc"),
    )
    step = ThemeWizardStep(runtime=runtime)
    project = _project()
    result = await step.render(console=None, project=project)
    assert result.status == "completed"
    assert project.theme.palette.primary == "aabbcc"
