"""Cost-aware autonomy ledger for HeatMind.

Every autonomous decision — LLM reasoning call or FortyGuard tool call — is
recorded with an estimated USD cost. The agent uses this to prefer cheaper
sufficient tool paths (env_params over heat_intelligence) and the app surfaces
the ledger so judges can see cost-aware behavior, per the Track 06 brief.
"""

from config import DAILY_BUDGET_USD
from utils.llm import estimate_cost

# Approximate USD cost of one FortyGuard tool execution.
TOOL_COST_USD = {
    "env_params": 0.01,
    "heatmap": 0.02,
    "heat_intelligence": 0.03,
    "satellite": 0.02,
    "streetview": 0.01,
    "alerts": 0.0,
}

# Daily budget — shared across all CostLedger instances via module-level tracker
_daily_spent: float = 0.0


class CostLedger:
    """Append-only ledger of LLM + tool costs for one agent run."""

    def __init__(self):
        self._entries: list[dict] = []

    def record_llm(self, provider, phase: str, input_chars: int, output_chars: int, latency_ms: float = 0.0) -> None:
        cost = round(estimate_cost(provider, input_chars, output_chars), 6)
        self._entries.append(
            {
                "kind": "llm",
                "phase": phase,
                "model": getattr(provider, "model", provider.name),
                "cost_usd": cost,
                "latency_ms": round(latency_ms, 1),
            }
        )
        global _daily_spent
        _daily_spent += cost

    def record_tool(self, tool: str) -> None:
        cost = TOOL_COST_USD.get(tool, 0.0)
        self._entries.append(
            {
                "kind": "tool",
                "tool": tool,
                "cost_usd": cost,
            }
        )
        global _daily_spent
        _daily_spent += cost

    def total_usd(self) -> float:
        return round(sum(e["cost_usd"] for e in self._entries), 6)

    def llm_calls(self) -> int:
        return sum(1 for e in self._entries if e["kind"] == "llm")

    def tool_calls(self) -> int:
        return sum(1 for e in self._entries if e["kind"] == "tool")

    def summary(self) -> dict:
        return {
            "usd": self.total_usd(),
            "llm_calls": self.llm_calls(),
            "tool_calls": self.tool_calls(),
            "ledger": list(self._entries),
        }

    def __len__(self) -> int:
        return len(self._entries)

    # ── Budget-aware methods ────────────────────────────────────────────

    def remaining_budget(self) -> float:
        """Remaining daily budget in USD."""
        return round(max(0.0, DAILY_BUDGET_USD - _daily_spent), 6)

    def budget_pct_used(self) -> float:
        """Percentage of daily budget consumed (0.0–1.0)."""
        if DAILY_BUDGET_USD <= 0:
            return 1.0
        return min(1.0, _daily_spent / DAILY_BUDGET_USD)

    def check_budget(self, estimated_cost: float = 0.01) -> str:
        """Check if we can afford an operation. Returns tier: 'full', 'reduced', 'minimal'."""
        remaining = self.remaining_budget()
        if remaining <= 0:
            return "minimal"
        if remaining >= DAILY_BUDGET_USD * 0.5:
            return "full"
        if remaining >= DAILY_BUDGET_USD * 0.2:
            return "reduced"
        return "minimal"

    @staticmethod
    def daily_spent() -> float:
        """Total spent today across all runs."""
        return round(_daily_spent, 6)

    @staticmethod
    def reset_daily():
        """Reset daily tracker (for tests or midnight rollover)."""
        global _daily_spent
        _daily_spent = 0.0
