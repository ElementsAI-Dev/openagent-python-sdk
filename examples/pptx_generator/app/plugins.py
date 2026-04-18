"""App-layer plugins for the pptx-agent example.

Each Pattern drives one stage of the 7-stage wizard. They inherit from
``openagents.interfaces.pattern.PatternPlugin`` so the runtime's
``setup()`` lifecycle populates ``self.context`` before ``execute()``
runs. Tests construct patterns directly and assign ``context`` manually
to bypass the full setup() dance.

This module starts with IntentAnalystPattern; sibling patterns
(ResearchPattern, OutlinePattern, ThemePattern, SlideGenPattern) are
appended in later tasks.
"""

from __future__ import annotations

import json
import re
from typing import Any

from pydantic import ValidationError

from openagents.interfaces.capabilities import PATTERN_EXECUTE
from openagents.interfaces.pattern import PatternPlugin

from ..state import IntentReport

_INTENT_SYSTEM = """You are a presentation planning assistant.
Extract an IntentReport as JSON only. Required fields:
topic, audience, purpose(one of pitch|report|teaching|announcement|other),
tone(one of formal|casual|energetic|minimalist),
slide_count_hint(int 3..20), required_sections(list), visuals_hint(list),
research_queries(list of up to 5 concrete search queries),
language(zh|en|bilingual).
Output ONLY JSON without markdown fencing."""


_FENCE_RE = re.compile(r"^\s*```(?:\w+)?\n?(?P<body>.*?)\n?```", re.DOTALL)


def _extract_json_block(raw: str) -> str:
    """Return the substring most likely to be a JSON document.

    Strips leading/trailing markdown code fences. If no fence is present,
    trims whitespace. If a fence exists, ignores any text outside it.
    """
    text = (raw or "").strip()
    m = _FENCE_RE.search(text)
    if m:
        return m.group("body").strip()
    return text


def _try_parse_intent(raw: str) -> tuple[IntentReport | None, str | None]:
    text = _extract_json_block(raw)
    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, f"JSON parse failed: {exc.msg}"
    try:
        return IntentReport.model_validate(data), None
    except ValidationError as exc:
        return None, f"Schema validation failed: {exc.errors()}"


class IntentAnalystPattern(PatternPlugin):
    """Stage 1: extract a validated IntentReport from the user's raw prompt.

    Budget: ``max_steps`` attempts. On validation failure the error is
    appended to the prompt before the next attempt. On final failure
    raises ``RuntimeError``.
    """

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config=config or {}, capabilities={PATTERN_EXECUTE})
        self.max_steps = int((config or {}).get("max_steps", 3))

    async def execute(self) -> IntentReport:
        ctx = self.context
        if ctx is None:
            raise RuntimeError("IntentAnalystPattern.context is not set; call setup() first")

        memory_view = getattr(ctx, "memory_view", {}) or {}
        goals = memory_view.get("user_goals", []) if isinstance(memory_view, dict) else []
        feedback = memory_view.get("user_feedback", []) if isinstance(memory_view, dict) else []
        priors = "\n".join(f"- {e.get('rule', '')}" for e in (goals + feedback))
        user_prompt = ctx.input_text or ""

        user_content = (
            f"Known user preferences:\n{priors or '(none)'}\n\n"
            f"User request:\n{user_prompt}"
        )

        last_raw = ""
        for step in range(1, self.max_steps + 1):
            messages = [
                {"role": "system", "content": _INTENT_SYSTEM},
                {"role": "user", "content": user_content},
            ]
            raw = await ctx.llm_client.complete(messages=messages)
            last_raw = str(raw or "")
            parsed, reason = _try_parse_intent(last_raw)
            if parsed is not None:
                ctx.state["intent"] = parsed.model_dump(mode="json")
                return parsed
            user_content = user_content + (
                f"\n\nPrevious attempt failed ({reason}). Raw output was:\n{last_raw}\nTry again with valid output."
            )
        raise RuntimeError(
            f"IntentAnalystPattern exhausted {self.max_steps} retries; last raw: {last_raw[:200]}"
        )
