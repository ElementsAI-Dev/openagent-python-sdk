from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TaskPlan:
    objective: str
    search_patterns: list[str]
    target_files: list[str]
    deliverables: list[str]
    success_criteria: list[str]
    risks_to_check: list[str]


@dataclass
class DeliveryEnvelope:
    summary: str
    root_cause: str
    recommended_changes: list[str]
    tests_to_run: list[str]
    risks: list[str]
    next_steps: list[str]


@dataclass
class VerificationEnvelope:
    summary: str
    commands: list[str]
    expectations: list[str]
    residual_risks: list[str]


@dataclass
class ProjectBlueprint:
    project_name: str
    package_name: str
    project_type: str
    summary: str
    goals: list[str]
    generated_files: list[str]
    verification_commands: list[str]


@dataclass
class BenchmarkTask:
    task_id: str
    prompt: str
    expected_files: list[str] = field(default_factory=list)
    expected_artifacts: list[str] = field(default_factory=list)
    expected_summary_terms: list[str] = field(default_factory=list)
    expected_generated_files: list[str] = field(default_factory=list)


@dataclass
class BenchmarkResult:
    task_id: str
    passed: bool
    summary: str
    matched_files: list[str]
    artifacts: list[str]
    generated_files: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
