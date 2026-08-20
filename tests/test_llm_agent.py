"""Tests for LLMAgent — the agentic LLM reasoning core."""

from unittest.mock import MagicMock, patch

import pytest

from agents.llm_agent import LLMAgent
from utils.demo import demo_env_params


@pytest.fixture
def mock_memory():
    return MagicMock()


def test_handle_full_loop_mock_llm(mock_memory):
    with patch("agents.llm_agent.FortyGuardClient") as mock_api:
        mock_api.side_effect = ValueError("no key")
        agent = LLMAgent(memory=mock_memory, llm=None)
        result = agent.handle(
            "What's the heat situation in Dubai?",
            "sess-1",
            {"latitude": 25.2, "longitude": 55.3, "date": "2026-08-19"},
        )
        assert result["agent"] == "llm"
        assert result["llm_mode"] == "mock"
        assert result["severity"] in ("low", "moderate", "high", "extreme")
        assert isinstance(result["reasoning"], list) and len(result["reasoning"]) >= 3
        assert result["map_data"]["latitude"] == 25.2
        assert result["map_data"]["longitude"] == 55.3
        assert result["response_time_ms"] >= 0


def test_handle_fallback_when_llm_plan_fails(mock_memory):
    with patch("agents.llm_agent.FortyGuardClient") as mock_api:
        mock_api.side_effect = ValueError("no key")
        with patch("agents.llm_agent.ChainAgent") as mock_chain_cls:
            mock_chain = MagicMock()
            mock_chain.execute_chain.return_value = {"response": "fallback response", "agent": "chain", "raw_data": {}}
            mock_chain_cls.return_value = mock_chain

            bad_llm = MagicMock()
            bad_llm.name = "broken"
            bad_llm.complete.side_effect = Exception("provider down")

            agent = LLMAgent(memory=mock_memory, llm=bad_llm)
            result = agent.handle(
                "heat in Dubai",
                "sess-2",
                {"latitude": 25.2, "longitude": 55.3, "date": "2026-08-19"},
            )
            assert result["agent"] == "chain"
            assert result["llm_mode"] == "fallback"
            assert result["fallback_reason"] == "llm_plan_unavailable"
            assert result["response"] == "fallback response"


def test_handle_uses_demo_data_when_no_api(mock_memory):
    with patch("agents.llm_agent.FortyGuardClient") as mock_api:
        mock_api.side_effect = ValueError("no key")
        with patch("agents.llm_agent.ChainAgent") as mock_chain_cls:
            mock_chain = MagicMock()
            mock_chain.execute_chain.return_value = {"response": "x", "agent": "chain"}
            mock_chain_cls.return_value = mock_chain

            agent = LLMAgent(memory=mock_memory, llm=None)
            result = agent.handle(
                "check heat",
                "sess-3",
                {"latitude": 25.2, "longitude": 55.3, "date": "2026-08-19"},
            )
            assert result["agent"] == "llm"
            env = result["raw_data"].get("env_params") or {}
            assert env.get("demo") is True


def test_plan_includes_whitelisted_tools_only():
    with patch("agents.llm_agent.FortyGuardClient") as mock_api:
        mock_api.side_effect = ValueError("no key")
        agent = LLMAgent(memory=MagicMock(), llm=None)
        plan = agent._plan("heat", "quick", "Dubai", 25.2, 55.3, "2026-08-19")
        assert isinstance(plan, dict)
        for call in plan.get("tool_calls", []):
            assert call["tool"] in ("env_params", "heatmap", "heat_intelligence", "satellite", "streetview")


def test_run_tool_unknown_tool():
    with patch("agents.llm_agent.FortyGuardClient") as mock_api:
        mock_api.side_effect = ValueError("no key")
        agent = LLMAgent(memory=MagicMock(), llm=None)
        data, err = agent._run_tool("not_a_tool", {}, 25.2, 55.3, "2026-08-19", "14:00")
        assert data == {}
        assert err == "unknown tool"


def test_format_response_includes_measured_conditions():
    answer = {"severity": "high", "summary": "Dangerous heat.", "recommendations": ["Cool down"]}
    observations = {"env_params": demo_env_params(25.2, 55.3)}
    agent = LLMAgent(memory=MagicMock(), llm=None)
    text = agent._format_response(answer, observations, MagicMock())
    assert "HIGH" in text
    assert "Measured Conditions" in text
    assert "Cool down" in text


def test_demo_disclaimer_when_demo_data():
    answer = {"severity": "moderate", "summary": "Watch closely.", "recommendations": []}
    observations = {"env_params": demo_env_params(25.2, 55.3)}
    agent = LLMAgent(memory=MagicMock(), llm=None)
    text = agent._format_response(answer, observations, MagicMock())
    assert "Demo data" in text
