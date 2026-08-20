"""Structured Handoff Documents — formal protocol for inter-agent transfer.

Defines a typed handoff protocol so agents pass context, deliverables,
and quality expectations explicitly — no implicit state leakage.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class HandoffDocument:
    """A formal handoff between two agents."""

    from_agent: str
    to_agent: str
    context: dict[str, Any]
    deliverable: str
    quality_expectations: list[str]
    timeout_seconds: int = 120
    priority: str = "normal"
    created_at: str = ""

    def __post_init__(self) -> None:
        if not self.created_at:
            self.created_at = datetime.now(UTC).isoformat()

    def to_dict(self) -> dict[str, Any]:
        return {
            "from_agent": self.from_agent,
            "to_agent": self.to_agent,
            "context": self.context,
            "deliverable": self.deliverable,
            "quality_expectations": self.quality_expectations,
            "timeout_seconds": self.timeout_seconds,
            "priority": self.priority,
            "created_at": self.created_at,
        }


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------


def create_handoff(
    from_agent: str,
    to_agent: str,
    context: dict[str, Any],
    deliverable: str,
    quality_expectations: list[str],
    timeout_seconds: int = 120,
    priority: str = "normal",
) -> HandoffDocument:
    """Create a validated handoff document."""
    doc = HandoffDocument(
        from_agent=from_agent,
        to_agent=to_agent,
        context=context,
        deliverable=deliverable,
        quality_expectations=quality_expectations,
        timeout_seconds=timeout_seconds,
        priority=priority,
    )
    errors = validate_handoff(doc)
    if errors:
        raise ValueError(f"Invalid handoff: {'; '.join(errors)}")
    return doc


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

_REQUIRED_FIELDS = ["from_agent", "to_agent", "deliverable"]
_VALID_PRIORITIES = {"normal", "high", "critical"}


def validate_handoff(handoff: HandoffDocument) -> list[str]:
    """Validate a handoff document. Returns a list of error messages (empty = valid)."""
    errors: list[str] = []

    for field_name in _REQUIRED_FIELDS:
        value = getattr(handoff, field_name, None)
        if not value or (isinstance(value, str) and not value.strip()):
            errors.append(f"Missing required field: {field_name}")

    if not isinstance(handoff.context, dict):
        errors.append("Context must be a dict")
    elif not handoff.context:
        errors.append("Context cannot be empty")

    if not isinstance(handoff.quality_expectations, list):
        errors.append("Quality expectations must be a list")
    elif not handoff.quality_expectations:
        errors.append("Quality expectations cannot be empty")

    if handoff.priority not in _VALID_PRIORITIES:
        errors.append(f"Invalid priority '{handoff.priority}'; must be one of: {', '.join(sorted(_VALID_PRIORITIES))}")

    if not isinstance(handoff.timeout_seconds, int) or handoff.timeout_seconds <= 0:
        errors.append("Timeout must be a positive integer")

    return errors


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def render_handoff_prompt(handoff: HandoffDocument) -> str:
    """Convert a HandoffDocument to an LLM-consumable string.

    The prompt is structured so the receiving agent understands:
    1. Who is handing off to them and why
    2. What context they have
    3. What deliverable they must produce
    4. What quality bar they must meet
    5. Time and priority constraints
    """
    priority_tag = handoff.priority.upper() if handoff.priority != "normal" else ""
    header = f"=== HANDOFF: {handoff.from_agent} -> {handoff.to_agent} ==="
    if priority_tag:
        header += f" [{priority_tag}]"

    context_lines = []
    for key, value in handoff.context.items():
        context_lines.append(f"  {key}: {value}")
    context_block = "\n".join(context_lines) if context_lines else "  (no context provided)"

    quality_lines = "\n".join(f"  - {q}" for q in handoff.quality_expectations)

    return f"""{header}

FROM: {handoff.from_agent}
TO: {handoff.to_agent}
PRIORITY: {handoff.priority}
TIMEOUT: {handoff.timeout_seconds}s
CREATED: {handoff.created_at}

## Context
{context_block}

## Your Deliverable
{handoff.deliverable}

## Quality Expectations
{quality_lines}

Produce the deliverable above. When done, return a JSON object:
{{"status": "complete", "output": "...", "issues": []}}"""
