import uuid
from unittest.mock import MagicMock, patch

import pytest

from agents.deep_agent import DeepAgent
from agents.emergency_agent import EmergencyAgent
from agents.quick_agent import QuickAgent


def make_session_id():
    return str(uuid.uuid4())


@pytest.fixture
def mock_api():
    with patch("agents.quick_agent.FortyGuardClient") as mock:
        client = MagicMock()
        mock.return_value = client
        client.create_env_params.return_value = "test-activity-123"
        client.wait_for_result.return_value = {
            "heat_index_celsius": 42.5,
            "relative_humidity_percent": 65,
            "air_quality:idx": 120,
        }
        yield client


@pytest.fixture
def mock_memory():
    with patch("agents.quick_agent.SessionMemory") as mock:
        mem = MagicMock()
        mock.return_value = mem
        yield mem


class TestQuickAgent:
    def test_instantiate(self):
        with patch("agents.quick_agent.FortyGuardClient"), patch("agents.quick_agent.SessionMemory"):
            agent = QuickAgent()
            assert agent is not None

    def test_handle_requires_params(self, mock_api, mock_memory):
        agent = QuickAgent()
        result = agent.handle("test", make_session_id(), {})
        assert "error" in result
        assert "Missing" in result["error"]

    def test_handle_missing_latitude(self, mock_api, mock_memory):
        agent = QuickAgent()
        result = agent.handle("test", make_session_id(), {"longitude": 55, "date": "2026-08-18"})
        assert "error" in result

    def test_handle_missing_longitude(self, mock_api, mock_memory):
        agent = QuickAgent()
        result = agent.handle("test", make_session_id(), {"latitude": 25, "date": "2026-08-18"})
        assert "error" in result

    def test_handle_missing_date(self, mock_api, mock_memory):
        agent = QuickAgent()
        result = agent.handle("test", make_session_id(), {"latitude": 25, "longitude": 55})
        assert "error" in result

    def test_handle_with_valid_params(self, mock_api, mock_memory):
        agent = QuickAgent()
        result = agent.handle("test", make_session_id(), {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-18"})
        assert "response" in result
        assert result["agent"] == "quick"

    def test_handle_logs_to_memory(self, mock_api, mock_memory):
        agent = QuickAgent()
        sid = make_session_id()
        agent.handle("test", sid, {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-18"})
        mock_memory.update_session_context.assert_called()
        mock_memory.log_event.assert_called()

    def test_handle_calls_api(self, mock_api, mock_memory):
        agent = QuickAgent()
        agent.handle("test", make_session_id(), {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-18"})
        mock_api.create_env_params.assert_called_once()

    def test_format_response(self, mock_api, mock_memory):
        agent = QuickAgent()
        response = agent._format_response(
            {
                "heat_index_celsius": 42.5,
                "relative_humidity_percent": 65,
                "air_quality:idx": 120,
            }
        )
        assert "42.5" in response
        assert "65" in response
        assert "120" in response

    def test_format_response_empty(self, mock_api, mock_memory):
        agent = QuickAgent()
        response = agent._format_response({})
        assert "Current Heat Conditions" in response

    def test_format_response_partial_data(self, mock_api, mock_memory):
        agent = QuickAgent()
        response = agent._format_response({"heat_index_celsius": 35})
        assert "35" in response
        assert "Humidity" not in response

    def test_handle_invalid_latitude(self, mock_api, mock_memory):
        agent = QuickAgent()
        result = agent.handle("test", make_session_id(), {"latitude": 91.0, "longitude": 55.0, "date": "2026-08-18"})
        assert "error" in result
        assert "Invalid latitude" in result["error"]

    def test_handle_invalid_longitude(self, mock_api, mock_memory):
        agent = QuickAgent()
        result = agent.handle("test", make_session_id(), {"latitude": 25.0, "longitude": 181.0, "date": "2026-08-18"})
        assert "error" in result
        assert "Invalid longitude" in result["error"]

    def test_handle_boundary_coords(self, mock_api, mock_memory):
        agent = QuickAgent()
        result = agent.handle("test", make_session_id(), {"latitude": 90.0, "longitude": 180.0, "date": "2026-08-18"})
        assert "response" in result


class TestDeepAgent:
    def test_instantiate(self):
        with patch("agents.deep_agent.FortyGuardClient"), patch("agents.deep_agent.SessionMemory"):
            agent = DeepAgent()
            assert agent is not None

    def test_handle_requires_params(self):
        with patch("agents.deep_agent.FortyGuardClient"), patch("agents.deep_agent.SessionMemory"):
            agent = DeepAgent()
            result = agent.handle("test", make_session_id(), {})
            assert "error" in result

    def test_handle_missing_latitude(self):
        with patch("agents.deep_agent.FortyGuardClient"), patch("agents.deep_agent.SessionMemory"):
            agent = DeepAgent()
            result = agent.handle("test", make_session_id(), {"longitude": 55, "date": "2026-08-18"})
            assert "error" in result

    def test_handle_with_valid_params(self):
        with patch("agents.deep_agent.FortyGuardClient") as mock_api, patch("agents.deep_agent.SessionMemory"):
            client = MagicMock()
            mock_api.return_value = client
            client.create_env_params.return_value = "env-123"
            client.create_heat_intelligence.return_value = "intel-123"
            client.wait_for_result.side_effect = [
                {"heat_index_celsius": 42.5, "relative_humidity_percent": 65},
                {"report": "generated"},
            ]
            agent = DeepAgent()
            result = agent.handle(
                "test", make_session_id(), {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-18"}
            )
            assert result["agent"] == "deep"

    def test_handle_with_polygon(self):
        with patch("agents.deep_agent.FortyGuardClient") as mock_api, patch("agents.deep_agent.SessionMemory"):
            client = MagicMock()
            mock_api.return_value = client
            client.create_heatmap.return_value = "hm-123"
            client.create_env_params.return_value = "env-123"
            client.create_heat_intelligence.return_value = "intel-123"
            client.wait_for_result.side_effect = [
                {"stats_data": {"Temperature_stats": {"Maximum": 45}}},
                {"heat_index_celsius": 42.5},
                {"report": "generated"},
            ]
            agent = DeepAgent()
            result = agent.handle(
                "test",
                make_session_id(),
                {
                    "latitude": 25.0,
                    "longitude": 55.0,
                    "date": "2026-08-18",
                    "polygon_aoi": {"type": "FeatureCollection", "features": []},
                },
            )
            assert result["agent"] == "deep"
            client.create_heatmap.assert_called_once()

    def test_handle_logs_to_memory(self):
        with patch("agents.deep_agent.FortyGuardClient") as mock_api:
            with patch("agents.deep_agent.SessionMemory") as mock_mem:
                client = MagicMock()
                mem = MagicMock()
                mock_api.return_value = client
                mock_mem.return_value = mem
                client.create_env_params.return_value = "env-123"
                client.create_heat_intelligence.return_value = "intel-123"
                client.wait_for_result.side_effect = [
                    {"heat_index_celsius": 42.5},
                    {"report": "done"},
                ]
                agent = DeepAgent()
                agent.handle("test", make_session_id(), {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-18"})
                mem.update_session_context.assert_called()
                mem.log_decision.assert_called()

    def test_format_response_full(self):
        with patch("agents.deep_agent.FortyGuardClient"), patch("agents.deep_agent.SessionMemory"):
            agent = DeepAgent()
            response = agent._format_response(
                {
                    "env_params": {"heat_index_celsius": 42.5, "relative_humidity_percent": 65, "air_quality:idx": 120},
                    "heatmap": {"stats_data": {"Temperature_stats": {"Minimum": 35, "Maximum": 48, "Mean": 41}}},
                    "heat_intelligence": {"report": "done"},
                }
            )
            assert "42.5" in response
            assert "Heat Intelligence Report" in response

    def test_format_response_empty(self):
        with patch("agents.deep_agent.FortyGuardClient"), patch("agents.deep_agent.SessionMemory"):
            agent = DeepAgent()
            response = agent._format_response({})
            assert "Comprehensive" in response

    def test_format_response_env_only(self):
        with patch("agents.deep_agent.FortyGuardClient"), patch("agents.deep_agent.SessionMemory"):
            agent = DeepAgent()
            response = agent._format_response({"env_params": {"heat_index_celsius": 30}})
            assert "30" in response

    def test_handle_invalid_latitude(self):
        with patch("agents.deep_agent.FortyGuardClient"), patch("agents.deep_agent.SessionMemory"):
            agent = DeepAgent()
            result = agent.handle(
                "test", make_session_id(), {"latitude": -91.0, "longitude": 55.0, "date": "2026-08-18"}
            )
            assert "error" in result
            assert "Invalid latitude" in result["error"]

    def test_handle_invalid_longitude(self):
        with patch("agents.deep_agent.FortyGuardClient"), patch("agents.deep_agent.SessionMemory"):
            agent = DeepAgent()
            result = agent.handle(
                "test", make_session_id(), {"latitude": 25.0, "longitude": -200.0, "date": "2026-08-18"}
            )
            assert "error" in result
            assert "Invalid longitude" in result["error"]


class TestEmergencyAgent:
    def test_instantiate(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            agent = EmergencyAgent()
            assert agent is not None

    def test_handle_requires_params(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            with patch("agents.emergency_agent.send_alert"):
                agent = EmergencyAgent()
                result = agent.handle("test", make_session_id(), {})
                assert "error" in result

    def test_handle_triggers_alert(self):
        with patch("agents.emergency_agent.FortyGuardClient") as mock_api:
            with patch("agents.emergency_agent.SessionMemory"):
                with patch("agents.emergency_agent.send_alert") as mock_alert:
                    client = MagicMock()
                    mock_api.return_value = client
                    client.create_env_params.return_value = "env-123"
                    client.wait_for_result.return_value = {"heat_index_celsius": 50}
                    agent = EmergencyAgent()
                    result = agent.handle(
                        "test", make_session_id(), {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-18"}
                    )
                    mock_alert.assert_called_once()
                    assert result["agent"] == "emergency"

    def test_assess_severity_extreme(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            agent = EmergencyAgent()
            assert agent._assess_severity(55, {}) == "extreme"

    def test_assess_severity_dangerous(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            agent = EmergencyAgent()
            assert agent._assess_severity(48, {}) == "dangerous"

    def test_assess_severity_emergency(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            agent = EmergencyAgent()
            assert agent._assess_severity(43, {}) == "emergency"

    def test_assess_severity_warning(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            agent = EmergencyAgent()
            assert agent._assess_severity(35, {}) == "warning"

    def test_assess_severity_normal(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            agent = EmergencyAgent()
            assert agent._assess_severity(25, {}) == "normal"

    def test_assess_severity_boundary_extreme(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            agent = EmergencyAgent()
            assert agent._assess_severity(54, {}) == "extreme"

    def test_assess_severity_boundary_dangerous(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            agent = EmergencyAgent()
            assert agent._assess_severity(46, {}) == "dangerous"

    def test_assess_severity_boundary_emergency(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            agent = EmergencyAgent()
            assert agent._assess_severity(41, {}) == "emergency"

    def test_assess_severity_boundary_warning(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            agent = EmergencyAgent()
            assert agent._assess_severity(32, {}) == "warning"

    def test_assess_severity_boundary_normal(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            agent = EmergencyAgent()
            assert agent._assess_severity(31, {}) == "normal"

    def test_recommendations_extreme(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            agent = EmergencyAgent()
            recs = agent._generate_recommendations("extreme", {})
            assert len(recs) >= 3
            assert any("evacuate" in r.lower() for r in recs)

    def test_recommendations_dangerous(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            agent = EmergencyAgent()
            recs = agent._generate_recommendations("dangerous", {})
            assert len(recs) >= 3

    def test_recommendations_emergency(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            agent = EmergencyAgent()
            recs = agent._generate_recommendations("emergency", {})
            assert len(recs) >= 2

    def test_recommendations_warning(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            agent = EmergencyAgent()
            recs = agent._generate_recommendations("warning", {})
            assert len(recs) >= 2

    def test_recommendations_normal(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            agent = EmergencyAgent()
            recs = agent._generate_recommendations("normal", {})
            assert len(recs) == 0

    def test_format_response_extreme(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            agent = EmergencyAgent()
            response = agent._format_response("extreme", 55, ["Evacuate workers"])
            assert "EXTREME" in response
            assert "55" in response
            assert "Evacuate" in response

    def test_format_response_normal(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            agent = EmergencyAgent()
            response = agent._format_response("normal", 25, [])
            assert "NORMAL" in response

    def test_handle_logs_decision(self):
        with patch("agents.emergency_agent.FortyGuardClient") as mock_api:
            with patch("agents.emergency_agent.SessionMemory") as mock_mem:
                with patch("agents.emergency_agent.send_alert"):
                    client = MagicMock()
                    mem = MagicMock()
                    mock_api.return_value = client
                    mock_mem.return_value = mem
                    client.create_env_params.return_value = "env-123"
                    client.wait_for_result.return_value = {"heat_index_celsius": 50}
                    agent = EmergencyAgent()
                    agent.handle("test", make_session_id(), {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-18"})
                    mem.log_decision.assert_called_once()

    def test_handle_zero_heat_index(self):
        with patch("agents.emergency_agent.FortyGuardClient") as mock_api:
            with patch("agents.emergency_agent.SessionMemory"):
                with patch("agents.emergency_agent.send_alert"):
                    client = MagicMock()
                    mock_api.return_value = client
                    client.create_env_params.return_value = "env-123"
                    client.wait_for_result.return_value = {"heat_index_celsius": 0}
                    agent = EmergencyAgent()
                    result = agent.handle(
                        "test", make_session_id(), {"latitude": 25, "longitude": 55, "date": "2026-08-18"}
                    )
                    assert result["severity"] == "normal"

    def test_handle_negative_heat_index(self):
        with patch("agents.emergency_agent.FortyGuardClient") as mock_api:
            with patch("agents.emergency_agent.SessionMemory"):
                with patch("agents.emergency_agent.send_alert"):
                    client = MagicMock()
                    mock_api.return_value = client
                    client.create_env_params.return_value = "env-123"
                    client.wait_for_result.return_value = {"heat_index_celsius": -10}
                    agent = EmergencyAgent()
                    result = agent.handle(
                        "test", make_session_id(), {"latitude": 25, "longitude": 55, "date": "2026-08-18"}
                    )
                    assert result["severity"] == "normal"

    def test_handle_includes_raw_data(self):
        with patch("agents.emergency_agent.FortyGuardClient") as mock_api:
            with patch("agents.emergency_agent.SessionMemory"):
                with patch("agents.emergency_agent.send_alert"):
                    client = MagicMock()
                    mock_api.return_value = client
                    client.create_env_params.return_value = "env-123"
                    client.wait_for_result.return_value = {"heat_index_celsius": 45}
                    agent = EmergencyAgent()
                    result = agent.handle(
                        "test", make_session_id(), {"latitude": 25, "longitude": 55, "date": "2026-08-18"}
                    )
                    assert "raw_data" in result
                    assert "env_params" in result["raw_data"]
                    assert "alert" in result["raw_data"]

    def test_handle_invalid_latitude(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            with patch("agents.emergency_agent.send_alert"):
                agent = EmergencyAgent()
                result = agent.handle(
                    "test", make_session_id(), {"latitude": 91.0, "longitude": 55.0, "date": "2026-08-18"}
                )
                assert "error" in result
                assert "Invalid latitude" in result["error"]

    def test_handle_invalid_longitude(self):
        with patch("agents.emergency_agent.FortyGuardClient"), patch("agents.emergency_agent.SessionMemory"):
            with patch("agents.emergency_agent.send_alert"):
                agent = EmergencyAgent()
                result = agent.handle(
                    "test", make_session_id(), {"latitude": 25.0, "longitude": 181.0, "date": "2026-08-18"}
                )
                assert "error" in result
                assert "Invalid longitude" in result["error"]
