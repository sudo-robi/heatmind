"""Tests for the LLM provider abstraction (utils/llm.py)."""

import json
from unittest.mock import MagicMock, patch

import pytest

from utils.llm import (
    LLMError,
    MockLLM,
    extract_json,
    get_llm,
    provider_name,
    reset_llm,
    safe_complete,
    timed_complete,
)


class TestMockLLM:
    def test_plan_mode(self):
        llm = MockLLM()
        text = llm.complete("[PHASE: PLAN] plan", "query")
        data = json.loads(text)
        assert "tool_calls" in data
        assert isinstance(data["tool_calls"], list)
        assert data["tool_calls"][0]["tool"] in (
            "env_params",
            "heatmap",
            "heat_intelligence",
            "satellite",
            "streetview",
        )

    def test_answer_mode(self):
        llm = MockLLM()
        text = llm.complete("[PHASE: ANSWER] answer", "query")
        data = json.loads(text)
        assert "summary" in data
        assert "severity" in data
        assert data["severity"] in ("low", "moderate", "high", "extreme")
        assert isinstance(data["recommendations"], list)

    def test_answer_detects_emergency(self):
        llm = MockLLM()
        text = llm.complete("[PHASE: ANSWER] answer", "EMERGENCY in Phoenix")
        data = json.loads(text)
        assert data["severity"] == "high"
        assert "send_alert" in data["actions"]

    def test_plan_emergency_adds_alert_action(self):
        llm = MockLLM()
        text = llm.complete("[PHASE: PLAN] plan", "EMERGENCY: workers collapsing")
        data = json.loads(text)
        assert "send_alert" in data["actions"]

    def test_name(self):
        assert MockLLM().name == "mock"


class TestExtractJson:
    def test_plain_json(self):
        assert extract_json('{"a": 1}') == {"a": 1}

    def test_code_fence(self):
        assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}

    def test_embedded_json(self):
        text = 'Here is the result:\n```json\n{"summary": "hot"}\n```\nHope that helps.'
        assert extract_json(text) == {"summary": "hot"}

    def test_invalid_returns_empty(self):
        result = extract_json("not json at all")
        assert result == {}


class TestProviderSelection:
    def test_defaults_to_mock(self):
        reset_llm()
        with patch("config.LLM_PROVIDER", ""), patch("config.OPENAI_API_KEY", ""):
            assert get_llm().name == "mock"

    def test_provider_name(self):
        assert provider_name() in ("openai", "anthropic", "gemini", "ollama", "mock")


class TestSafeComplete:
    def test_success(self):
        llm = MockLLM()
        text, latency = timed_complete(llm, "plan", "query")
        assert isinstance(text, str)
        assert latency >= 0

    def test_error_propagates(self):
        llm = MagicMock()
        llm.complete.side_effect = LLMError("boom")
        with pytest.raises(LLMError):
            safe_complete(llm, "plan", "query")

    def test_mock_is_cached_singleton(self):
        reset_llm()
        with patch("config.LLM_PROVIDER", ""), patch("config.OPENAI_API_KEY", ""):
            a = get_llm()
            b = get_llm()
            assert a is b
