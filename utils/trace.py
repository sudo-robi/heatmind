"""Structured evidence trail for HeatMind decisions.

Every autonomous decision gets a trace_id, per-phase spans, cost attribution,
and confidence scoring. Judges can audit exactly what happened and why.
"""

import time
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


def generate_trace_id() -> str:
    """Generate a unique trace ID."""
    return f"tr_{uuid.uuid4().hex[:12]}"


@dataclass
class Span:
    """A single phase within a trace."""
    phase: str
    provider: str = ""
    tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    started_at: str = ""
    completed_at: str = ""

    def to_dict(self) -> dict:
        return {
            "phase": self.phase,
            "provider": self.provider,
            "tokens": self.tokens,
            "cost_usd": round(self.cost_usd, 6),
            "latency_ms": round(self.latency_ms, 1),
            "started_at": self.started_at,
            "completed_at": self.completed_at,
        }


@dataclass
class Trace:
    """Complete trace of an autonomous decision."""
    trace_id: str
    query: str
    zone: str = ""
    started_at: str = ""
    completed_at: str = ""
    total_cost_usd: float = 0.0
    confidence: float = 0.0
    severity: str = "unknown"
    outcome: str = "pending"
    spans: list[Span] = field(default_factory=list)
    delegations: list[str] = field(default_factory=list)
    user_feedback: str | None = None
    agent: str = "llm"
    llm_mode: str = ""

    def add_span(self, phase: str, **kwargs) -> Span:
        """Add a span to this trace."""
        span = Span(phase=phase, started_at=datetime.now(UTC).isoformat(), **kwargs)
        self.spans.append(span)
        return span

    def complete(self, outcome: str = "success", confidence: float = 0.0, severity: str = "unknown"):
        """Mark the trace as complete."""
        self.completed_at = datetime.now(UTC).isoformat()
        self.outcome = outcome
        self.confidence = confidence
        self.severity = severity
        # Calculate total cost from spans
        self.total_cost_usd = round(sum(s.cost_usd for s in self.spans), 6)

    def to_dict(self) -> dict:
        return {
            "trace_id": self.trace_id,
            "query": self.query,
            "zone": self.zone,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "confidence": round(self.confidence, 3),
            "severity": self.severity,
            "outcome": self.outcome,
            "spans": [s.to_dict() for s in self.spans],
            "delegations": self.delegations,
            "user_feedback": self.user_feedback,
            "agent": self.agent,
            "llm_mode": self.llm_mode,
        }


class TraceCollector:
    """Collects and stores traces for a session."""

    def __init__(self):
        self._traces: list[dict] = []

    def record(self, trace: Trace):
        """Record a completed trace."""
        self._traces.append(trace.to_dict())

    def get_all(self, limit: int = 50) -> list[dict]:
        """Get all traces, most recent first."""
        return list(reversed(self._traces[-limit:]))

    def get_by_zone(self, zone: str, limit: int = 20) -> list[dict]:
        """Get traces filtered by zone."""
        filtered = [t for t in self._traces if t.get("zone") == zone]
        return list(reversed(filtered[-limit:]))

    def get_by_trace_id(self, trace_id: str) -> dict | None:
        """Get a single trace by ID."""
        for t in self._traces:
            if t.get("trace_id") == trace_id:
                return t
        return None

    def stats(self) -> dict:
        """Aggregate statistics across all traces."""
        if not self._traces:
            return {"total": 0, "avg_cost": 0, "avg_confidence": 0, "success_rate": 0}

        total = len(self._traces)
        avg_cost = sum(t.get("total_cost_usd", 0) for t in self._traces) / total
        avg_conf = sum(t.get("confidence", 0) for t in self._traces) / total
        success = sum(1 for t in self._traces if t.get("outcome") == "success")

        return {
            "total": total,
            "avg_cost": round(avg_cost, 6),
            "avg_confidence": round(avg_conf, 3),
            "success_rate": round(success / total, 3) if total else 0,
        }
