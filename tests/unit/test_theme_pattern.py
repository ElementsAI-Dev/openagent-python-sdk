from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from examples.pptx_generator.app.catalog import FONT_PAIRINGS, PALETTES
from examples.pptx_generator.app.plugins import ThemePattern
from examples.pptx_generator.state import ThemeSelection


def test_catalog_has_at_least_five_palettes():
    assert len(PALETTES) >= 5
    for p in PALETTES:
        assert set(p).issuperset({"name", "palette", "mood"})


def test_font_pairings_cover_zh_en():
    assert any(fp["cjk"] for fp in FONT_PAIRINGS)


def _make_ctx(llm_return: str):
    return SimpleNamespace(
        input_text="",
        state={"intent": {"tone": "formal", "language": "zh"}},
        memory_view={"decisions": []},
        tool_results=[],
        assembly_metadata={},
        llm_client=SimpleNamespace(complete=AsyncMock(return_value=llm_return)),
    )


@pytest.mark.asyncio
async def test_theme_pattern_selects_valid_theme():
    llm_response = json.dumps({
        "palette_name": PALETTES[0]["name"],
        "font_pairing_name": FONT_PAIRINGS[0]["name"],
        "style": "sharp",
        "page_badge_style": "circle",
    })
    pattern = ThemePattern(config={})
    pattern.context = _make_ctx(llm_response)
    result = await pattern.execute()
    assert isinstance(result, ThemeSelection)
    assert result.palette.primary == PALETTES[0]["palette"]["primary"].lower()
    assert result.fonts.heading == FONT_PAIRINGS[0]["heading"]


@pytest.mark.asyncio
async def test_theme_pattern_retries_on_unknown_palette_name():
    calls = []

    async def complete(*, messages, **kwargs):
        calls.append(messages)
        if len(calls) < 2:
            return json.dumps({
                "palette_name": "no-such-palette",
                "font_pairing_name": FONT_PAIRINGS[0]["name"],
                "style": "soft", "page_badge_style": "circle",
            })
        return json.dumps({
            "palette_name": PALETTES[0]["name"],
            "font_pairing_name": FONT_PAIRINGS[0]["name"],
            "style": "soft", "page_badge_style": "circle",
        })

    pattern = ThemePattern(config={"max_steps": 3})
    ctx = _make_ctx("")
    ctx.llm_client.complete = complete
    pattern.context = ctx
    result = await pattern.execute()
    assert isinstance(result, ThemeSelection)
    assert len(calls) == 2


@pytest.mark.asyncio
async def test_theme_pattern_exhausts():
    pattern = ThemePattern(config={"max_steps": 2})
    pattern.context = _make_ctx("garbage")
    with pytest.raises(RuntimeError, match="exhausted"):
        await pattern.execute()
