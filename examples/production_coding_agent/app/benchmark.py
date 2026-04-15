from __future__ import annotations

import json
import shutil
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import openagents.llm.registry as llm_registry
from openagents.llm.base import LLMClient
from openagents.runtime.runtime import Runtime

from .protocols import BenchmarkResult, BenchmarkTask


class DeterministicBenchmarkLLM(LLMClient):
    async def complete(
        self,
        *,
        messages: list[dict[str, str]],
        model: str | None = None,
        temperature: float | None = None,
        max_tokens: int | None = None,
        tools: list[dict] | None = None,
        tool_choice: dict | None = None,
        response_format: dict | None = None,
    ) -> str:
        _ = (model, temperature, max_tokens, tools, tool_choice, response_format)
        user_text = ""
        for item in reversed(messages):
            if item.get("role") == "user":
                user_text = item.get("content", "")
                break
        if "PURPOSE: planning" in user_text:
            return json.dumps(
                {
                    "objective": "Investigate API client configuration flow",
                    "search_patterns": ["API_BASE_URL", "load_settings", "timeout"],
                    "target_files": ["app/config.py", "app/service.py", "tests/test_service.py"],
                    "deliverables": ["delivery-report.md", "patch-plan.md", "verification-report.md"],
                    "success_criteria": ["Identify hotspot", "Produce delivery report", "Produce next steps"],
                    "risks_to_check": ["Missing validation", "Weak tests"],
                },
                ensure_ascii=False,
            )
        if "PURPOSE: project_blueprint" in user_text:
            return json.dumps(
                {
                    "project_name": "todo-cli-app",
                    "package_name": "todo_cli_app",
                    "project_type": "python_cli",
                    "summary": "A complete Python CLI project for task tracking.",
                    "goals": [
                        "Scaffold a runnable Python project",
                        "Provide a CLI entrypoint",
                        "Ship tests and documentation",
                    ],
                    "generated_files": [
                        "README.md",
                        "pyproject.toml",
                        "src/todo_cli_app/__init__.py",
                        "src/todo_cli_app/service.py",
                        "src/todo_cli_app/cli.py",
                        "tests/test_service.py",
                        ".gitignore",
                    ],
                    "verification_commands": ["python -m py_compile src/**/*.py", "pytest -q"],
                },
                ensure_ascii=False,
            )
        if "PURPOSE: delivery" in user_text:
            return json.dumps(
                {
                    "summary": "已完成仓库检查，并生成可执行的交付报告与补丁计划。",
                    "root_cause": "当前实现依赖环境输入，但配置边界和回归验证说明不够集中。",
                    "recommended_changes": [
                        "集中收敛 API client 配置入口",
                        "补充对空 key 与基础配置边界的测试",
                        "在交付说明中明确运行与回退策略",
                    ],
                    "tests_to_run": ["pytest -q", "针对配置边界的定向回归测试"],
                    "risks": ["后续变更可能引入新的配置分叉", "文档与代码可能再次漂移"],
                    "next_steps": ["评审补丁计划", "实施最小修改", "跑定向验证"],
                },
                ensure_ascii=False,
            )
        return json.dumps({"type": "final", "content": "unexpected"}, ensure_ascii=False)


def _example_root() -> Path:
    return Path("examples/production_coding_agent")


def _outputs_root() -> Path:
    return _example_root() / "outputs"


def _memory_root() -> Path:
    return _example_root() / ".agent_memory"


def load_tasks(path: Path | None = None) -> list[BenchmarkTask]:
    task_path = path or (_example_root() / "benchmarks" / "tasks.json")
    payload = json.loads(task_path.read_text(encoding="utf-8"))
    return [BenchmarkTask(**item) for item in payload]


def cleanup_generated_files() -> None:
    for path in (
        _outputs_root() / "task-brief.json",
        _outputs_root() / "delivery-report.md",
        _outputs_root() / "patch-plan.md",
        _outputs_root() / "verification-report.md",
    ):
        if path.exists():
            path.unlink()
    if _memory_root().exists():
        shutil.rmtree(_memory_root())


@contextmanager
def patched_llm(factory: Any) -> Iterator[None]:
    original = llm_registry.create_llm_client
    llm_registry.create_llm_client = factory
    try:
        yield
    finally:
        llm_registry.create_llm_client = original


async def run_benchmark(*, tasks: list[BenchmarkTask] | None = None) -> list[BenchmarkResult]:
    benchmark_tasks = tasks or load_tasks()
    results: list[BenchmarkResult] = []
    with patched_llm(lambda llm: DeterministicBenchmarkLLM()):
        runtime = Runtime.from_config(_example_root() / "agent.json")
        try:
            for task in benchmark_tasks:
                cleanup_generated_files()
                output = await runtime.run(
                    agent_id="production-coding-agent",
                    session_id=f"benchmark-{task.task_id}",
                    input_text=task.prompt,
                )
                summary = str(output.get("summary", ""))
                matched_files = list(output.get("matched_files", []))
                artifacts = [Path(item).name for item in output.get("artifacts", [])]
                generated_files = list(output.get("generated_files", []))
                notes: list[str] = []
                for item in task.expected_files:
                    if item not in matched_files:
                        notes.append(f"missing expected file: {item}")
                for item in task.expected_artifacts:
                    if item not in artifacts:
                        notes.append(f"missing expected artifact: {item}")
                for item in task.expected_summary_terms:
                    if item not in summary:
                        notes.append(f"summary missing term: {item}")
                for item in task.expected_generated_files:
                    if item not in generated_files:
                        notes.append(f"missing generated file: {item}")
                results.append(
                    BenchmarkResult(
                        task_id=task.task_id,
                        passed=not notes,
                        summary=summary,
                        matched_files=matched_files,
                        artifacts=artifacts,
                        generated_files=generated_files,
                        notes=notes,
                    )
                )
        finally:
            await runtime.close()
            cleanup_generated_files()
    return results
