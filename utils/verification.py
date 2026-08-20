"""Post-synthesis verification loop for HeatMind.

Cross-references every factual claim in the LLM's answer against actual
FortyGuard API observations to detect hallucinations before they reach
the user. This is the core grounding pattern for agentic AI reliability.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class VerificationResult:
    """A single verified claim from the synthesized answer."""

    claim: str
    source_data: str
    supported: bool
    confidence: float
    issue: str = ""


# ── Threshold rules ─────────────────────────────────────────────────────

SEVERITY_THRESHOLDS: list[tuple[float, set[str]]] = [
    (45.0, {"extreme"}),
    (38.0, {"high", "extreme"}),
    (33.0, {"moderate", "high", "extreme"}),
]

SEVERITY_ORDER = {"low": 0, "moderate": 1, "high": 2, "extreme": 3}

EXTREME_RECOMMENDATIONS = {
    "evacuate",
    "evacuate immediately",
    "seek emergency shelter",
    "emergency evacuation",
    "mandatory evacuation",
    "do not go outside",
}

HIGH_RECOMMENDATIONS = {
    "stay indoors",
    "limit outdoor exposure",
    "avoid outdoor activities",
    "stay in air conditioning",
    "avoid prolonged sun exposure",
    "use extreme caution",
}


def _extract_heat_index(observations: dict) -> float | None:
    """Pull the heat index from observations, checking common key patterns."""
    env = observations.get("env_params") or {}
    for key in ("heat_index_celsius", "heat_index"):
        val = env.get(key)
        if isinstance(val, (int, float)):
            return float(val)
    return None


def _extract_severity(answer: dict) -> str | None:
    """Extract severity from the answer dict."""
    sev = answer.get("severity")
    if isinstance(sev, str) and sev in SEVERITY_ORDER:
        return sev
    return None


def _extract_heat_index_from_answer(answer: dict) -> float | None:
    """Extract heat index values mentioned in the answer text or fields."""
    # Check explicit fields first
    for key in ("heat_index", "heat_index_celsius", "heat_index_value"):
        val = answer.get(key)
        if isinstance(val, (int, float)):
            return float(val)

    # Search in summary/recommendations text for numeric patterns
    text_parts = []
    summary = answer.get("summary", "")
    if isinstance(summary, str):
        text_parts.append(summary)
    for rec in answer.get("recommendations", []):
        if isinstance(rec, str):
            text_parts.append(rec)

    combined = " ".join(text_parts)
    # Match patterns like "heat index of 47" or "47°C" or "47 degrees"
    matches = re.findall(r"(?:heat\s*index|temperature)\s*(?:of|is|was|:)?\s*(\d+(?:\.\d+)?)", combined, re.IGNORECASE)
    if matches:
        return float(matches[0])
    c_matches = re.findall(r"(\d+(?:\.\d+)?)\s*°?\s*C", combined)
    if c_matches:
        return float(c_matches[0])
    return None


def _extract_recommended_actions(answer: dict) -> list[str]:
    """Extract recommendation strings from the answer."""
    recs = answer.get("recommendations") or []
    if isinstance(recs, list):
        return [str(r).lower().strip() for r in recs if isinstance(r, str)]
    return []


def _normalize(text: str) -> str:
    """Normalize text for comparison."""
    return re.sub(r"[^a-z0-9\s]", "", text.lower()).strip()


def _rec_matches_any(rec: str, target_set: set[str]) -> bool:
    """Check if a recommendation matches any entry in a target set."""
    norm_rec = _normalize(rec)
    return any(_normalize(target) in norm_rec or norm_rec in _normalize(target) for target in target_set)


# ── Core verification ──────────────────────────────────────────────────


def verify_answer(answer: dict, observations: dict) -> dict:
    """Verify every factual claim in the synthesized answer against observations.

    Args:
        answer: The LLM-synthesized answer dict (severity, recommendations, summary, etc.).
        observations: Raw data returned by the tool calls (env_params, heatmap, etc.).

    Returns:
        dict with keys: verified (bool), results (list[VerificationResult]), hallucination_risk (str).
    """
    results: list[VerificationResult] = []
    obs_heat_index = _extract_heat_index(observations)
    answer_severity = _extract_severity(answer)
    answer_heat_index = _extract_heat_index_from_answer(answer)
    recommendations = _extract_recommended_actions(answer)

    # ── Check 1: severity vs heat_index threshold ──────────────────────
    if obs_heat_index is not None and answer_severity is not None:
        issue = ""
        supported = True
        confidence = 1.0
        for threshold, allowed_severities in SEVERITY_THRESHOLDS:
            if obs_heat_index >= threshold and answer_severity not in allowed_severities:
                supported = False
                confidence = 0.0
                issue = (
                    f"heat_index={obs_heat_index} >= {threshold} but severity={answer_severity} "
                    f"not in {allowed_severities}"
                )
                break
        # Also check upper bound: severity too low for the threshold
        if supported and obs_heat_index is not None:
            for threshold, allowed_severities in reversed(SEVERITY_THRESHOLDS):
                if obs_heat_index < threshold and answer_severity in allowed_severities:
                    # Only flag if severity is strictly above what threshold allows
                    min_allowed = min(SEVERITY_ORDER[s] for s in allowed_severities)
                    if SEVERITY_ORDER[answer_severity] > min_allowed:
                        supported = False
                        confidence = 0.3
                        issue = (
                            f"heat_index={obs_heat_index} < {threshold} but severity={answer_severity} may be too high"
                        )
                        break

        results.append(
            VerificationResult(
                claim=f"severity={answer_severity} for heat_index={obs_heat_index}",
                source_data=f"env_params.heat_index_celsius={obs_heat_index}",
                supported=supported,
                confidence=confidence,
                issue=issue,
            )
        )

    # ── Check 2: recommendations match severity ────────────────────────
    if answer_severity is not None:
        for rec in recommendations:
            supported = True
            confidence = 1.0
            issue = ""

            if answer_severity == "extreme":
                # Extreme can have any recommendation
                pass
            elif answer_severity == "high":
                if _rec_matches_any(rec, EXTREME_RECOMMENDATIONS):
                    supported = False
                    confidence = 0.0
                    issue = f"'{rec}' is an extreme-severity recommendation but severity is high"
            elif answer_severity == "moderate":
                if _rec_matches_any(rec, EXTREME_RECOMMENDATIONS | HIGH_RECOMMENDATIONS):
                    supported = False
                    confidence = 0.0
                    issue = f"'{rec}' is a high/extreme recommendation but severity is moderate"
            elif answer_severity == "low":
                if _rec_matches_any(rec, EXTREME_RECOMMENDATIONS | HIGH_RECOMMENDATIONS):
                    supported = False
                    confidence = 0.0
                    issue = f"'{rec}' is a high/extreme recommendation but severity is low"

            results.append(
                VerificationResult(
                    claim=f"recommendation: '{rec}' for severity={answer_severity}",
                    source_data=f"answer.severity={answer_severity}",
                    supported=supported,
                    confidence=confidence,
                    issue=issue,
                )
            )

    # ── Check 3: heat_index values in answer must come from observations ─
    if answer_heat_index is not None:
        if obs_heat_index is not None:
            supported = abs(answer_heat_index - obs_heat_index) < 2.0
            confidence = 1.0 if supported else 0.0
            issue = (
                ""
                if supported
                else (f"answer mentions heat_index={answer_heat_index} but observations show {obs_heat_index}")
            )
        else:
            supported = False
            confidence = 0.0
            issue = f"answer mentions heat_index={answer_heat_index} but no heat_index in observations"

        results.append(
            VerificationResult(
                claim=f"heat_index value {answer_heat_index}",
                source_data=f"env_params.heat_index_celsius={obs_heat_index}",
                supported=supported,
                confidence=confidence,
                issue=issue,
            )
        )

    # ── Check 4: severity exists in answer ─────────────────────────────
    if answer_severity is None and obs_heat_index is not None:
        results.append(
            VerificationResult(
                claim="answer provides severity classification",
                source_data=f"env_params.heat_index_celsius={obs_heat_index}",
                supported=False,
                confidence=0.0,
                issue="No severity field in answer despite having heat_index data",
            )
        )

    # ── Aggregate ──────────────────────────────────────────────────────
    unsupported = [r for r in results if not r.supported]
    if not results:
        verified = True
        risk = "low"
    elif not unsupported:
        verified = True
        risk = "low"
    elif len(unsupported) == 1 and unsupported[0].confidence > 0.3:
        verified = True
        risk = "medium"
    else:
        verified = False
        risk = "high"

    return {
        "verified": verified,
        "results": [r.__dict__ for r in results],
        "hallucination_risk": risk,
    }
