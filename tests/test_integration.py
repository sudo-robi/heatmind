import pytest
import uuid
from unittest.mock import patch, MagicMock
from datetime import datetime


def make_session_id():
    return str(uuid.uuid4())


class TestEndToEndFlow:
    def test_full_quick_flow(self):
        with patch("agents.quick_agent.FortyGuardClient") as mock_api:
            with patch("agents.quick_agent.SessionMemory"):
                client = MagicMock()
                mock_api.return_value = client
                client.create_env_params.return_value = "act-123"
                client.wait_for_result.return_value = {
                    "heat_index_celsius": 42.5,
                    "relative_humidity_percent": 65,
                    "air_quality:idx": 120,
                }
                from agents.quick_agent import QuickAgent
                agent = QuickAgent()
                result = agent.handle(
                    "what is the temperature",
                    make_session_id(),
                    {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-18"}
                )
                assert result["agent"] == "quick"
                assert "42.5" in result["response"]

    def test_full_router_to_agent_flow(self):
        from agents.router import route_query
        query = "what is the temperature in Dubai"
        routing = route_query(query)
        assert routing.agent == "quick"

        query2 = "give me a comprehensive heat risk assessment with all data"
        routing2 = route_query(query2)
        assert routing2.agent == "deep"

        query3 = "EMERGENCY extreme heat danger warning"
        routing3 = route_query(query3)
        assert routing3.agent == "emergency"

    def test_memory_persists_across_queries(self):
        from memory.session import SessionMemory
        mem = SessionMemory()
        sid = mem.create_session("integration_user")
        try:
            mem.update_session_context(sid, "last_zone", "Dubai")
            ctx1 = mem.get_session_context(sid)
            assert ctx1["last_zone"] == "Dubai"

            mem.update_session_context(sid, "last_zone", "Abu Dhabi")
            ctx2 = mem.get_session_context(sid)
            assert ctx2["last_zone"] == "Abu Dhabi"
            assert ctx2["last_zone"] != "Dubai"
        finally:
            mem.sessions.drop()
            mem.events.drop()
            mem.decisions.drop()

    def test_monitor_analyze_threshold(self):
        with patch("monitor.loop.FortyGuardClient"):
            with patch("monitor.loop.SessionMemory"):
                with patch("monitor.loop.EmergencyAgent"):
                    from monitor.loop import MonitorLoop
                    from config import HEAT_INDEX_THRESHOLD
                    loop = MonitorLoop()
                    reading = {"env_params": {"heat_index_celsius": HEAT_INDEX_THRESHOLD + 10}}
                    assert loop.analyze_reading(reading) is True
                    reading2 = {"env_params": {"heat_index_celsius": 10}}
                    assert loop.analyze_reading(reading2) is False

    def test_emergency_agent_full_flow(self):
        with patch("agents.emergency_agent.FortyGuardClient") as mock_api:
            with patch("agents.emergency_agent.SessionMemory"):
                with patch("agents.emergency_agent.send_alert") as mock_alert:
                    client = MagicMock()
                    mock_api.return_value = client
                    client.create_env_params.return_value = "env-123"
                    client.wait_for_result.return_value = {"heat_index_celsius": 55}
                    from agents.emergency_agent import EmergencyAgent
                    agent = EmergencyAgent()
                    result = agent.handle(
                        "EMERGENCY heat alert",
                        make_session_id(),
                        {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-18"}
                    )
                    assert result["agent"] == "emergency"
                    assert result["severity"] == "extreme"
                    mock_alert.assert_called_once()

    def test_deep_agent_full_flow(self):
        with patch("agents.deep_agent.FortyGuardClient") as mock_api:
            with patch("agents.deep_agent.SessionMemory"):
                client = MagicMock()
                mock_api.return_value = client
                client.create_env_params.return_value = "env-123"
                client.create_heat_intelligence.return_value = "intel-123"
                client.wait_for_result.side_effect = [
                    {"heat_index_celsius": 42.5, "relative_humidity_percent": 65},
                    {"report": "Heat intelligence generated successfully"},
                ]
                from agents.deep_agent import DeepAgent
                agent = DeepAgent()
                result = agent.handle(
                    "full assessment needed",
                    make_session_id(),
                    {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-18"}
                )
                assert result["agent"] == "deep"
                assert "42.5" in result["response"]

    def test_emergency_recommends_evacuation_on_extreme(self):
        with patch("agents.emergency_agent.FortyGuardClient") as mock_api:
            with patch("agents.emergency_agent.SessionMemory"):
                with patch("agents.emergency_agent.send_alert"):
                    client = MagicMock()
                    mock_api.return_value = client
                    client.create_env_params.return_value = "env-123"
                    client.wait_for_result.return_value = {"heat_index_celsius": 60}
                    from agents.emergency_agent import EmergencyAgent
                    agent = EmergencyAgent()
                    result = agent.handle(
                        "EMERGENCY", make_session_id(),
                        {"latitude": 25.0, "longitude": 55.0, "date": "2026-08-18"}
                    )
                    assert "Evacuate" in result["response"]
                    assert result["severity"] == "extreme"

    def test_quick_agent_missing_params_returns_error(self):
        with patch("agents.quick_agent.FortyGuardClient"):
            with patch("agents.quick_agent.SessionMemory"):
                from agents.quick_agent import QuickAgent
                agent = QuickAgent()
                result = agent.handle("test", make_session_id(), {})
                assert "error" in result
                assert "Missing" in result["error"]
