"""Pre-execution safety hooks for tool calls.

Blocks dangerous operations (SQL injection, command injection, path traversal,
secret leakage) before they execute and inspects results after.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

# ---------------------------------------------------------------------------
# Pattern definitions
# ---------------------------------------------------------------------------

BLOCK_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"DROP\s+TABLE", re.IGNORECASE),
    re.compile(r"DELETE\s+FROM", re.IGNORECASE),
    re.compile(r"TRUNCATE", re.IGNORECASE),
    re.compile(r";\s*rm\s+-rf", re.IGNORECASE),
    re.compile(r"&&\s*rm\b", re.IGNORECASE),
    re.compile(r"\|\s*rm\b", re.IGNORECASE),
    re.compile(r"\.\./", re.IGNORECASE),
    re.compile(r"\.\.\\", re.IGNORECASE),
    # Plain-text secret patterns
    re.compile(r"(?:api[_-]?key|password|secret)\s*[=:]\s*['\"][^'\"]{8,}['\"]", re.IGNORECASE),
]

WARN_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"chmod\s+[0-7]*7[0-7]*\s", re.IGNORECASE),
    re.compile(r"wget\b.*\|.*sh\b", re.IGNORECASE),
    re.compile(r"curl\b.*\|.*sh\b", re.IGNORECASE),
]

# Secrets in output
SECRET_OUTPUT_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"(?:api[_-]?key|password|secret|token)\s*[=:]\s*\S{10,}", re.IGNORECASE),
]


def check_input_safety(input_text: str) -> dict[str, Any]:
    """Check *input_text* against blocked and warning patterns.

    Returns ``{"safe": bool, "violations": [...], "warnings": [...]}``.
    """
    violations: list[str] = []
    warnings: list[str] = []

    for pat in BLOCK_PATTERNS:
        if pat.search(input_text):
            violations.append(pat.pattern)

    for pat in WARN_PATTERNS:
        if pat.search(input_text):
            warnings.append(pat.pattern)

    return {
        "safe": len(violations) == 0,
        "violations": violations,
        "warnings": warnings,
    }


def check_tool_safety(tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
    """Validate tool arguments against safety rules.

    Serialises all values to strings before pattern matching.
    """
    combined_text = " ".join(str(v) for v in args.values())
    result = check_input_safety(combined_text)
    result["tool_name"] = tool_name
    return result


# ---------------------------------------------------------------------------
# Hook class
# ---------------------------------------------------------------------------


@dataclass
class SafetyHook:
    """Session-scoped safety hook that records all violations."""

    violations: list[dict[str, Any]] = field(default_factory=list, init=False)

    def pre_tool_call(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        """Run safety checks before tool execution."""
        result = check_tool_safety(tool_name, args)
        if not result["safe"]:
            self.violations.append(
                {
                    "phase": "pre",
                    "tool": tool_name,
                    "violations": result["violations"],
                }
            )
        return result

    def post_tool_call(self, tool_name: str, result: Any) -> dict[str, Any]:
        """Run post-checks — e.g. no secrets leaked in response."""
        text = str(result)
        output_violations: list[str] = []
        for pat in SECRET_OUTPUT_PATTERNS:
            if pat.search(text):
                output_violations.append(pat.pattern)

        safe = len(output_violations) == 0
        if not safe:
            self.violations.append(
                {
                    "phase": "post",
                    "tool": tool_name,
                    "violations": output_violations,
                }
            )
        return {"safe": safe, "violations": output_violations}

    def get_violations(self) -> list[dict[str, Any]]:
        """Return all violations recorded during this session."""
        return list(self.violations)
