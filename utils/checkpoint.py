"""Checkpoint system for HeatMind agent state snapshots.

Saves state at logical points for rollback and resumption.
"""

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime

from memory.session import SessionMemory


@dataclass
class Checkpoint:
    """A state snapshot at a logical point in the agent pipeline."""

    checkpoint_id: str
    name: str
    timestamp: str
    phase: str
    observations: dict
    trace: list
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "checkpoint_id": self.checkpoint_id,
            "name": self.name,
            "timestamp": self.timestamp,
            "phase": self.phase,
            "observations": self.observations,
            "trace": self.trace,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Checkpoint":
        return cls(
            checkpoint_id=data.get("checkpoint_id", ""),
            name=data.get("name", ""),
            timestamp=data.get("timestamp", ""),
            phase=data.get("phase", ""),
            observations=data.get("observations", {}),
            trace=data.get("trace", []),
            metadata=data.get("metadata", {}),
        )


class CheckpointManager:
    """Manages checkpoint storage, retrieval, and rollback via SessionMemory."""

    def __init__(self, memory: SessionMemory | None = None):
        self._memory = memory or SessionMemory()
        self._local_checkpoints: dict[str, Checkpoint] = {}
        self._session_id: str | None = None

    def _ensure_session(self) -> str:
        if self._session_id is None:
            self._session_id = self._memory.create_session(user_id="checkpoint_manager")
        return self._session_id

    def save_checkpoint(
        self,
        name: str,
        phase: str,
        observations: dict,
        trace: list,
        metadata: dict | None = None,
    ) -> str:
        """Save a checkpoint and return its ID."""
        cp_id = f"cp_{uuid.uuid4().hex[:12]}"
        checkpoint = Checkpoint(
            checkpoint_id=cp_id,
            name=name,
            timestamp=datetime.now(UTC).isoformat(),
            phase=phase,
            observations=observations,
            trace=trace,
            metadata=metadata or {},
        )
        self._local_checkpoints[cp_id] = checkpoint
        session_id = self._ensure_session()
        self._memory.update_session_context(session_id, f"checkpoint.{cp_id}", checkpoint.to_dict())
        return cp_id

    def load_checkpoint(self, checkpoint_id: str) -> Checkpoint | None:
        """Load a checkpoint by ID."""
        if checkpoint_id in self._local_checkpoints:
            return self._local_checkpoints[checkpoint_id]
        session_id = self._ensure_session()
        ctx = self._memory.get_session_context(session_id)
        cp_data = ctx.get(f"checkpoint.{checkpoint_id}")
        if cp_data:
            return Checkpoint.from_dict(cp_data)
        return None

    def list_checkpoints(self) -> list[dict]:
        """List all checkpoints (id, name, phase, timestamp)."""
        result = []
        for cp in self._local_checkpoints.values():
            result.append(
                {
                    "checkpoint_id": cp.checkpoint_id,
                    "name": cp.name,
                    "phase": cp.phase,
                    "timestamp": cp.timestamp,
                }
            )
        if not result and self._session_id:
            ctx = self._memory.get_session_context(self._session_id)
            for key, val in ctx.items():
                if key.startswith("checkpoint.") and isinstance(val, dict):
                    result.append(
                        {
                            "checkpoint_id": val.get("checkpoint_id", ""),
                            "name": val.get("name", ""),
                            "phase": val.get("phase", ""),
                            "timestamp": val.get("timestamp", ""),
                        }
                    )
        return sorted(result, key=lambda x: x.get("timestamp", ""), reverse=True)

    def rollback_to(self, checkpoint_id: str) -> dict | None:
        """Return checkpoint data for rollback."""
        cp = self.load_checkpoint(checkpoint_id)
        if cp is None:
            return None
        return {
            "phase": cp.phase,
            "observations": cp.observations,
            "trace": cp.trace,
            "metadata": cp.metadata,
        }

    def auto_checkpoint(self, phase: str, observations: dict, trace: list) -> str:
        """Save automatically at phase boundaries."""
        name = f"auto_{phase}_{datetime.now(UTC).strftime('%H%M%S')}"
        return self.save_checkpoint(name, phase, observations, trace, {"auto": True})
