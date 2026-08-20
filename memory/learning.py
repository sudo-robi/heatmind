"""Continuous learning engine for HeatMind.

Extracts reusable patterns from past decisions and injects them into the
planning phase so the agent improves with every query. Patterned after
everything-claude-code's continuous-learning skill.
"""

import logging
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


def extract_pattern(trace: dict) -> dict | None:
    """Extract a reusable pattern from a completed trace.

    Returns a pattern document suitable for storage, or None if the trace
    doesn't contain enough signal.
    """
    zone = trace.get("zone", "")
    severity = trace.get("severity", "")
    outcome = trace.get("outcome", "")
    tools_used = trace.get("tool_calls", [])
    confidence = trace.get("confidence", 0.0)
    feedback = trace.get("user_feedback")

    if not zone or not tools_used:
        return None

    # Only extract patterns from successful runs
    if outcome not in ("success", "completed"):
        return None

    # Classify the query type from the trace
    query_type = _classify_query(trace.get("query", ""))

    pattern = {
        "zone": zone,
        "query_type": query_type,
        "tools_used": tools_used,
        "severity": severity,
        "outcome": outcome,
        "confidence": confidence,
        "user_feedback": feedback,
        "trace_id": trace.get("trace_id", ""),
        "timestamp": datetime.now(UTC).isoformat(),
        "pattern_key": f"{zone.lower()}:{query_type}",
    }
    return pattern


def _classify_query(query: str) -> str:
    """Classify a query into a type for pattern matching."""
    q = query.lower()
    if any(w in q for w in ("heat index", "heat index", "current temperature", "what's the temp")):
        return "heat_index"
    if any(w in q for w in ("risk", "danger", "emergency", "safe", "unsafe")):
        return "risk_assessment"
    if any(w in q for w in ("map", "heatmap", "thermal", "distribution")):
        return "thermal_map"
    if any(w in q for w in ("satellite", "aerial", "overview")):
        return "satellite_view"
    if any(w in q for w in ("street", "ground", "visual")):
        return "street_view"
    if any(w in q for w in ("report", "analysis", "assess", "evaluate")):
        return "full_analysis"
    if any(w in q for w in ("alert", "warning", "notify")):
        return "alert"
    return "general"


def patterns_to_prompt(patterns: list[dict]) -> str:
    """Format patterns into a prompt snippet for the planning phase."""
    if not patterns:
        return ""

    lines = ["Past successful strategies for this zone/type:"]
    seen = set()
    for p in patterns[:5]:
        key = f"{p.get('tools_used', [])}:{p.get('severity', '')}"
        if key in seen:
            continue
        seen.add(key)
        tools = " + ".join(p.get("tools_used", []))
        sev = p.get("severity", "unknown")
        fb = p.get("user_feedback")
        fb_note = " (user approved)" if fb == "positive" else ""
        lines.append(f"- {p.get('query_type', '?')} at {sev} severity: {tools}{fb_note}")

    return "\n".join(lines)


def aggregate_patterns(patterns: list[dict]) -> list[dict]:
    """Aggregate patterns by pattern_key, keeping the most recent and best-performing."""
    by_key: dict[str, list[dict]] = {}
    for p in patterns:
        key = p.get("pattern_key", "unknown")
        by_key.setdefault(key, []).append(p)

    aggregated = []
    for _key, group in by_key.items():
        # Sort by: positive feedback first, then by confidence, then by recency
        group.sort(
            key=lambda x: (
                1 if x.get("user_feedback") == "positive" else 0,
                x.get("confidence", 0),
                x.get("timestamp", ""),
            ),
            reverse=True,
        )
        best = group[0].copy()
        best["occurrences"] = len(group)
        best["success_rate"] = sum(1 for g in group if g.get("outcome") in ("success", "completed")) / len(group)
        aggregated.append(best)

    # Sort by occurrences (most used strategies first)
    aggregated.sort(key=lambda x: x.get("occurrences", 0), reverse=True)
    return aggregated[:10]


def get_learning_stats(patterns: list[dict]) -> dict:
    """Compute learning statistics from patterns."""
    if not patterns:
        return {"total_patterns": 0, "zones_covered": 0, "top_tools": [], "avg_confidence": 0}

    zones = {p.get("zone", "") for p in patterns}
    tool_counts: dict[str, int] = {}
    for p in patterns:
        for t in p.get("tools_used", []):
            tool_counts[t] = tool_counts.get(t, 0) + 1
    top_tools = sorted(tool_counts.items(), key=lambda x: x[1], reverse=True)[:5]

    confidences = [p.get("confidence", 0) for p in patterns if p.get("confidence")]
    avg_conf = sum(confidences) / len(confidences) if confidences else 0

    positive = sum(1 for p in patterns if p.get("user_feedback") == "positive")
    negative = sum(1 for p in patterns if p.get("user_feedback") == "negative")

    return {
        "total_patterns": len(patterns),
        "zones_covered": len(zones),
        "top_tools": top_tools,
        "avg_confidence": round(avg_conf, 3),
        "positive_feedback": positive,
        "negative_feedback": negative,
    }
