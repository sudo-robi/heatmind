"""Failure Mode Taxonomy — classify and recover from agent failures.

Seven failure types from agency-agents with classify/recover functions:
HARD, SILENT, PARTIAL, CONTRADICTION, CASCADE, LOOP, CONTEXT.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

logger = logging.getLogger(__name__)


class FailureType(StrEnum):
    """The seven canonical failure types."""

    HARD = "HARD"
    SILENT = "SILENT"
    PARTIAL = "PARTIAL"
    CONTRADICTION = "CONTRADICTION"
    CASCADE = "CASCADE"
    LOOP = "LOOP"
    CONTEXT = "CONTEXT"


@dataclass
class FailureRecord:
    """A classified failure with its recovery strategy."""

    type: FailureType
    error: str
    recovery_strategy: str
    attempts: int = 0
    resolved: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type.value,
            "error": self.error,
            "recovery_strategy": self.recovery_strategy,
            "attempts": self.attempts,
            "resolved": self.resolved,
        }


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


def classify(error: Any, context: dict[str, Any] | None = None) -> FailureType:
    """Determine the failure type from an error and optional context.

    Parameters
    ----------
    error:
        The exception, string message, or error dict.
    context:
        Additional context (previous errors, response schemas, iteration count, etc.).
    """
    ctx = context or {}
    error_str = _error_to_str(error)
    error_lower = error_str.lower()

    # 7. CONTEXT — context window exceeded
    if any(kw in error_lower for kw in ("context", "token limit", "max tokens", "too long", "exceeded")):
        return FailureType.CONTEXT

    # 1. HARD — explicit error codes, timeouts, connection failures
    if any(
        kw in error_lower for kw in ("timeout", "timed out", "connection", "500", "502", "503", "econnrefused", "eof")
    ):
        return FailureType.HARD

    # 4. CONTRADICTION — conflicting data signals
    if ctx.get("contradiction_detected") or "contradict" in error_lower:
        return FailureType.CONTRADICTION

    # 3. PARTIAL — partial data returned
    if ctx.get("partial") or "partial" in error_lower or "incomplete" in error_lower:
        return FailureType.PARTIAL

    # 5. CASCADE — dependent failure in chain
    if ctx.get("cascade") or "cascade" in error_lower or "dependency" in error_lower:
        return FailureType.CASCADE

    # 6. LOOP — stuck in iteration
    iter_count = ctx.get("iteration_count", 0)
    if iter_count >= 3 or "loop" in error_lower or "stuck" in error_lower:
        return FailureType.LOOP

    # 2. SILENT — no error but wrong/empty output
    if ctx.get("output_valid") is False or "wrong output" in error_lower or "unexpected" in error_lower:
        return FailureType.SILENT

    # Default: treat as HARD if we have an exception, SILENT if empty
    if error is None or error_str == "":
        return FailureType.SILENT

    return FailureType.HARD


def _error_to_str(error: Any) -> str:
    """Convert any error representation to a searchable string."""
    if error is None:
        return ""
    if isinstance(error, str):
        return error
    if isinstance(error, dict):
        return str(error.get("message", error.get("error", str(error))))
    if isinstance(error, Exception):
        return f"{type(error).__name__}: {error}"
    return str(error)


# ---------------------------------------------------------------------------
# Recovery strategies
# ---------------------------------------------------------------------------


def recover(
    failure_type: FailureType,
    error: Any,
    context: dict[str, Any] | None = None,
) -> str:
    """Return a recovery strategy for the given failure type.

    The strategy is a human-readable description of the recommended
    recovery action. A caller can parse this or extend it with code.
    """
    ctx = context or {}

    if failure_type == FailureType.HARD:
        attempts = ctx.get("attempts", 0)
        if attempts < 3:
            backoff = 2**attempts
            return f"Retry with exponential backoff ({backoff}s delay). Attempt {attempts + 1}/3."
        return "Max retries exceeded. Fall back to degraded mode or escalate to operator."

    if failure_type == FailureType.SILENT:
        return "Schema validation failed. Retry with explicit output format instructions and field-level constraints."

    if failure_type == FailureType.PARTIAL:
        missing = ctx.get("missing_fields", [])
        if missing:
            return f"Request specific missing fields: {', '.join(missing)}. Fill gaps with defaults where safe."
        return "Request specific missing fields and fill gaps with safe defaults."

    if failure_type == FailureType.CONTRADICTION:
        conflicting = ctx.get("conflicting_sources", [])
        if conflicting:
            return f"Arbitrate between conflicting sources: {', '.join(conflicting)}. Prefer authoritative source or escalate to human."
        return "Run arbitration logic to resolve conflicting data. Escalate to human if unresolvable."

    if failure_type == FailureType.CASCADE:
        checkpoint = ctx.get("last_checkpoint")
        if checkpoint:
            return f"Rollback to checkpoint '{checkpoint}' and re-run the failed dependency."
        return "Rollback to last known good state and re-run the dependency chain."

    if failure_type == FailureType.LOOP:
        last_best = ctx.get("last_best_output")
        if last_best:
            return f"Iteration stuck. Force exit and return last best output: {last_best}"
        return "Iteration stuck. Force exit with best available output and escalate."

    if failure_type == FailureType.CONTEXT:
        return "Context window exceeded. Compress context by summarizing earlier turns, then retry."

    return "Unknown failure type. Log details and escalate."
