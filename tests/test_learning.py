"""Tests for memory/learning.py - Continuous Learning."""

from memory.learning import extract_pattern, patterns_to_prompt


def test_extract_pattern():
    pattern = extract_pattern(
        {
            "trace_id": "test_1",
            "zone": "Dubai",
            "query": "heat in Dubai",
            "query_type": "quick",
            "severity": "high",
            "tool_calls": ["env_params"],
            "outcome": "success",
            "confidence": 0.8,
        }
    )
    assert pattern is not None
    assert pattern.get("zone") == "Dubai"
    assert pattern.get("outcome") == "success"
    assert pattern.get("confidence") == 0.8


def test_extract_pattern_missing_zone():
    pattern = extract_pattern(
        {
            "zone": "",
            "tool_calls": ["env_params"],
            "outcome": "success",
        }
    )
    assert pattern is None


def test_extract_pattern_missing_tools():
    pattern = extract_pattern(
        {
            "zone": "Dubai",
            "tool_calls": [],
            "outcome": "success",
        }
    )
    assert pattern is None


def test_extract_pattern_failed_outcome():
    pattern = extract_pattern(
        {
            "zone": "Dubai",
            "tool_calls": ["env_params"],
            "outcome": "failure",
        }
    )
    assert pattern is None


def test_patterns_to_prompt():
    patterns = [
        {"zone": "Dubai", "query_type": "quick", "severity": "high", "tools_used": ["env_params"], "occurrences": 3},
    ]
    prompt = patterns_to_prompt(patterns)
    assert "quick" in prompt
    assert "env_params" in prompt
    assert isinstance(prompt, str)


def test_patterns_to_prompt_empty():
    prompt = patterns_to_prompt([])
    assert prompt == ""
