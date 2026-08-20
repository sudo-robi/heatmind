"""Token budget enforcement for HeatMind agent phases.

Each agent phase (plan/reflect/synthesize/debate) gets a hard token budget.
If exceeded, the module compresses text, truncates, or signals escalation.
"""

import logging
from dataclasses import dataclass

from config import DAILY_BUDGET_USD
from utils.cost_ledger import CostLedger

logger = logging.getLogger(__name__)

PHASE_DEFAULTS: dict[str, tuple[int, int]] = {
    "plan": (2000, 500),
    "reflect": (1500, 300),
    "synthesize": (3000, 800),
    "debate": (1000, 200),
}


@dataclass
class TokenBudget:
    """Token budget for a single agent phase."""

    phase: str
    max_input_tokens: int = 2000
    max_output_tokens: int = 500
    used_input_tokens: int = 0
    used_output_tokens: int = 0

    @property
    def remaining_input(self) -> int:
        return max(0, self.max_input_tokens - self.used_input_tokens)

    @property
    def remaining_output(self) -> int:
        return max(0, self.max_output_tokens - self.used_output_tokens)

    @property
    def input_pct_used(self) -> float:
        if self.max_input_tokens <= 0:
            return 1.0
        return min(1.0, self.used_input_tokens / self.max_input_tokens)

    @property
    def output_pct_used(self) -> float:
        if self.max_output_tokens <= 0:
            return 1.0
        return min(1.0, self.used_output_tokens / self.max_output_tokens)

    def is_over(self) -> bool:
        return self.used_input_tokens >= self.max_input_tokens or self.used_output_tokens >= self.max_output_tokens


class BudgetManager:
    """Manages per-phase token budgets and daily cost budget."""

    def __init__(self, ledger: CostLedger | None = None):
        self._budgets: dict[str, TokenBudget] = {}
        self._ledger = ledger or CostLedger()
        self._daily_input_tokens = 0
        self._daily_output_tokens = 0

    def _get_or_create(self, phase: str) -> TokenBudget:
        if phase not in self._budgets:
            defaults = PHASE_DEFAULTS.get(phase, (2000, 500))
            self._budgets[phase] = TokenBudget(
                phase=phase,
                max_input_tokens=defaults[0],
                max_output_tokens=defaults[1],
            )
        return self._budgets[phase]

    def check_budget(self, phase: str) -> dict[str, int]:
        """Return remaining budget for the given phase."""
        budget = self._get_or_create(phase)
        return {
            "remaining_input": budget.remaining_input,
            "remaining_output": budget.remaining_output,
            "max_input": budget.max_input_tokens,
            "max_output": budget.max_output_tokens,
        }

    def record_usage(self, phase: str, input_tokens: int, output_tokens: int) -> None:
        """Deduct tokens from the phase budget and track daily totals."""
        budget = self._get_or_create(phase)
        budget.used_input_tokens += input_tokens
        budget.used_output_tokens += output_tokens
        self._daily_input_tokens += input_tokens
        self._daily_output_tokens += output_tokens
        if budget.is_over():
            logger.warning(
                "Phase '%s' exceeded token budget: input=%d/%d output=%d/%d",
                phase,
                budget.used_input_tokens,
                budget.max_input_tokens,
                budget.used_output_tokens,
                budget.max_output_tokens,
            )

    def compress_if_needed(self, text: str, phase: str, char_to_token: float = 4.0) -> str:
        """Compress text if it would exceed the remaining output budget.

        Returns truncated text if over budget, otherwise returns as-is.
        """
        budget = self._get_or_create(phase)
        tokens_needed = len(text) / char_to_token
        if tokens_needed <= budget.remaining_output:
            return text
        max_chars = int(budget.remaining_output * char_to_token)
        if max_chars < 50:
            return text[:50] + "... [truncated]"
        return text[:max_chars] + "... [compressed]"

    def get_daily_summary(self) -> dict:
        """Return total tokens used today and estimated cost."""
        total_tokens = self._daily_input_tokens + self._daily_output_tokens
        cost_usd = self._ledger.total_usd()
        return {
            "input_tokens": self._daily_input_tokens,
            "output_tokens": self._daily_output_tokens,
            "total_tokens": total_tokens,
            "estimated_cost_usd": cost_usd,
            "daily_budget_usd": DAILY_BUDGET_USD,
        }

    def is_over_budget(self) -> bool:
        """True if daily cost budget has been exceeded."""
        return self._ledger.total_usd() >= DAILY_BUDGET_USD

    def get_phase(self, phase: str) -> TokenBudget:
        """Return the TokenBudget object for a phase."""
        return self._get_or_create(phase)

    def reset_phase(self, phase: str) -> None:
        """Reset a phase budget (e.g., for a new run)."""
        self._budgets.pop(phase, None)
