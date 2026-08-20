"""Root Cause Analysis protocol for HeatMind.

When a tool call, LLM call, or synthesis step fails, this module traces
backward through the execution context to identify the root cause, assess
blast radius, and recommend fixes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class RCAReport:
    """Root Cause Analysis report for a failure."""

    failure_type: str
    blast_radius: str
    root_cause: str
    evidence: list[str] = field(default_factory=list)
    recommendation: str = ""
    severity: str = "P3"


# ── Failure taxonomy ──────────────────────────────────────────────────

FAILURE_MODES = {
    "api_timeout": {
        "description": "FortyGuard API did not respond within timeout",
        "default_severity": "P2",
    },
    "api_error": {
        "description": "FortyGuard API returned an error response",
        "default_severity": "P2",
    },
    "llm_parse_error": {
        "description": "LLM returned unparsable JSON",
        "default_severity": "P3",
    },
    "llm_unavailable": {
        "description": "LLM provider unreachable or rate-limited",
        "default_severity": "P1",
    },
    "tool_error": {
        "description": "Tool execution raised an exception",
        "default_severity": "P3",
    },
    "data_missing": {
        "description": "Required data field missing from observations",
        "default_severity": "P3",
    },
    "synthesis_failure": {
        "description": "LLM synthesis phase returned no usable answer",
        "default_severity": "P2",
    },
    "hallucination": {
        "description": "Verification detected unsupported claims in answer",
        "default_severity": "P2",
    },
    "delegation_failure": {
        "description": "Sub-agent delegation failed",
        "default_severity": "P3",
    },
    "unknown": {
        "description": "Unclassified failure",
        "default_severity": "P4",
    },
}


def classify_failure(error: Exception | str | None, context: dict | None = None) -> str:
    """Classify an error into a failure type from the taxonomy.

    Args:
        error: The exception or error string.
        context: Optional execution context (phase, tool name, etc.).

    Returns:
        One of the FAILURE_MODES keys.
    """
    if error is None:
        return "unknown"

    text = str(error).lower() if isinstance(error, str) else f"{type(error).__name__}: {error}".lower()
    ctx = context or {}

    # Timeout patterns
    if "timeout" in text or "timed out" in text:
        return "api_timeout"

    # Tool-specific patterns (check before api_error to avoid false matches)
    phase = ctx.get("phase", "")
    tool = ctx.get("tool", "")
    if "tool" in phase.lower() or "endpoint" in phase.lower():
        if tool in ("env_params", "heatmap", "heat_intelligence", "satellite", "streetview"):
            return "tool_error"

    # API error patterns
    if "api" in text and ("error" in text or "status" in text or "429" in text or "500" in text):
        return "api_error"
    if "rate limit" in text or "429" in text:
        return "api_error"

    # LLM patterns
    if "json" in text and ("parse" in text or "decode" in text or "expect" in text):
        return "llm_parse_error"
    if "json" in text and ("extract" in text or "malformed" in text or "invalid" in text):
        return "llm_parse_error"
    if "llm" in text and ("unavailable" in text or "connect" in text or "auth" in text):
        return "llm_unavailable"
    if "openai" in text or "anthropic" in text or "gemini" in text:
        if "error" in text or "connect" in text or "timeout" in text:
            return "llm_unavailable"

    # Data patterns
    if "missing" in text or "not found" in text or "none" in text:
        if ctx.get("phase") == "synthesize":
            return "data_missing"
        return "data_missing"

    # Synthesis patterns
    if "synth" in text or "answer" in text or "summary" in text:
        return "synthesis_failure"

    # Delegation patterns
    if "delegat" in text or "sub-agent" in text:
        return "delegation_failure"

    return "unknown"


def _trace_failure_origin(tool_results: list[dict], context: dict) -> str:
    """Walk backward through tool results to find the origin of failure."""
    # Check tool results in reverse order for first error
    for entry in reversed(tool_results):
        status = entry.get("status", "")
        if status == "error":
            tool = entry.get("endpoint", "unknown")
            summary = entry.get("result_summary", "")
            return f"Tool '{tool}' failed: {summary}"

    # Check context for phase information
    phase = context.get("phase", "unknown")
    return f"Failure originated in {phase} phase"


def _assess_blast_radius(failure_type: str, context: dict) -> str:
    """Assess what downstream components are affected."""
    phase = context.get("phase", "")
    tool_results = context.get("tool_results", [])

    if failure_type == "api_timeout":
        return "Tool results incomplete; synthesis may lack data from failed endpoint"

    if failure_type == "api_error":
        return "Tool results may be partial or empty; synthesis quality degraded"

    if failure_type == "llm_parse_error":
        if phase == "plan":
            return "Planning failed; agent falls back to ChainAgent deterministic path"
        elif phase == "synthesize":
            return "Answer generation failed; no user-facing response produced"
        return "LLM output could not be parsed; downstream phases skipped"

    if failure_type == "llm_unavailable":
        return "LLM provider unreachable; entire agent pipeline falls back to ChainAgent"

    if failure_type == "tool_error":
        # Count how many subsequent tools might be affected
        failed_idx = len(tool_results)
        remaining = max(0, 5 - failed_idx)
        if remaining > 0:
            return f"Remaining {remaining} tool call(s) may be affected by missing data"
        return "Tool failed but other calls may have succeeded"

    if failure_type == "data_missing":
        return "Synthesis lacks required data; answer may be incomplete or generic"

    if failure_type == "synthesis_failure":
        return "No user-facing answer produced; system returns fallback response"

    if failure_type == "hallucination":
        return "Answer contains unsupported claims; user may receive inaccurate information"

    if failure_type == "delegation_failure":
        return "Sub-agent did not produce output; parent agent continues without sub-agent insights"

    return "Unknown blast radius"


def _generate_recommendation(failure_type: str, root_cause: str, context: dict) -> str:
    """Generate actionable recommendation based on failure analysis."""
    recommendations = {
        "api_timeout": "Increase timeout threshold or implement retry with exponential backoff. "
        "Consider cached fallback data for repeated timeout patterns.",
        "api_error": "Check API key validity and rate limits. Implement circuit breaker "
        "to prevent cascade failures. Log full error response for debugging.",
        "llm_parse_error": "Add JSON extraction retries with temperature reduction. "
        "Consider using structured output mode if provider supports it.",
        "llm_unavailable": "Verify LLM provider configuration and API key. "
        "Ensure graceful fallback to ChainAgent is working.",
        "tool_error": "Add tool-specific error handling. Consider retry with "
        "different parameters. Validate inputs before API call.",
        "data_missing": "Ensure all required fields are extracted from API responses. "
        "Add validation in tool wrapper before passing to synthesis.",
        "synthesis_failure": "Simplify synthesis prompt. Reduce observation payload size. "
        "Consider splitting synthesis into smaller focused calls.",
        "hallucination": "Run verification loop post-synthesis. Add grounding instructions "
        "to synthesis prompt requiring citation of observation data.",
        "delegation_failure": "Verify sub-agent prompt quality. Ensure delegation payload "
        "includes sufficient context for the sub-agent.",
        "unknown": "Collect more diagnostic information. Add structured logging at each phase boundary.",
    }
    return recommendations.get(failure_type, "Investigate and add specific error handling.")


def analyze_failure(
    error: Exception | str | None,
    context: dict,
    tool_results: list[dict] | None = None,
) -> RCAReport:
    """Analyze a failure and produce an RCAReport.

    Args:
        error: The exception or error string that triggered the analysis.
        context: Execution context with keys like phase, tool, zone, query, etc.
        tool_results: List of trace entries from tool execution phases.

    Returns:
        RCAReport with failure_type, blast_radius, root_cause, evidence, recommendation, severity.
    """
    tool_results = tool_results or []
    failure_type = classify_failure(error, context)

    # Trace origin
    root_cause = _trace_failure_origin(tool_results, context)
    if error is not None:
        error_msg = str(error) if isinstance(error, str) else f"{type(error).__name__}: {error}"
        root_cause = f"{root_cause} — {error_msg[:200]}"

    # Build evidence list
    evidence = []
    if error is not None:
        error_msg = str(error) if isinstance(error, str) else f"{type(error).__name__}: {error}"
        evidence.append(f"Error: {error_msg[:300]}")

    phase = context.get("phase", "unknown")
    evidence.append(f"Phase: {phase}")

    tool = context.get("tool", "")
    if tool:
        evidence.append(f"Tool: {tool}")

    # Add relevant tool results as evidence
    for entry in tool_results[-3:]:  # Last 3 steps
        status = entry.get("status", "")
        ep = entry.get("endpoint", "")
        summary = entry.get("result_summary", "")
        if status == "error":
            evidence.append(f"Failed step: {ep} — {summary[:200]}")

    zone = context.get("zone", "")
    if zone:
        evidence.append(f"Zone: {zone}")

    query = context.get("query", "")
    if query:
        evidence.append(f"Query: {query[:100]}")

    # Blast radius
    blast_radius = _assess_blast_radius(failure_type, context)

    # Recommendation
    recommendation = _generate_recommendation(failure_type, root_cause, context)

    # Severity
    severity = FAILURE_MODES.get(failure_type, {}).get("default_severity", "P4")

    return RCAReport(
        failure_type=failure_type,
        blast_radius=blast_radius,
        root_cause=root_cause,
        evidence=evidence,
        recommendation=recommendation,
        severity=severity,
    )


def rca_to_dict(report: RCAReport) -> dict:
    """Convert an RCAReport to a plain dict for trace integration."""
    return {
        "failure_type": report.failure_type,
        "blast_radius": report.blast_radius,
        "root_cause": report.root_cause,
        "evidence": report.evidence,
        "recommendation": report.recommendation,
        "severity": report.severity,
    }
