"""Cost-aware autonomy ledger for HeatMind.

Every autonomous decision — LLM reasoning call or FortyGuard tool call — is
recorded with an estimated USD cost. The agent uses this to prefer cheaper
sufficient tool paths (env_params over heat_intelligence) and the app surfaces
the ledger so judges can see cost-aware behavior, per the Track 06 brief.
"""

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


class CostLedger:
    """Append-only ledger of LLM + tool costs for one agent run."""

    def __init__(self):
        self._entries: list[dict] = []

    def record_llm(self, provider, phase: str, input_chars: int, output_chars: int, latency_ms: float = 0.0) -> None:
        self._entries.append(
            {
                "kind": "llm",
                "phase": phase,
                "model": getattr(provider, "model", provider.name),
                "cost_usd": round(estimate_cost(provider, input_chars, output_chars), 6),
                "latency_ms": round(latency_ms, 1),
            }
        )

    def record_tool(self, tool: str) -> None:
        self._entries.append(
            {
                "kind": "tool",
                "tool": tool,
                "cost_usd": TOOL_COST_USD.get(tool, 0.0),
            }
        )

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
