"""Runtime plugin contract - core execution orchestration."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from .plugin import BasePlugin


RUN_STOP_COMPLETED = "completed"
RUN_STOP_FAILED = "failed"
RUN_STOP_CANCELLED = "cancelled"
RUN_STOP_TIMEOUT = "timeout"


@dataclass
class RunBudget:
    """Optional execution budget for a single run."""

    max_steps: int | None = None
    max_duration_ms: int | None = None
    max_tool_calls: int | None = None


@dataclass
class RunArtifact:
    """Artifact emitted by a run."""

    name: str
    kind: str = "generic"
    payload: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class RunUsage:
    """Usage statistics collected during a run."""

    llm_calls: int = 0
    tool_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0


@dataclass
class RunRequest:
    """Structured runtime request."""

    agent_id: str
    session_id: str
    input_text: str
    run_id: str = field(default_factory=lambda: str(uuid4()))
    parent_run_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    context_hints: dict[str, Any] = field(default_factory=dict)
    budget: RunBudget | None = None


@dataclass
class RunResult:
    """Structured runtime result."""

    run_id: str
    final_output: Any = None
    stop_reason: str = RUN_STOP_COMPLETED
    usage: RunUsage = field(default_factory=RunUsage)
    artifacts: list[RunArtifact] = field(default_factory=list)
    error: str | None = None
    exception: Exception | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


class RuntimePlugin(BasePlugin):
    """Base runtime plugin.

    Implementations control the execution lifecycle, orchestration flow,
    and how agents are run. Runtime is the top-level coordinator.
    """

    async def initialize(self) -> None:
        """Initialize runtime before first use.

        Called once during Runtime startup. Use for:
        - Loading configurations
        - Establishing connections
        - Setting up resources
        """
        pass

    async def validate(self) -> None:
        """Validate runtime configuration.

        Called after initialize(). Should raise if configuration is invalid.
        """
        pass

    async def health_check(self) -> bool:
        """Check runtime health status.

        Returns:
            True if runtime is healthy, False otherwise
        """
        return True

    async def run(
        self,
        *,
        request: RunRequest,
        **kwargs: Any,
    ) -> RunResult:
        """Execute an agent run with the given request.

        Args:
            request: Structured run request
            **kwargs: Runtime-specific execution dependencies

        Returns:
            Structured execution result
        """
        raise NotImplementedError("RuntimePlugin.run must be implemented")

    async def pause(self) -> None:
        """Pause runtime execution.

        Suspends any ongoing runs. State should be preserved.
        """
        pass

    async def resume(self) -> None:
        """Resume runtime execution.

        Continues previously paused runs.
        """
        pass

    async def close(self) -> None:
        """Cleanup runtime resources.

        Called during Runtime shutdown. Use for:
        - Closing connections
        - Flushing buffers
        - Releasing resources
        """
        pass


# Capability constants for runtime plugins
RUNTIME_RUN = "runtime.run"
RUNTIME_MANAGE = "runtime.manage"  # start/stop/pause runtime
RUNTIME_LIFECYCLE = "runtime.lifecycle"  # initialize/validate/health_check
