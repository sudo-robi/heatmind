"""Shadow testing for model routing.

Routes 5% of queries to experimental models, compares quality,
and autonomously promotes better models.
"""

import hashlib
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

logger = logging.getLogger(__name__)

_SHADOW_RATE = 0.05
_PROMOTION_THRESHOLD = 0.6
_MIN_COMPARISONS = 20


def _quality_score(result: dict, heat_index: float | None = None) -> float:
    """Score a result on quality heuristics (0.0 - 1.0)."""
    score = 0.0
    if result.get("summary"):
        score += 0.2
    severity = result.get("severity")
    if severity in ("low", "moderate", "high", "extreme"):
        score += 0.2
    if result.get("recommendations"):
        recs = result["recommendations"]
        if isinstance(recs, list) and len(recs) > 0:
            score += 0.2
        elif isinstance(recs, dict) and any(v for v in recs.values()):
            score += 0.2
    if severity and heat_index is not None:
        expected = (
            "extreme" if heat_index >= 45 else "high" if heat_index >= 38 else "moderate" if heat_index >= 33 else "low"
        )
        if severity == expected:
            score += 0.2
    if result.get("reasoning") or result.get("trace"):
        score += 0.2
    return score


@dataclass
class ShadowResult:
    """Result of a shadow comparison between primary and shadow models."""

    query: str
    primary_model: str
    shadow_model: str
    primary_result: dict
    shadow_result: dict
    primary_score: float = 0.0
    shadow_score: float = 0.0
    winner: str = "tie"
    timestamp: str = ""

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now(UTC).isoformat()


class ShadowTester:
    """Manages shadow testing: routing, scoring, comparison, promotion."""

    def __init__(self):
        self._comparisons: list[ShadowResult] = []

    def should_shadow(self, query: str = "") -> bool:
        """Returns True ~5% of the time, deterministic based on timestamp + query."""
        now = datetime.now(UTC)
        seed = f"{now.hour}:{now.minute}:{now.day}:{query[:20]}"
        h = int(hashlib.md5(seed.encode()).hexdigest(), 16)
        return (h % 100) < (_SHADOW_RATE * 100)

    def compare_results(
        self,
        primary: dict,
        shadow: dict,
        query: str = "",
        primary_model: str = "primary",
        shadow_model: str = "shadow",
        heat_index: float | None = None,
    ) -> ShadowResult:
        """Score both results and determine a winner."""
        p_score = _quality_score(primary, heat_index)
        s_score = _quality_score(shadow, heat_index)

        if p_score > s_score:
            winner = "primary"
        elif s_score > p_score:
            winner = "shadow"
        else:
            winner = "tie"

        result = ShadowResult(
            query=query,
            primary_model=primary_model,
            shadow_model=shadow_model,
            primary_result=primary,
            shadow_result=shadow,
            primary_score=p_score,
            shadow_score=s_score,
            winner=winner,
        )
        self.record_comparison(result)
        return result

    def record_comparison(self, result: ShadowResult) -> None:
        """Store a comparison result."""
        self._comparisons.append(result)

    def get_promotion_recommendation(self) -> dict:
        """If shadow consistently wins, recommend promotion."""
        if len(self._comparisons) < _MIN_COMPARISONS:
            return {"promote": False, "reason": f"Need {_MIN_COMPARISONS} comparisons, have {len(self._comparisons)}"}

        shadow_wins = sum(1 for c in self._comparisons if c.winner == "shadow")
        win_rate = shadow_wins / len(self._comparisons)

        if win_rate >= _PROMOTION_THRESHOLD:
            models = [c.shadow_model for c in self._comparisons if c.winner == "shadow"]
            best_model = max(set(models), key=models.count) if models else "unknown"
            return {
                "promote": True,
                "shadow_model": best_model,
                "win_rate": round(win_rate, 3),
                "total_comparisons": len(self._comparisons),
            }

        return {
            "promote": False,
            "win_rate": round(win_rate, 3),
            "total_comparisons": len(self._comparisons),
        }

    def get_stats(self) -> dict:
        """Total comparisons, win rates per model."""
        if not self._comparisons:
            return {"total": 0, "win_rates": {}}

        model_wins: dict[str, int] = {}
        model_appearances: dict[str, int] = {}
        for c in self._comparisons:
            for model in (c.primary_model, c.shadow_model):
                model_appearances[model] = model_appearances.get(model, 0) + 1
            if c.winner == "primary":
                model_wins[c.primary_model] = model_wins.get(c.primary_model, 0) + 1
            elif c.winner == "shadow":
                model_wins[c.shadow_model] = model_wins.get(c.shadow_model, 0) + 1

        win_rates = {}
        for model, wins in model_wins.items():
            appearances = model_appearances.get(model, 1)
            win_rates[model] = round(wins / appearances, 3)

        return {
            "total": len(self._comparisons),
            "win_rates": win_rates,
        }
