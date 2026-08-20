"""Trust scoring engine for HeatMind.

Trust starts at 0.5 (neutral) and increases/decreases based on outcomes.
High-stakes actions (alerts, escalations) require trust above a threshold
before auto-executing — otherwise the system asks for human approval.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)

# Trust thresholds for different action types
TRUST_GATES = {
    "send_alert": 0.6,
    "emergency_escalation": 0.7,
    "daily_report": 0.3,
    "deep_analysis": 0.4,
}

# Trust adjustment amounts
TRUST_SUCCESS = 0.05
TRUST_FAILURE = -0.10
TRUST_INITIAL = 0.5


class TrustScore:
    """Per-session trust scoring engine."""

    def __init__(self):
        self._score = TRUST_INITIAL
        self._approvals = 0
        self._rejections = 0
        self._total_actions = 0

    @property
    def score(self) -> float:
        return round(max(0.0, min(1.0, self._score)), 3)

    def check_gate(self, action_type: str) -> dict:
        """Check if trust level allows auto-execution of an action.

        Returns:
            {
                "allowed": bool,
                "trust_score": float,
                "threshold": float,
                "reason": str,
            }
        """
        threshold = TRUST_GATES.get(action_type, 0.5)
        allowed = self._score >= threshold

        if allowed:
            reason = f"Trust {self._score:.0%} >= threshold {threshold:.0%} — auto-approved"
        else:
            reason = f"Trust {self._score:.0%} < threshold {threshold:.0%} — requires approval"

        return {
            "allowed": allowed,
            "trust_score": self.score,
            "threshold": threshold,
            "reason": reason,
        }

    def record_success(self, action_type: str = "general"):
        """Record a successful action — trust increases."""
        self._score += TRUST_SUCCESS
        self._approvals += 1
        self._total_actions += 1
        logger.info("Trust: +%.2f → %.3f (success: %s)", TRUST_SUCCESS, self._score, action_type)

    def record_failure(self, action_type: str = "general"):
        """Record a failed/rejected action — trust decreases."""
        self._score += TRUST_FAILURE  # TRUST_FAILURE is negative
        self._rejections += 1
        self._total_actions += 1
        logger.info("Trust: %.2f → %.3f (failure: %s)", TRUST_FAILURE, self._score, action_type)

    def record_approval(self):
        """User approved an action — trust increases."""
        self._score += TRUST_SUCCESS
        self._approvals += 1
        self._total_actions += 1

    def record_rejection(self):
        """User rejected an action — trust decreases."""
        self._score += TRUST_FAILURE
        self._rejections += 1
        self._total_actions += 1

    def stats(self) -> dict:
        return {
            "score": self.score,
            "approvals": self._approvals,
            "rejections": self._rejections,
            "total_actions": self._total_actions,
            "approval_rate": round(self._approvals / max(1, self._total_actions), 3),
        }

    def reset(self):
        """Reset trust to initial state."""
        self._score = TRUST_INITIAL
        self._approvals = 0
        self._rejections = 0
        self._total_actions = 0


# Global trust score instance
_trust: TrustScore | None = None


def get_trust() -> TrustScore:
    """Get the global trust score (singleton)."""
    global _trust
    if _trust is None:
        _trust = TrustScore()
    return _trust


def reset_trust():
    """Reset the global trust score (for tests)."""
    global _trust
    _trust = TrustScore()
