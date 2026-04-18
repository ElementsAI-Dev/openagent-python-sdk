"""pptx-agent CLI entry point.

This file exposes ``main`` (async) and ``main_sync`` (entry point for
``project.scripts``). The ``run_wizard`` function is a stub in this task
— task T24 wires it to the full 7-step wizard.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

from .persistence import load_project, save_project
from .state import DeckProject


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="pptx-agent",
        description="Interactive PPT generator built on openagents.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_new = sub.add_parser("new", help="start a new deck")
    p_new.add_argument("--topic", help="initial topic prompt (optional)")
    p_new.add_argument("--slug", help="override project slug")

    p_resume = sub.add_parser("resume", help="resume an existing deck by slug")
    p_resume.add_argument("slug")

    p_memory = sub.add_parser("memory", help="list persisted memory entries")
    p_memory.add_argument(
        "--section",
        default=None,
        help="limit to a specific section (user_goals|user_feedback|decisions|references)",
    )
    return parser


_SLUG_CHAR_RE = re.compile(r"[^a-z0-9]+")
_MAX_BASE_LEN = 48  # leaves room for "-YYYYMMDD-HHMMSS" (16 chars) within 64-char limit


def _slugify(topic: str | None) -> str:
    base = _SLUG_CHAR_RE.sub("-", (topic or "deck").lower()).strip("-") or "deck"
    base = base[:_MAX_BASE_LEN].rstrip("-")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    return f"{base}-{stamp}"


def outputs_root() -> Path:
    return Path(os.environ.get("PPTX_AGENT_OUTPUTS", "examples/pptx_generator/outputs"))


async def run_wizard(
    project: DeckProject,
    *,
    resume: bool = False,
    runtime=None,
    shell_tool=None,
) -> int:
    """Stub: persist the project and return 0.

    Task T24 replaces this with the real 7-step wizard wiring.
    """
    save_project(project, root=outputs_root())
    return 0


async def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "new":
        slug = args.slug or _slugify(args.topic)
        project = DeckProject(
            slug=slug,
            created_at=datetime.now(timezone.utc),
            stage="intent",
        )
        save_project(project, root=outputs_root())
        return await run_wizard(project)
    if args.command == "resume":
        project = load_project(args.slug, root=outputs_root())
        return await run_wizard(project, resume=True)
    if args.command == "memory":
        from openagents.plugins.builtin.memory.markdown_memory import MarkdownMemory

        mem = MarkdownMemory(config={"memory_dir": "~/.config/pptx-agent/memory"})
        sections = [args.section] if args.section else mem.cfg.sections
        for s in sections:
            print(f"## {s}")
            for e in mem.list_entries(s):
                print(f"- [{e['id']}] {e['rule']}  — {e['reason']}")
        return 0
    return 1


def main_sync() -> int:
    return asyncio.run(main(sys.argv[1:]))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main_sync())
