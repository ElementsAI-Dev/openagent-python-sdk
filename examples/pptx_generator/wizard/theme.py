"""Stage 5 wizard step — theme selection."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openagents.cli.wizard import StepResult, Wizard

from ..state import DeckProject, ThemeSelection


@dataclass
class ThemeWizardStep:
    runtime: Any
    title: str = "theme"
    description: str = "Pick palette, fonts, and style."

    async def render(self, console: Any, project: DeckProject) -> StepResult:
        result = await self.runtime.run(
            agent_id="theme-selector",
            session_id=project.slug,
            input_text="",
        )
        theme = self._extract(result)

        if console is not None:
            try:
                self._render_preview(console, theme)
            except Exception:
                pass

        action = await Wizard.select(
            "Theme action?",
            choices=["accept", "try another", "custom hex", "abort"],
            default="accept",
        )
        if action == "try another":
            return StepResult(status="retry")
        if action == "abort":
            return StepResult(status="aborted")
        if action == "custom hex":
            primary = await Wizard.text(
                "primary hex (6 chars, no '#')", default=theme.palette.primary,
            )
            theme = theme.model_copy(
                update={"palette": theme.palette.model_copy(update={"primary": primary})}
            )

        project.theme = theme
        project.stage = "slides"
        return StepResult(status="completed")

    @staticmethod
    def _extract(result: Any) -> ThemeSelection:
        if isinstance(result, ThemeSelection):
            return result
        parsed = getattr(result, "parsed", None)
        if isinstance(parsed, ThemeSelection):
            return parsed
        state = getattr(result, "state", None) or {}
        return ThemeSelection.model_validate(state.get("theme", {}))

    @staticmethod
    def _render_preview(console: Any, theme: ThemeSelection) -> None:
        from rich.columns import Columns
        from rich.panel import Panel

        p = theme.palette
        swatches = [
            Panel(f"[bold]{name}[/bold]\n#{val}", style=f"on #{val}",
                  width=20, height=4)
            for name, val in [
                ("primary", p.primary), ("secondary", p.secondary),
                ("accent", p.accent), ("light", p.light), ("bg", p.bg),
            ]
        ]
        console.print(Columns(swatches))
        console.print(
            f"Heading: [bold]{theme.fonts.heading}[/bold]   "
            f"Body: {theme.fonts.body}   CJK: {theme.fonts.cjk}"
        )
        console.print(f"Style: {theme.style}   Badge: {theme.page_badge_style}")
