"""Pretty-printing event bus for the pptx-agent CLI.

Wraps an inner ``async`` bus (standard delivery) and renders a curated
subset of events as Rich renderables tuned for tool calls and LLM
activity. Noise events (memory.*, context.*, session.*, run.*) are
suppressed by default so the wizard UI stays readable.

Tavily-aware result formatting: when a tool returns a dict with a
``results`` list, each result is shown as a compact table of
title/url/snippet instead of dumping raw JSON.
"""

from __future__ import annotations

import fnmatch
import time
from typing import Any, Awaitable, Callable, Literal

from pydantic import BaseModel, Field

from openagents.interfaces.events import (
    EVENT_EMIT,
    EVENT_HISTORY,
    EVENT_SUBSCRIBE,
    EventBusPlugin,
    RuntimeEvent,
)
from openagents.observability._rich import make_console

_DEFAULT_EXCLUDES = [
    "memory.*",
    "context.*",
    "session.*",
    "run.*",
    "usage.*",
]

_TOOL_ICON = "🔧"
_TOOL_OK_ICON = "✓"
_TOOL_FAIL_ICON = "✗"
_LLM_ICON = "🧠"


def _matches_any(name: str, patterns: list[str]) -> bool:
    return any(fnmatch.fnmatchcase(name, pat) for pat in patterns)


