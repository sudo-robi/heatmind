"""Lightweight eval harness for HeatMind agent quality.

Defines 15 test cases spanning emergency, moderate, low-severity, edge-case,
and missing-data scenarios. Runs each through the agent function, scores
results, and produces an aggregate report.

Usage::

    from utils.eval_harness import run_eval, print_report
    results = run_eval(my_agent_fn)
    print_report(results)
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class EvalCase:
    """A single eval case definition."""

    id: str
    query: str
    expected_severity: str
    expected_tools: list[str] = field(default_factory=list)
    expected_actions: list[str] = field(default_factory=list)
    min_recommendations: int = 0
    params: dict = field(default_factory=dict)
    category: str = "general"


EVAL_CASES: list[EvalCase] = [
    # ── Emergency / extreme severity ──────────────────────────────────
    EvalCase(
        id="emergency_01",
        query="There's a heat emergency in Dubai, heat index 47°C",
        expected_severity="extreme",
        expected_tools=["env_params"],
        expected_actions=["send_alert"],
        min_recommendations=3,
        params={"latitude": 25.2048, "longitude": 55.2708},
        category="emergency",
    ),
    EvalCase(
        id="emergency_02",
        query="Phoenix is experiencing dangerous heat, 49°C heat index, people collapsing",
        expected_severity="extreme",
        expected_tools=["env_params"],
        expected_actions=["send_alert"],
        min_recommendations=3,
        params={"latitude": 33.4484, "longitude": -112.0740},
        category="emergency",
    ),
    EvalCase(
        id="emergency_03",
        query="URGENT: Outdoor workers at risk, heat index 46°C in Riyadh",
        expected_severity="extreme",
        expected_tools=["env_params"],
        expected_actions=["send_alert"],
        min_recommendations=3,
        params={"latitude": 24.7136, "longitude": 46.6753},
        category="emergency",
    ),
    # ── High severity ────────────────────────────────────────────────
    EvalCase(
        id="high_01",
        query="What's the heat risk in Abu Dhabi today? It feels very hot.",
        expected_severity="high",
        expected_tools=["env_params"],
        min_recommendations=2,
        params={"latitude": 24.4539, "longitude": 54.3773},
        category="high",
    ),
    EvalCase(
        id="high_02",
        query="Should I cancel my outdoor event in Doha? Temperature is around 42°C.",
        expected_severity="high",
        expected_tools=["env_params", "heatmap"],
        min_recommendations=2,
        params={"latitude": 25.2854, "longitude": 51.5310},
        category="high",
    ),
    # ── Moderate severity ────────────────────────────────────────────
    EvalCase(
        id="moderate_01",
        query="Is it safe to jog in Cairo this afternoon?",
        expected_severity="moderate",
        expected_tools=["env_params"],
        min_recommendations=1,
        params={"latitude": 30.0444, "longitude": 31.2357},
        category="moderate",
    ),
    EvalCase(
        id="moderate_02",
        query="How's the heat in Athens for sightseeing tomorrow?",
        expected_severity="moderate",
        expected_tools=["env_params"],
        min_recommendations=1,
        params={"latitude": 37.9838, "longitude": 23.7275},
        category="moderate",
    ),
    # ── Low severity ─────────────────────────────────────────────────
    EvalCase(
        id="low_01",
        query="Is London comfortable for walking today?",
        expected_severity="low",
        expected_tools=["env_params"],
        min_recommendations=0,
        params={"latitude": 51.5074, "longitude": -0.1278},
        category="low",
    ),
    EvalCase(
        id="low_02",
        query="Can I have a picnic in Berlin this weekend?",
        expected_severity="low",
        expected_tools=["env_params"],
        min_recommendations=0,
        params={"latitude": 52.5200, "longitude": 13.4050},
        category="low",
    ),
    # ── Comprehensive / multi-tool ───────────────────────────────────
    EvalCase(
        id="comprehensive_01",
        query="Give me a full heat assessment of Singapore including satellite data and street view.",
        expected_severity="moderate",
        expected_tools=["env_params", "satellite", "streetview"],
        min_recommendations=2,
        params={"latitude": 1.3521, "longitude": 103.8198},
        category="comprehensive",
    ),
    EvalCase(
        id="comprehensive_02",
        query="Analyze urban heat island effect in Tokyo with heatmap and satellite imagery.",
        expected_severity="moderate",
        expected_tools=["heatmap", "satellite", "env_params"],
        min_recommendations=2,
        params={"latitude": 35.6762, "longitude": 139.6503},
        category="comprehensive",
    ),
    # ── Missing data / edge cases ────────────────────────────────────
    EvalCase(
        id="edge_01",
        query="What's the heat index? I don't know where I am.",
        expected_severity="low",
        expected_tools=["env_params"],
        min_recommendations=0,
        category="edge",
    ),
    EvalCase(
        id="edge_02",
        query="Tell me about heat in the middle of the ocean at coordinates 0,0.",
        expected_severity="low",
        expected_tools=["env_params"],
        min_recommendations=0,
        params={"latitude": 0.0, "longitude": 0.0},
        category="edge",
    ),
    EvalCase(
        id="edge_03",
        query="Heat assessment at the North Pole.",
        expected_severity="low",
        expected_tools=["env_params"],
        min_recommendations=0,
        params={"latitude": 90.0, "longitude": 0.0},
        category="edge",
    ),
    EvalCase(
        id="time_of_day_01",
        query="What's the heat like in Jeddah at midnight?",
        expected_severity="moderate",
        expected_tools=["env_params"],
        min_recommendations=1,
        params={"latitude": 21.4858, "longitude": 39.1925, "time": "00:00"},
        category="edge",
    ),
]


def score_result(result: dict, expected: EvalCase) -> dict:
    """Score a single agent result against expected values.

    Returns dict with per-field pass/fail and overall pass.
    """
    scores = {}

    # Severity match
    actual_sev = result.get("severity", "unknown")
    scores["severity"] = actual_sev == expected.expected_severity

    # Tools used (check if expected tools appear in trace)
    trace_endpoints = set()
    for step in result.get("reasoning", []):
        ep = step.get("endpoint", "")
        if ep.startswith("POST /v1/"):
            trace_endpoints.add(ep.replace("POST /v1/", ""))
    if expected.expected_tools:
        scores["tools"] = all(t in trace_endpoints for t in expected.expected_tools)
    else:
        scores["tools"] = True

    # Actions (e.g., send_alert)
    actions = set(result.get("actions", []))
    # Also check trace for alert triggers
    for step in result.get("reasoning", []):
        if step.get("action") == "Trigger alert":
            actions.add("send_alert")
    if expected.expected_actions:
        scores["actions"] = all(a in actions for a in expected.expected_actions)
    else:
        scores["actions"] = True

    # Minimum recommendations
    recs = result.get("recommendations", [])
    scores["recommendations"] = len(recs) >= expected.min_recommendations

    # Non-empty response
    scores["has_response"] = bool(result.get("response"))

    # Overall pass
    scores["pass"] = all(scores.values())

    return scores


def aggregate_results(results: list[dict]) -> dict:
    """Aggregate eval results into summary metrics."""
    if not results:
        return {
            "total": 0,
            "pass_rate": 0.0,
            "pass@1": 0.0,
            "by_category": {},
            "by_field": {},
        }

    total = len(results)
    passed = sum(1 for r in results if r["scores"]["pass"])

    # Per-category pass rates
    by_category: dict[str, dict] = {}
    for r in results:
        cat = r["case"].category
        if cat not in by_category:
            by_category[cat] = {"total": 0, "passed": 0}
        by_category[cat]["total"] += 1
        if r["scores"]["pass"]:
            by_category[cat]["passed"] += 1
    for cat in by_category:
        t = by_category[cat]["total"]
        p = by_category[cat]["passed"]
        by_category[cat]["rate"] = round(p / t, 3) if t else 0.0

    # Per-field pass rates
    fields = ["severity", "tools", "actions", "recommendations", "has_response"]
    by_field: dict[str, dict] = {}
    for f in fields:
        field_passed = sum(1 for r in results if r["scores"].get(f, False))
        by_field[f] = {"total": total, "passed": field_passed, "rate": round(field_passed / total, 3)}

    return {
        "total": total,
        "passed": passed,
        "pass_rate": round(passed / total, 3),
        "pass@1": round(passed / total, 3),
        "by_category": by_category,
        "by_field": by_field,
    }


def run_eval(agent_fn, cases: list[EvalCase] | None = None, timeout: float = 30.0) -> list[dict]:
    """Run all eval cases through the agent function.

    Args:
        agent_fn: Callable with signature (query: str, params: dict) -> dict.
        cases: Optional override for EVAL_CASES.
        timeout: Per-case timeout in seconds (informational, not enforced).

    Returns:
        List of dicts, each with 'case', 'result', 'scores', 'latency_ms'.
    """
    if cases is None:
        cases = EVAL_CASES

    results = []
    for case in cases:
        start = time.time()
        try:
            result = agent_fn(case.query, case.params)
        except Exception as e:
            result = {
                "severity": "unknown",
                "recommendations": [],
                "response": "",
                "reasoning": [],
                "actions": [],
                "error": str(e),
            }
        latency_ms = (time.time() - start) * 1000
        scores = score_result(result, case)
        results.append(
            {
                "case": case,
                "result": result,
                "scores": scores,
                "latency_ms": round(latency_ms, 1),
            }
        )
    return results


def print_report(results: list[dict]) -> str:
    """Pretty-print the eval report. Returns the report string."""
    agg = aggregate_results(results)
    lines = [
        "=" * 60,
        "  HeatMind Eval Report",
        "=" * 60,
        f"  Total: {agg['total']}  |  Passed: {agg.get('passed', 0)}  |  Rate: {agg['pass_rate']:.1%}",
        "-" * 60,
    ]

    # Per-case results
    for r in results:
        case = r["case"]
        scores = r["scores"]
        status = "PASS" if scores["pass"] else "FAIL"
        lat = r["latency_ms"]
        lines.append(f"  [{status}] {case.id} ({lat:.0f}ms)")
        if not scores["pass"]:
            failed_fields = [k for k, v in scores.items() if k != "pass" and not v]
            actual_sev = r["result"].get("severity", "?")
            lines.append(f"         severity: {actual_sev} (expected: {case.expected_severity})")
            if failed_fields:
                lines.append(f"         failed: {', '.join(failed_fields)}")

    # Per-category breakdown
    lines.append("-" * 60)
    lines.append("  By Category:")
    for cat, data in agg["by_category"].items():
        lines.append(f"    {cat:15s}  {data['passed']}/{data['total']}  ({data['rate']:.0%})")

    # Per-field breakdown
    lines.append("-" * 60)
    lines.append("  By Field:")
    for field_name, data in agg["by_field"].items():
        lines.append(f"    {field_name:15s}  {data['passed']}/{data['total']}  ({data['rate']:.0%})")

    lines.append("=" * 60)
    report = "\n".join(lines)
    print(report)
    return report
