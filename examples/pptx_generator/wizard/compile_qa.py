"""Stage 7 wizard step — compile JS templates + run node + QA via markitdown."""

from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openagents.cli.wizard import StepResult

from ..state import DeckProject, SlideIR


@dataclass
class CompileQAWizardStep:
    shell_tool: Any
    output_root: Path
    templates_dir: Path
    title: str = "compile"
    description: str = "Render JS, run PptxGenJS, QA via MarkItDown."

    async def render(self, console: Any, project: DeckProject) -> StepResult:
        out_dir = Path(self.output_root) / project.slug / "slides"
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "output").mkdir(exist_ok=True)

        for slide in project.slides:
            self._write_slide_file(out_dir, slide)

        (out_dir / "compile.js").write_text(self._compile_script(project), encoding="utf-8")

        pkg = out_dir / "package.json"
        if not pkg.exists():
            pkg.write_text(
                json.dumps(
                    {
                        "name": f"deck-{project.slug}",
                        "private": True,
                        "dependencies": {"pptxgenjs": "^3.12.0"},
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            await self.shell_tool.invoke(
                {"command": ["npm", "install"], "cwd": str(out_dir)},
                context=None,
            )

        await self.shell_tool.invoke(
            {"command": ["node", "compile.js"], "cwd": str(out_dir)},
            context=None,
        )

        # Optional QA via markitdown
        pptx = out_dir / "output" / "presentation.pptx"
        md_path = out_dir / "output" / "presentation.md"
        if shutil.which("markitdown") is not None:
            await self.shell_tool.invoke(
                {"command": ["markitdown", str(pptx), "-o", str(md_path)]},
                context=None,
            )

        project.stage = "done"
        return StepResult(status="completed")

    def _write_slide_file(self, out_dir: Path, slide: SlideIR) -> None:
        filename = f"slide-{slide.index:02d}.js"
        path = out_dir / filename
        if slide.type == "freeform" and slide.freeform_js:
            path.write_text(slide.freeform_js, encoding="utf-8")
            return
        template = (self.templates_dir / f"{slide.type}.js").read_text(encoding="utf-8")
        # Wrap the template so its `module.exports.createSlide(pres, theme, slots)`
        # is re-exported as a slots-closed-over `createSlide(pres, theme)`.
        content = (
            "const base = (function() {\n"
            "  var module = { exports: {} };\n"
            f"{template}\n"
            "  return module.exports;\n"
            "})();\n"
            f"const slots = {json.dumps(slide.slots, ensure_ascii=False)};\n"
            "function createSlide(pres, theme) { return base.createSlide(pres, theme, slots); }\n"
            "module.exports = { createSlide };\n"
        )
        path.write_text(content, encoding="utf-8")

    @staticmethod
    def _compile_script(project: DeckProject) -> str:
        theme_palette = project.theme.palette.model_dump() if project.theme else {}
        title = project.intent.topic if project.intent else "Deck"
        requires = "\n".join(
            f'  require("./slide-{s.index:02d}.js").createSlide(pres, theme);'
            for s in project.slides
        )
        return (
            'const pptxgen = require("pptxgenjs");\n\n'
            "async function main() {\n"
            "  const pres = new pptxgen();\n"
            '  pres.layout = "LAYOUT_16x9";\n'
            f'  pres.title = {json.dumps(title)};\n'
            f"  const theme = {json.dumps(theme_palette)};\n"
            f"{requires}\n"
            '  await pres.writeFile({ fileName: "./output/presentation.pptx" });\n'
            "}\n\n"
            "main().catch((err) => { console.error(err); process.exitCode = 1; });\n"
        )
