"""Tests for ChainAgent — multi-endpoint chaining with reasoning steps."""

from unittest.mock import MagicMock, patch

import pytest

from agents.chain_agent import ChainAgent, ReasoningStep


@pytest.fixture
def mock_memory():
    return MagicMock()


@pytest.fixture
def mock_api():
    with patch("agents.chain_agent.FortyGuardClient") as mock:
        client = mock.return_value
        client.create_env_params.return_value = "env-123"
        client.create_heatmap.return_value = "heat-456"
        client.create_heat_intelligence.return_value = "intel-789"
        client.wait_for_result.side_effect = lambda aid: {
            "env-123": {
                "heat_index_celsius": [42.5],
                "apparent_temperature_celsius": [45.0],
                "relative_humidity_percent": [65],
            },
            "heat-456": {"stats_data": {"Temperature_stats": {"Minimum": 35.0, "Maximum": 48.0, "Mean": 41.0}}},
            "intel-789": {"analysis": {"risk_level": "high"}},
        }.get(aid, {})
        client.get_call_log.return_value = [{"method": "POST", "url": "/v1/env_params"}]
        yield client


class TestReasoningStep:
    def test_to_dict_pending(self):
        step = ReasoningStep(1, "test", "/v1/test", "because")
        d = step.to_dict()
        assert d["step"] == 1
        assert d["status"] == "pending"

    def test_to_dict_success(self):
        step = ReasoningStep(1, "test", "/v1/test", "because")
        step.result = {"key": "value"}
        d = step.to_dict()
        assert d["status"] == "success"

    def test_to_dict_error(self):
        step = ReasoningStep(1, "test", "/v1/test", "because")
        step.error = "something broke"
        d = step.to_dict()
        assert d["status"] == "error"

    def test_summarize_result_dict(self):
        step = ReasoningStep(1, "test", "/v1/test", "because")
        step.result = {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5, "f": 6}
        s = step._summarize_result()
        assert "Keys:" in s

    def test_summarize_result_error(self):
        step = ReasoningStep(1, "test", "/v1/test", "because")
        step.error = "oops"
        assert "Error: oops" in step._summarize_result()

    def test_summarize_result_none(self):
        step = ReasoningStep(1, "test", "/v1/test", "because")
        assert step._summarize_result() == "Pending"


class TestChainAgent:
    def test_execute_chain_env_params_only(self, mock_api, mock_memory):
        agent = ChainAgent(memory=mock_memory)
        result = agent.execute_chain(
            query="check heat in Phoenix",
            session_id="test-session",
            endpoints=["env_params"],
            params={
                "latitude": 33.45,
                "longitude": -112.07,
                "date": "2026-08-15",
                "temperature": 35.0,
            },
        )
        assert result["agent"] == "chain"
        assert "env_params" in result["raw_data"]
        assert len(result["reasoning"]) == 1
        mock_api.create_env_params.assert_called_once()

    def test_execute_chain_full(self, mock_api, mock_memory):
        agent = ChainAgent(memory=mock_memory)
        polygon = {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [54.37, 24.45],
                                [54.47, 24.45],
                                [54.47, 24.55],
                                [54.37, 24.55],
                                [54.37, 24.45],
                            ]
                        ],
                    },
                }
            ],
        }
        result = agent.execute_chain(
            query="full analysis",
            session_id="test-session",
            endpoints=["env_params", "heatmap", "heat_intelligence"],
            params={
                "latitude": 24.5,
                "longitude": 54.4,
                "date": "2026-08-15",
                "temperature": 35.0,
                "polygon_aoi": polygon,
            },
        )
        assert len(result["reasoning"]) == 3
        assert "env_params" in result["raw_data"]
        assert "heatmap" in result["raw_data"]
        assert "heat_intelligence" in result["raw_data"]

    def test_execute_chain_env_params_failure(self, mock_api, mock_memory):
        mock_api.create_env_params.return_value = None
        agent = ChainAgent(memory=mock_memory)
        result = agent.execute_chain(
            query="check heat",
            session_id="test-session",
            endpoints=["env_params"],
            params={
                "latitude": 33.45,
                "longitude": -112.07,
                "date": "2026-08-15",
            },
        )
        assert result["reasoning"][0]["status"] == "error"

    def test_execute_chain_api_exception(self, mock_api, mock_memory):
        mock_api.create_env_params.side_effect = Exception("API down")
        agent = ChainAgent(memory=mock_memory)
        result = agent.execute_chain(
            query="check heat",
            session_id="test-session",
            endpoints=["env_params"],
            params={
                "latitude": 33.45,
                "longitude": -112.07,
                "date": "2026-08-15",
            },
        )
        assert result["reasoning"][0]["status"] == "error"
        assert "API down" in result["reasoning"][0]["result_summary"]

    def test_execute_chain_message_logged(self, mock_api, mock_memory):
        agent = ChainAgent(memory=mock_memory)
        agent.execute_chain(
            query="test query",
            session_id="s1",
            endpoints=["env_params"],
            params={
                "latitude": 33.45,
                "longitude": -112.07,
                "date": "2026-08-15",
            },
        )
        mock_memory.add_message.assert_any_call("s1", "user", "test query")
        mock_memory.add_message.assert_any_call("s1", "assistant", mock_memory.add_message.call_args_list[-1][0][2])

    def test_execute_chain_decision_logged(self, mock_api, mock_memory):
        agent = ChainAgent(memory=mock_memory)
        agent.execute_chain(
            query="test",
            session_id="s1",
            endpoints=["env_params", "heatmap"],
            params={
                "latitude": 33.45,
                "longitude": -112.07,
                "date": "2026-08-15",
            },
        )
        mock_memory.log_decision.assert_called_once()
        call_kwargs = mock_memory.log_decision.call_args[1]
        assert "chain:env_params,heatmap" in call_kwargs["decision"]

    def test_build_reasoning_text(self, mock_api, mock_memory):
        agent = ChainAgent(memory=mock_memory)
        step = ReasoningStep(1, "test", "/v1/test", "reason")
        step.result = {"ok": True}
        text = agent._build_reasoning_text([step])
        assert "/v1/test" in text
        assert "success" in text
        assert "reason" in text

    def test_format_chained_response_env_params(self, mock_api, mock_memory):
        agent = ChainAgent(memory=mock_memory)
        step = ReasoningStep(1, "fetch", "/v1/env_params", "need data")
        step.result = {"heat_index_celsius": [42.5]}
        results = {"env_params": {"heat_index_celsius": [42.5]}}
        resp = agent._format_chained_response(results, [step], "test")
        assert "Environmental Conditions" in resp
        assert "Heat Index Celsius" in resp

    def test_format_chained_response_heatmap(self, mock_api, mock_memory):
        agent = ChainAgent(memory=mock_memory)
        step = ReasoningStep(1, "map", "/v1/heatmap", "visualize")
        step.result = True
        results = {"heatmap": {"stats_data": {"Temperature_stats": {"Minimum": 35.0, "Maximum": 48.0, "Mean": 41.0}}}}
        resp = agent._format_chained_response(results, [step], "test")
        assert "Heatmap Statistics" in resp
