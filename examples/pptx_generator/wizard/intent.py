"""Stage 1 wizard step — intent analysis."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from openagents.cli.wizard import StepResult, Wizard
from openagents.plugins.builtin.memory.markdown_memory import MarkdownMemory

from ..state import DeckProject, IntentReport


@dataclass
class IntentWizardStep:
    runtime: Any
    topic_hint: str | None = None
    title: str = "intent"
    description: str = "Understand what you want to present."

    async def render(self, console: Any, project: DeckProject) -> StepResult:
        report = await self._invoke_agent(project)
        if console is not None:
            try:
                console.print(Wizard.panel("Intent", self._format_report(report)))
            except Exception:
                pass
        confirmed = await Wizard.confirm("Does this match your intent?", default=True)
        if not confirmed:
            return StepResult(status="retry")
        project.intent = report
        project.stage = "env"
        save = await Wizard.confirm("Save these as long-term preferences?", default=False)
        if save:
            try:
                mem = MarkdownMemory(config={"memory_dir": "~/.config/pptx-agent/memory"})
                mem.capture(
                    category="user_goals",
                    rule=f"typical deck: {report.slide_count_hint} slides, tone={report.tone}",
                    reason="confirmed at intent stage",
                )
            except Exception:
                pass
        return StepResult(status="completed", data=report)

    async def _invoke_agent(self, project: DeckProject) -> IntentReport:
        result = await self.runtime.run(
            agent_id="intent-analyst",
            session_id=project.slug,
            input_text=self.topic_hint or "",
        )
        # Runtime.run returns the pattern's final_output directly (IntentReport).
        if isinstance(result, IntentReport):
            return result
        # Back-compat for test doubles that wrap it: SimpleNamespace(parsed=...) or state dict.
        parsed = getattr(result, "parsed", None)
        if isinstance(parsed, IntentReport):
            return parsed
        state = getattr(result, "state", None) or {}
        intent_dict = state.get("intent")
        if intent_dict is None:
            raise RuntimeError("intent-analyst returned no IntentReport")
        return IntentReport.model_validate(intent_dict)

    @staticmethod
    def _format_report(r: IntentReport) -> str:
        lines = [
            f"Topic:      {r.topic}",
            f"Audience:   {r.audience}",
            f"Purpose:    {r.purpose}",
            f"Tone:       {r.tone}",
            f"Slides:     {r.slide_count_hint}",
            f"Language:   {r.language}",
            f"Sections:   {', '.join(r.required_sections) or '(none)'}",
            f"Visuals:    {', '.join(r.visuals_hint) or '(none)'}",
            f"Research:   {', '.join(r.research_queries) or '(none)'}",
        ]
        return "\n".join(lines)
