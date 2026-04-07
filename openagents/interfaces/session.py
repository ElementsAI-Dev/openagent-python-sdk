"""Session manager plugin contract - session lifecycle and isolation."""

from __future__ import annotations

from copy import deepcopy
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, AsyncIterator

from .plugin import BasePlugin


_TRANSCRIPT_KEY = "_session_transcript"
_ARTIFACTS_KEY = "_session_artifacts"
_CHECKPOINTS_KEY = "_session_checkpoints"


@dataclass
class SessionArtifact:
    """Stored artifact associated with a session."""

    name: str
    kind: str = "generic"
    payload: Any = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionArtifact":
        return cls(
            name=str(data.get("name", "")),
            kind=str(data.get("kind", "generic")),
            payload=data.get("payload"),
            metadata=dict(data.get("metadata", {})),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "kind": self.kind,
            "payload": deepcopy(self.payload),
            "metadata": deepcopy(self.metadata),
        }


@dataclass
class SessionCheckpoint:
    """Named checkpoint of session state."""

    checkpoint_id: str
    state: dict[str, Any]
    transcript_length: int = 0
    artifact_count: int = 0
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionCheckpoint":
        return cls(
            checkpoint_id=str(data.get("checkpoint_id", "")),
            state=deepcopy(dict(data.get("state", {}))),
            transcript_length=int(data.get("transcript_length", 0)),
            artifact_count=int(data.get("artifact_count", 0)),
            created_at=str(data.get("created_at", "")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "checkpoint_id": self.checkpoint_id,
            "state": deepcopy(self.state),
            "transcript_length": self.transcript_length,
            "artifact_count": self.artifact_count,
            "created_at": self.created_at,
        }


class SessionManagerPlugin(BasePlugin):
    """Base session manager plugin.

    Implementations control session lifecycle, locking strategy,
    and state persistence. Enables distributed session management.
    """

    @asynccontextmanager
    async def session(self, session_id: str) -> AsyncIterator[dict[str, Any]]:
        """Acquire and manage a session.

        Args:
            session_id: Unique session identifier

        Yields:
            Session state dict that can be used to store/restore state
        """
        raise NotImplementedError("SessionManagerPlugin.session must be implemented")

    async def get_state(self, session_id: str) -> dict[str, Any]:
        """Get current session state without acquiring lock.

        Args:
            session_id: Session identifier

        Returns:
            Session state dict
        """
        raise NotImplementedError("SessionManagerPlugin.get_state must be implemented")

    async def set_state(self, session_id: str, state: dict[str, Any]) -> None:
        """Set session state.

        Args:
            session_id: Session identifier
            state: State dict to persist
        """
        raise NotImplementedError("SessionManagerPlugin.set_state must be implemented")

    async def delete_session(self, session_id: str) -> None:
        """Delete a session and its state.

        Args:
            session_id: Session identifier
        """
        raise NotImplementedError("SessionManagerPlugin.delete_session must be implemented")

    async def list_sessions(self) -> list[str]:
        """List all active session IDs.

        Returns:
            List of session IDs
        """
        raise NotImplementedError("SessionManagerPlugin.list_sessions must be implemented")

    async def append_message(self, session_id: str, message: dict[str, Any]) -> None:
        """Append a message to the session transcript."""
        state = await self.get_state(session_id)
        transcript = list(state.get(_TRANSCRIPT_KEY, []))
        transcript.append(deepcopy(message))
        state[_TRANSCRIPT_KEY] = transcript
        await self.set_state(session_id, state)

    async def load_messages(self, session_id: str) -> list[dict[str, Any]]:
        """Load the full transcript for a session."""
        state = await self.get_state(session_id)
        return deepcopy(list(state.get(_TRANSCRIPT_KEY, [])))

    async def save_artifact(self, session_id: str, artifact: SessionArtifact) -> None:
        """Save an artifact for a session."""
        state = await self.get_state(session_id)
        artifacts = list(state.get(_ARTIFACTS_KEY, []))
        artifacts.append(artifact.to_dict())
        state[_ARTIFACTS_KEY] = artifacts
        await self.set_state(session_id, state)

    async def list_artifacts(self, session_id: str) -> list[SessionArtifact]:
        """List stored artifacts for a session."""
        state = await self.get_state(session_id)
        artifacts = state.get(_ARTIFACTS_KEY, [])
        return [SessionArtifact.from_dict(item) for item in deepcopy(list(artifacts))]

    async def create_checkpoint(
        self,
        session_id: str,
        checkpoint_id: str,
    ) -> SessionCheckpoint:
        """Create a checkpoint for a session."""
        state = await self.get_state(session_id)
        transcript = list(state.get(_TRANSCRIPT_KEY, []))
        artifacts = list(state.get(_ARTIFACTS_KEY, []))
        checkpoints = dict(state.get(_CHECKPOINTS_KEY, {}))
        checkpoint = SessionCheckpoint(
            checkpoint_id=checkpoint_id,
            state=deepcopy(state),
            transcript_length=len(transcript),
            artifact_count=len(artifacts),
        )
        checkpoints[checkpoint_id] = checkpoint.to_dict()
        state[_CHECKPOINTS_KEY] = checkpoints
        await self.set_state(session_id, state)
        return checkpoint

    async def load_checkpoint(
        self,
        session_id: str,
        checkpoint_id: str,
    ) -> SessionCheckpoint | None:
        """Load a checkpoint by id."""
        state = await self.get_state(session_id)
        checkpoints = dict(state.get(_CHECKPOINTS_KEY, {}))
        raw = checkpoints.get(checkpoint_id)
        if raw is None:
            return None
        return SessionCheckpoint.from_dict(deepcopy(raw))

    async def close(self) -> None:
        """Cleanup session manager resources."""
        pass


# Capability constants
SESSION_MANAGE = "session.manage"
SESSION_STATE = "session.state"
SESSION_TRANSCRIPT = "session.transcript"
SESSION_ARTIFACTS = "session.artifacts"
SESSION_CHECKPOINTS = "session.checkpoints"
