"""Stage 6 wizard step — parallel slide generation."""

from __future__ import annotations

import asyncio
import json
from dataclasses import dataclass
from typing import Any

from openagents.cli.wizard import StepResult

from ..state import DeckProject, SlideIR, SlideSpec


@dataclass
class SlideGeneratorWizardStep:
    runtime: Any
    concurrency: int = 3
    title: str = "slides"
    description: str = "Generate each slide's content JSON and convert to IR."

    async def render(self, console: Any, project: DeckProject) -> StepResult:
        assert project.outline is not None, "SlideGeneratorWizardStep requires outline"
        sem = asyncio.Semaphore(self.concurrency)
        theme_dump = project.theme.model_dump(mode="json") if project.theme else {}

        async def run_one(spec: SlideSpec) -> SlideIR:
            async with sem:
                payload = json.dumps({
                    "target_spec": spec.model_dump(mode="json"),
                    "theme": theme_dump,
                }, ensure_ascii=False)
                result = await self.runtime.run(
                    agent_id="slide-generator",
                    session_id=project.slug,
                    input_text=payload,
                )
                if isinstance(result, SlideIR):
                    return result
                parsed = getattr(result, "parsed", None)
                if isinstance(parsed, SlideIR):
                    return parsed
                raise RuntimeError(
                    f"slide {spec.index} returned no SlideIR"
                )

        raw = await asyncio.gather(
            *(run_one(s) for s in project.outline.slides), return_exceptions=True,
        )
        slides: list[SlideIR] = []
        errors: list[str] = []
        for result in raw:
            if isinstance(result, SlideIR):
                slides.append(result)
            elif isinstance(result, BaseException):
                errors.append(str(result))

        if not slides and errors:
            raise RuntimeError(f"all slides failed: {errors[0]}")

        project.slides = sorted(slides, key=lambda s: s.index)
        project.stage = "compile"

        if console is not None and errors:
            try:
                console.print(f"[yellow]Slides with errors: {len(errors)}[/yellow]")
            except Exception:
                pass

        if console is not None:
            try:
                strict = sum(1 for s in project.slides if s.type != "freeform")
                freeform = sum(1 for s in project.slides if s.type == "freeform")
                console.print(
                    f"Generated {len(project.slides)} slides "
                    f"([green]{strict} strict[/green], [yellow]{freeform} freeform[/yellow])"
                )
            except Exception:
                pass
        return StepResult(status="completed")