class PrettyEventBus(EventBusPlugin):
    """Rich event bus with tool/LLM-aware formatting.

    Config:
        inner: dict                -- inner bus ref (default async)
        include_events: list[str]? -- if set, only render matching names
        exclude_events: list[str]  -- deny-list (wins over include); defaults
                                      to a sensible noise suppression set
        stream: "stdout" | "stderr" (default "stderr")
        show_details: bool         -- include per-field breakdown (default True)
    """

    class Config(BaseModel):
        inner: dict[str, Any] = Field(default_factory=lambda: {"type": "async"})
        include_events: list[str] | None = None
        exclude_events: list[str] = Field(default_factory=lambda: list(_DEFAULT_EXCLUDES))
        stream: Literal["stdout", "stderr"] = "stderr"
        show_details: bool = True
        max_history: int = 10_000

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(
            config=config or {},
            capabilities={EVENT_SUBSCRIBE, EVENT_EMIT, EVENT_HISTORY},
        )
        cfg = self.Config.model_validate(self.config)
        self._include = list(cfg.include_events) if cfg.include_events is not None else None
        self._exclude = list(cfg.exclude_events)
        self._show_details = cfg.show_details
        self._console = make_console(cfg.stream)
        inner_ref = dict(cfg.inner)
        inner_cfg = dict(inner_ref.get("config") or {})
        inner_cfg.setdefault("max_history", cfg.max_history)
        inner_ref["config"] = inner_cfg
        self._inner = self._load_inner(inner_ref)
        self._tool_start_ns: dict[str, int] = {}
        self._llm_start_ns: dict[str, int] = {}

    def _load_inner(self, ref: dict[str, Any]) -> Any:
        from openagents.config.schema import EventBusRef
        from openagents.plugins.loader import load_plugin

        return load_plugin("events", EventBusRef(**ref), required_methods=("emit", "subscribe"))

    def _should_render(self, event_name: str) -> bool:
        if self._exclude and _matches_any(event_name, self._exclude):
            return False
        if self._include is None:
            return True
        return _matches_any(event_name, self._include)

    @property
    def history(self) -> list[RuntimeEvent]:
        return getattr(self._inner, "history", [])

    def subscribe(
        self,
        event_name: str,
        handler: Callable[[RuntimeEvent], Awaitable[None] | None],
    ) -> None:
        self._inner.subscribe(event_name, handler)

    async def emit(self, event_name: str, **payload: Any) -> RuntimeEvent:
        event = await self._inner.emit(event_name, **payload)
        if self._should_render(event_name):
            try:
                self._render(event_name, payload)
            except Exception:
                # never disrupt event delivery; swallow render errors
                pass
        return event

    async def get_history(
        self, event_name: str | None = None, limit: int | None = None
    ) -> list[RuntimeEvent]:
        return await self._inner.get_history(event_name=event_name, limit=limit)

    async def clear_history(self) -> None:
        await self._inner.clear_history()

    # --------------------------------------------------------------- render
    def _render(self, name: str, payload: dict[str, Any]) -> None:
        if name == "tool.called":
            self._render_tool_called(payload)
        elif name == "tool.succeeded":
            self._render_tool_succeeded(payload)
        elif name == "tool.failed":
            self._render_tool_failed(payload)
        elif name == "llm.called":
            self._render_llm_called(payload)
        elif name == "llm.succeeded":
            self._render_llm_succeeded(payload)
        else:
            self._render_generic(name, payload)

    def _render_tool_called(self, payload: dict[str, Any]) -> None:
        from rich.text import Text

        tool_id = str(payload.get("tool_id") or "?")
        params = payload.get("params") or {}
        self._tool_start_ns[tool_id] = time.monotonic_ns()

        line = Text()
        line.append(f"{_TOOL_ICON} ", style="bold cyan")
        line.append(tool_id, style="bold")
        if params:
            primary_key = self._pick_primary_param_key(params)
            if primary_key is not None:
                line.append("  ")
                line.append(str(params[primary_key])[:120], style="yellow")
            extra = {k: v for k, v in params.items() if k != primary_key}
            if extra and self._show_details:
                line.append(
                    "  " + ", ".join(f"{k}={self._short(v)}" for k, v in extra.items()),
                    style="dim",
                )
        self._console.print(line)

    def _render_tool_succeeded(self, payload: dict[str, Any]) -> None:
        from rich.panel import Panel
        from rich.table import Table
        from rich.text import Text

        tool_id = str(payload.get("tool_id") or "?")
        result = payload.get("result")
        elapsed_ms = self._pop_elapsed(self._tool_start_ns, tool_id)

        header = Text()
        header.append(f"{_TOOL_OK_ICON} ", style="bold green")
        header.append(tool_id, style="bold")
        if elapsed_ms is not None:
            header.append(f"  {elapsed_ms} ms", style="dim")

        # Tavily-shaped: {"results": [{url, title, content|snippet, ...}, ...]}
        if isinstance(result, dict) and isinstance(result.get("results"), list) and result["results"]:
            table = Table(show_header=True, header_style="bold", expand=False, pad_edge=False)
            table.add_column("#", width=3, style="dim")
            table.add_column("Title", overflow="ellipsis", max_width=42)
            table.add_column("URL", overflow="ellipsis", max_width=48, style="blue")
            table.add_column("Snippet", overflow="ellipsis", max_width=60, style="dim")
            for i, item in enumerate(result["results"][:5], start=1):
                if not isinstance(item, dict):
                    continue
                table.add_row(
                    str(i),
                    str(item.get("title") or ""),
                    str(item.get("url") or ""),
                    str(item.get("content") or item.get("snippet") or "")[:120],
                )
            more = len(result["results"]) - 5
            footer = Text()
            if more > 0:
                footer.append(f"(+{more} more)", style="dim italic")
            self._console.print(Panel(table, title=header, title_align="left", border_style="green"))
            if more > 0:
                self._console.print(footer)
            return

        # Short scalar / dict summary
        summary = self._summarize_result(result)
        if summary:
            header.append("  ")
            header.append(summary, style="dim")
        self._console.print(header)

    def _render_tool_failed(self, payload: dict[str, Any]) -> None:
        from rich.text import Text

        tool_id = str(payload.get("tool_id") or "?")
        err = str(payload.get("error") or "")
        elapsed_ms = self._pop_elapsed(self._tool_start_ns, tool_id)

        line = Text()
        line.append(f"{_TOOL_FAIL_ICON} ", style="bold red")
        line.append(tool_id, style="bold red")
        if elapsed_ms is not None:
            line.append(f"  {elapsed_ms} ms", style="dim")
        if err:
            line.append("  ")
            line.append(err[:200], style="red")
        self._console.print(line)

    def _render_llm_called(self, payload: dict[str, Any]) -> None:
        from rich.text import Text

        model = str(payload.get("model") or "?")
        self._llm_start_ns[model] = time.monotonic_ns()
        line = Text()
        line.append(f"{_LLM_ICON} ", style="bold magenta")
        line.append(model, style="bold")
        line.append("  thinking…", style="dim italic")
        self._console.print(line)

    def _render_llm_succeeded(self, payload: dict[str, Any]) -> None:
        from rich.text import Text

        model = str(payload.get("model") or "?")
        elapsed_ms = self._pop_elapsed(self._llm_start_ns, model)
        line = Text()
        line.append(f"{_LLM_ICON} ", style="bold magenta")
        line.append(model, style="bold")
        if elapsed_ms is not None:
            line.append(f"  {elapsed_ms} ms", style="dim")
        self._console.print(line)

    def _render_generic(self, name: str, payload: dict[str, Any]) -> None:
        from rich.text import Text

        line = Text()
        line.append("·  ", style="dim")
        line.append(name, style="bold dim")
        if payload and self._show_details:
            bits = [f"{k}={self._short(v)}" for k, v in payload.items()]
            line.append("  ")
            line.append(" ".join(bits)[:200], style="dim")
        self._console.print(line)

    # --------------------------------------------------------------- utils
    @staticmethod
    def _pick_primary_param_key(params: dict[str, Any]) -> str | None:
        for preferred in ("query", "command", "path", "url", "rule", "input_text"):
            if preferred in params:
                return preferred
        return next(iter(params), None)

    @staticmethod
    def _short(value: Any) -> str:
        if isinstance(value, str):
            return value if len(value) <= 40 else value[:37] + "…"
        if isinstance(value, (dict, list)):
            return f"{type(value).__name__}[{len(value)}]"
        return str(value)

    @staticmethod
    def _summarize_result(result: Any) -> str:
        if result is None:
            return ""
        if isinstance(result, dict):
            keys = list(result.keys())[:4]
            return "{" + ", ".join(keys) + ("…}" if len(result) > 4 else "}")
        if isinstance(result, list):
            return f"[{len(result)} items]"
        s = str(result)
        return s if len(s) <= 80 else s[:77] + "…"

    @staticmethod
    def _pop_elapsed(store: dict[str, int], key: str) -> int | None:
        start = store.pop(key, None)
        if start is None:
            return None
        return (time.monotonic_ns() - start) // 1_000_000
