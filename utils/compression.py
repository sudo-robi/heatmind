"""Context compression for HeatMind agent phases.

Compresses observations between phases to save tokens and cost.
"""

from utils.llm import estimate_tokens


def _summarize_value(key: str, value: object) -> str | None:
    """Summarize a single observation value into 1-2 lines."""
    if value is None:
        return None
    if isinstance(value, dict):
        parts = []
        for k, v in value.items():
            if v is None:
                continue
            if isinstance(v, (int, float)):
                parts.append(f"{k}={v}")
            elif isinstance(v, str):
                parts.append(f"{k}={v[:60]}")
            elif isinstance(v, dict):
                inner = ", ".join(f"{ik}={iv}" for ik, iv in v.items() if iv is not None)
                if inner:
                    parts.append(f"{k}: {inner}")
        return f"{key}: {', '.join(parts)}" if parts else None
    if isinstance(value, list):
        if not value:
            return None
        return f"{key}: [{len(value)} items]"
    if isinstance(value, str) and not value.strip():
        return None
    return f"{key}: {value}"


_PRIORITY_ORDER = ["env_params", "heatmap", "satellite", "streetview", "heat_intelligence"]


def compress_observations(observations: dict, max_tokens: int = 1000) -> str:
    """Summarize each tool result into 1-2 lines, prioritized by importance.

    Priority: env_params > heatmap > satellite > streetview > heat_intelligence.
    Keys with None/empty values are dropped.
    """
    ordered_keys = [k for k in _PRIORITY_ORDER if k in observations]
    for k in observations:
        if k not in ordered_keys:
            ordered_keys.append(k)

    lines: list[str] = []
    for key in ordered_keys:
        summary = _summarize_value(key, observations[key])
        if summary:
            lines.append(summary)

    result = "\n".join(lines)
    if estimate_tokens(result) <= max_tokens:
        return result

    truncated: list[str] = []
    running_tokens = 0
    for line in lines:
        line_tokens = estimate_tokens(line)
        if running_tokens + line_tokens > max_tokens - 20:
            truncated.append("... [truncated]")
            break
        truncated.append(line)
        running_tokens += line_tokens
    return "\n".join(truncated)


def compress_for_synthesis(observations: dict, plan: dict | None = None, max_tokens: int = 800) -> str:
    """Focused compression for the synthesis phase.

    Includes: key metrics from env_params, heatmap stats summary,
    heat_intelligence summary. Target: max 800 tokens.
    """
    parts: list[str] = []

    env = observations.get("env_params")
    if env and isinstance(env, dict):
        hi = env.get("heat_index_celsius") or env.get("heat_index")
        hum = env.get("relative_humidity_percent") or env.get("relative_humidity")
        aqi = env.get("air_quality:idx") or env.get("aqi")
        app = env.get("apparent_temperature_celsius")
        metrics = []
        if hi is not None:
            metrics.append(f"heat_index_celsius: {hi}")
        if hum is not None:
            metrics.append(f"relative_humidity_percent: {hum}")
        if aqi is not None:
            metrics.append(f"air_quality:idx: {aqi}")
        if app is not None:
            metrics.append(f"apparent_temperature_celsius: {app}")
        if metrics:
            parts.append("ENV: " + ", ".join(metrics))

    heatmap = observations.get("heatmap")
    if heatmap and isinstance(heatmap, dict):
        stats = heatmap.get("stats_data", {})
        temp_stats = stats.get("Temperature_stats", {})
        if temp_stats:
            parts.append(
                f"HEATMAP: min={temp_stats.get('Minimum', '?')}, "
                f"max={temp_stats.get('Maximum', '?')}, "
                f"mean={temp_stats.get('Mean', '?')}"
            )

    intel = observations.get("heat_intelligence")
    if intel and isinstance(intel, dict):
        risk = intel.get("risk_level", intel.get("risk"))
        summary = intel.get("summary", "")
        if risk:
            parts.append(f"INTEL risk={risk}")
        if summary:
            parts.append(f"INTEL: {summary[:200]}")

    if plan:
        tools = plan.get("tool_calls", [])
        if tools:
            tool_names = [t.get("tool", t) if isinstance(t, dict) else str(t) for t in tools]
            parts.append(f"PLAN tools: {', '.join(tool_names)}")

    result = "\n".join(parts)
    if estimate_tokens(result) <= max_tokens:
        return result
    return result[: int(max_tokens * 4)] + "... [compressed]"
