from __future__ import annotations

import json
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from examples.pptx_generator.state import (
    DeckProject, FontPairing, IntentReport, Palette, ResearchFindings,
    SlideIR, SlideOutline, SlideSpec, ThemeSelection,
)
from examples.pptx_generator.wizard.slides import SlideGeneratorWizardStep


def _base_project(n=3):
    specs = [SlideSpec(index=i, type="content", title=f"S{i}",
                       key_points=[], sources_cited=[]) for i in range(1, n + 1)]
    return DeckProject(
        slug="x", created_at=datetime.now(timezone.utc), stage="slides",
        intent=IntentReport(topic="t", audience="a", purpose="pitch", tone="formal",
                            slide_count_hint=n, required_sections=[], visuals_hint=[],
                            research_queries=[], language="zh"),
        research=ResearchFindings(),
        outline=SlideOutline(slides=specs),
        theme=ThemeSelection(
            palette=Palette(primary="111111", secondary="222222",
                            accent="333333", light="444444", bg="555555"),
            fonts=FontPairing(heading="Arial", body="Arial", cjk="Microsoft YaHei"),
            style="sharp", page_badge_style="circle",
        ),
    )


@pytest.mark.asyncio
async def test_generates_all_slides_in_parallel():
    async def fake_run(*, agent_id, session_id, input_text, deps=None):
        payload = json.loads(input_text)
        i = payload["target_spec"]["index"]
        return SimpleNamespace(parsed=SlideIR(
            index=i, type="content",
            slots={"title": f"S{i}", "body_blocks": []},
            generated_at=datetime.now(timezone.utc),
        ))
    runtime = SimpleNamespace(run=AsyncMock(side_effect=fake_run))
    step = SlideGeneratorWizardStep(runtime=runtime, concurrency=3)
    project = _base_project(n=3)
    result = await step.render(console=None, project=project)
    assert result.status == "completed"
    assert len(project.slides) == 3
    assert [s.index for s in project.slides] == [1, 2, 3]
    assert project.stage == "compile"


@pytest.mark.asyncio
async def test_slides_sorted_when_async_out_of_order():
    import asyncio
    call_count = [0]

    async def fake_run(*, agent_id, session_id, input_text, deps=None):
        call_count[0] += 1
        payload = json.loads(input_text)
        i = payload["target_spec"]["index"]
        # Invert timing so higher-index finishes first
        await asyncio.sleep(0.001 * (5 - i))
        return SimpleNamespace(parsed=SlideIR(
            index=i, type="content",
            slots={"title": f"S{i}", "body_blocks": []},
            generated_at=datetime.now(timezone.utc),
        ))
    runtime = SimpleNamespace(run=AsyncMock(side_effect=fake_run))
    step = SlideGeneratorWizardStep(runtime=runtime, concurrency=4)
    project = _base_project(n=4)
    result = await step.render(console=None, project=project)
    assert result.status == "completed"
    assert [s.index for s in project.slides] == [1, 2, 3, 4]


@pytest.mark.asyncio
async def test_raises_when_slide_returns_no_ir():
    async def fake_run(*, agent_id, session_id, input_text, deps=None):
        return SimpleNamespace(parsed=None, state={})
    runtime = SimpleNamespace(run=AsyncMock(side_effect=fake_run))
    step = SlideGeneratorWizardStep(runtime=runtime, concurrency=2)
    # slide_count_hint ge=3 — use n=3 but all runs return no IR
    project = _base_project(n=3)
    with pytest.raises(RuntimeError, match="all slides failed|SlideIR"):
        await step.render(console=None, project=project)
