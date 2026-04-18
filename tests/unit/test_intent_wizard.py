from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from examples.pptx_generator.state import DeckProject, IntentReport
from examples.pptx_generator.wizard.intent import IntentWizardStep


def _mk_report() -> IntentReport:
    return IntentReport(
        topic="t", audience="a", purpose="pitch", tone="formal",
        slide_count_hint=5, required_sections=[], visuals_hint=[],
        research_queries=[], language="zh",
    )


def _mk_project() -> DeckProject:
    return DeckProject(slug="x", created_at=datetime.now(timezone.utc), stage="intent")


@pytest.mark.asyncio
async def test_intent_wizard_accepted(monkeypatch):
    report = _mk_report()
    runtime = SimpleNamespace(run=AsyncMock(return_value=SimpleNamespace(
        parsed=report,
        state={"intent": report.model_dump(mode="json")},
    )))
    # User accepts the intent; doesn't save to memory
    monkeypatch.setattr("examples.pptx_generator.wizard.intent.Wizard.confirm",
                        AsyncMock(side_effect=[True, False]))
    step = IntentWizardStep(runtime=runtime, topic_hint="draft")
    project = _mk_project()
    result = await step.render(console=None, project=project)
    assert result.status == "completed"
    assert project.intent is not None
    assert project.intent.topic == "t"
    assert project.stage == "env"


@pytest.mark.asyncio
async def test_intent_wizard_rejected_retries(monkeypatch):
    report = _mk_report()
    runtime = SimpleNamespace(run=AsyncMock(return_value=SimpleNamespace(
        parsed=report, state={"intent": report.model_dump(mode="json")},
    )))
    monkeypatch.setattr("examples.pptx_generator.wizard.intent.Wizard.confirm",
                        AsyncMock(return_value=False))
    step = IntentWizardStep(runtime=runtime, topic_hint="draft")
    project = _mk_project()
    result = await step.render(console=None, project=project)
    assert result.status == "retry"
    assert project.intent is None  # unchanged
    assert project.stage == "intent"


@pytest.mark.asyncio
async def test_intent_wizard_saves_to_memory(monkeypatch, tmp_path):
    report = _mk_report()
    runtime = SimpleNamespace(run=AsyncMock(return_value=SimpleNamespace(
        parsed=report, state={"intent": report.model_dump(mode="json")},
    )))
    # User confirms + chooses to save preferences
    monkeypatch.setattr("examples.pptx_generator.wizard.intent.Wizard.confirm",
                        AsyncMock(side_effect=[True, True]))
    # Redirect memory writes to tmp_path
    capture_log = []
    class FakeMem:
        def __init__(self, config=None):
            self.config = config
        def capture(self, category, rule, reason):
            capture_log.append((category, rule, reason))
            return "xyz"
    monkeypatch.setattr(
        "examples.pptx_generator.wizard.intent.MarkdownMemory", FakeMem
    )
    step = IntentWizardStep(runtime=runtime, topic_hint="draft")
    project = _mk_project()
    result = await step.render(console=None, project=project)
    assert result.status == "completed"
    assert len(capture_log) >= 1
    assert capture_log[0][0] == "user_goals"
