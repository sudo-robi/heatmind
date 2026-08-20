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


class TestReflectiveLoop:
    def test_reflect_concludes_when_evidence_sufficient(self):
        with patch("agents.llm_agent.FortyGuardClient") as mock_api:
            mock_api.side_effect = ValueError("no key")
            agent = LLMAgent(memory=MagicMock(), llm=None)
            reflect = agent._reflect(
                "how hot is it?", MagicMock(location="Dubai"), {"env_params": demo_env_params(25.2, 55.3)}
            )
            assert isinstance(reflect, dict)
            assert reflect["continue"] is False
            assert reflect["next_tool_calls"] == []

    def test_reflect_requests_more_when_missing(self):
        with patch("agents.llm_agent.FortyGuardClient") as mock_api:
            mock_api.side_effect = ValueError("no key")
            agent = LLMAgent(memory=MagicMock(), llm=None)
            reflect = agent._reflect(
                "comprehensive risk assessment",
                MagicMock(location="Dubai"),
                {"env_params": demo_env_params(25.2, 55.3)},
            )
            assert reflect["continue"] is True
            assert len(reflect["next_tool_calls"]) >= 1
            for call in reflect["next_tool_calls"]:
                assert call["tool"] in ("env_params", "heatmap", "heat_intelligence", "satellite", "streetview")

    def test_handle_has_reflection_step_in_trace(self, mock_memory):
        with patch("agents.llm_agent.FortyGuardClient") as mock_api:
            mock_api.side_effect = ValueError("no key")
            agent = LLMAgent(memory=mock_memory, llm=None)
            result = agent.handle(
                "comprehensive heat risk assessment for Dubai",
                "sess-r",
                {"latitude": 25.2, "longitude": 55.3, "date": "2026-08-19"},
            )
            actions = [s["action"] for s in result["reasoning"]]
            assert any("Reflect" in a for a in actions)

    def test_handle_reports_cost_ledger(self, mock_memory):
        with patch("agents.llm_agent.FortyGuardClient") as mock_api:
            mock_api.side_effect = ValueError("no key")
            agent = LLMAgent(memory=mock_memory, llm=None)
            result = agent.handle(
                "heat in Dubai",
                "sess-c",
                {"latitude": 25.2, "longitude": 55.3, "date": "2026-08-19"},
            )
            cost = result["cost"]
            assert cost["llm_calls"] >= 2  # plan + synthesize (+reflect)
            assert cost["tool_calls"] >= 1
            assert isinstance(cost["usd"], (int, float))


class TestSubAgentHandoff:
    def test_delegate_runs_spec_agent(self, mock_memory):
        with patch("agents.llm_agent.FortyGuardClient") as mock_api:
            mock_api.side_effect = ValueError("no key")
            agent = LLMAgent(memory=mock_memory, llm=None)
            handoff = agent._delegate("heat-analyst", "ANALYZE", "Observations here")
            assert handoff["success"] is True
            assert "analysis" in handoff["result"]
            assert any(d["agent"] == "heat-analyst" for d in agent._delegations)

    def test_emergency_delegates_to_coordinator_and_alert(self, mock_memory):
        with patch("agents.llm_agent.FortyGuardClient") as mock_api:
            mock_api.side_effect = ValueError("no key")
            agent = LLMAgent(memory=mock_memory, llm=None)
            result = agent.handle(
                "extreme heat emergency in Dubai",
                "sess-e",
                {"latitude": 25.2, "longitude": 55.3, "date": "2026-08-19"},
            )
            agents_used = [d["agent"] for d in result["delegations"]]
            assert "emergency-coordinator" in agents_used
            assert "public-alert" in agents_used
            assert result["severity"] in ("high", "extreme")

    def test_moderate_delegates_to_analyst_only(self, mock_memory):
        with patch("agents.llm_agent.FortyGuardClient") as mock_api:
            mock_api.side_effect = ValueError("no key")
            moderate_env = dict(demo_env_params(25.2, 55.3))
            moderate_env["heat_index_celsius"] = 34.0
            with patch("agents.llm_agent.demo_env_params", return_value=moderate_env):
                agent = LLMAgent(memory=mock_memory, llm=None)
                result = agent.handle(
                    "heat advisory for Dubai",
                    "sess-m",
                    {"latitude": 25.2, "longitude": 55.3, "date": "2026-08-19"},
                )
            agents_used = [d["agent"] for d in result["delegations"]]
            assert "heat-analyst" in agents_used
            assert "emergency-coordinator" not in agents_used

    def test_demo_mode_forces_demo_data_even_with_key(self, mock_memory):
        with patch("agents.llm_agent.FortyGuardClient") as mock_api:
            mock_api.return_value = MagicMock()
            agent = LLMAgent(memory=mock_memory, llm=None, demo_mode=True)
            assert agent._api is None
