from unittest.mock import MagicMock, patch

import pytest

from config import HEAT_INDEX_THRESHOLD, HEAT_THRESHOLD_C
from monitor.loop import MonitorLoop


@pytest.fixture
def loop():
    with patch("monitor.loop.FortyGuardClient"), patch("monitor.loop.SessionMemory"):
        with patch("monitor.loop.EmergencyAgent"):
            return MonitorLoop()


@pytest.fixture
def mock_api_loop():
    with patch("monitor.loop.FortyGuardClient") as mock_api, patch("monitor.loop.SessionMemory") as mock_mem:
        with patch("monitor.loop.EmergencyAgent") as mock_emerg:
            client = MagicMock()
            mem = MagicMock()
            agent = MagicMock()
            mock_api.return_value = client
            mock_mem.return_value = mem
            mock_emerg.return_value = agent
            yield client, mem, agent


class TestMonitorLoopInit:
    def test_instantiate(self, loop):
        assert loop is not None
        assert loop.zones == []

    def test_zones_empty(self, loop):
        assert isinstance(loop.zones, list)
        assert len(loop.zones) == 0


class TestAddZone:
    def test_add_zone(self, loop):
        loop.add_zone("Dubai", {"type": "FeatureCollection", "features": []}, 25.0, 55.0)
        assert len(loop.zones) == 1
        assert loop.zones[0]["name"] == "Dubai"
        assert loop.zones[0]["latitude"] == 25.0
        assert loop.zones[0]["longitude"] == 55.0
        assert "polygon_aoi" in loop.zones[0]

    def test_add_multiple_zones(self, loop):
        loop.add_zone("Dubai", {"type": "FeatureCollection", "features": []}, 25.0, 55.0)
        loop.add_zone("Abu Dhabi", {"type": "FeatureCollection", "features": []}, 24.5, 54.7)
        assert len(loop.zones) == 2

    def test_add_zone_duplicate_name(self, loop):
        loop.add_zone("Dubai", {"type": "FeatureCollection", "features": []}, 25.0, 55.0)
        loop.add_zone("Dubai", {"type": "FeatureCollection", "features": []}, 25.1, 55.1)
        assert len(loop.zones) == 2

    def test_add_zone_empty_name(self, loop):
        loop.add_zone("", {"type": "FeatureCollection", "features": []}, 25.0, 55.0)
        assert len(loop.zones) == 1

    def test_add_zone_extreme_coords(self, loop):
        loop.add_zone("Pole", {"type": "FeatureCollection", "features": []}, 90.0, 180.0)
        assert loop.zones[0]["latitude"] == 90.0
        assert loop.zones[0]["longitude"] == 180.0

    def test_add_zone_negative_coords(self, loop):
        loop.add_zone("South", {"type": "FeatureCollection", "features": []}, -90.0, -180.0)
        assert loop.zones[0]["latitude"] == -90.0

    def test_add_zone_zero_coords(self, loop):
        loop.add_zone("Origin", {"type": "FeatureCollection", "features": []}, 0.0, 0.0)
        assert loop.zones[0]["latitude"] == 0.0

    def test_many_zones(self, loop):
        for i in range(50):
            loop.add_zone(f"Zone_{i}", {"type": "FeatureCollection", "features": []}, 25.0 + i, 55.0)
        assert len(loop.zones) == 50


class TestCheckZone:
    def test_check_zone_returns_reading(self, mock_api_loop):
        client, mem, agent = mock_api_loop
        client.create_heatmap.return_value = "hm-123"
        client.create_env_params.return_value = "env-123"
        client.wait_for_result.side_effect = [
            {"stats_data": {"Temperature_stats": {"Maximum": 35}}},
            {"heat_index_celsius": 35, "relative_humidity": 50},
        ]
        loop = MonitorLoop()
        loop.add_zone("Dubai", {"type": "FeatureCollection", "features": []}, 25.0, 55.0)
        reading = loop.check_zone(loop.zones[0])
        assert "heatmap" in reading
        assert "env_params" in reading
        assert reading["zone"] == "Dubai"

    def test_check_zone_logs_event(self, mock_api_loop):
        client, mem, agent = mock_api_loop
        client.create_heatmap.return_value = "hm-123"
        client.create_env_params.return_value = "env-123"
        client.wait_for_result.side_effect = [
            {"stats_data": {}},
            {"heat_index_celsius": 35},
        ]
        loop = MonitorLoop()
        loop.add_zone("Dubai", {"type": "FeatureCollection", "features": []}, 25.0, 55.0)
        loop.check_zone(loop.zones[0])
        mem.log_event.assert_called_once()

    def test_check_zone_api_error(self, mock_api_loop):
        client, mem, agent = mock_api_loop
        client.create_heatmap.side_effect = Exception("API down")
        loop = MonitorLoop()
        loop.add_zone("Dubai", {"type": "FeatureCollection", "features": []}, 25.0, 55.0)
        with pytest.raises(Exception, match="API down"):
            loop.check_zone(loop.zones[0])

    def test_check_zone_empty_polygon(self, mock_api_loop):
        client, mem, agent = mock_api_loop
        client.create_heatmap.return_value = "hm-123"
        client.create_env_params.return_value = "env-123"
        client.wait_for_result.side_effect = [
            {"stats_data": {}},
            {"heat_index_celsius": 35},
        ]
        loop = MonitorLoop()
        loop.add_zone("Test", {}, 25.0, 55.0)
        reading = loop.check_zone(loop.zones[0])
        assert "env_params" in reading


class TestAnalyzeReading:
    def test_above_heat_index_celsius_threshold(self, loop):
        reading = {"env_params": {"heat_index_celsius": HEAT_INDEX_THRESHOLD + 5}}
        assert loop.analyze_reading(reading) is True

    def test_below_heat_index_celsius_threshold(self, loop):
        reading = {"env_params": {"heat_index_celsius": 20}}
        assert loop.analyze_reading(reading) is False

    def test_exact_heat_index_celsius_threshold(self, loop):
        reading = {"env_params": {"heat_index_celsius": HEAT_INDEX_THRESHOLD}}
        assert loop.analyze_reading(reading) is True

    def test_above_heat_threshold_in_heatmap(self, loop):
        reading = {
            "env_params": {"heat_index_celsius": 20},
            "heatmap": {"stats_data": {"Temperature_stats": {"Maximum": HEAT_THRESHOLD_C + 5}}},
        }
        assert loop.analyze_reading(reading) is True

    def test_below_heat_threshold_in_heatmap(self, loop):
        reading = {
            "env_params": {"heat_index_celsius": 20},
            "heatmap": {"stats_data": {"Temperature_stats": {"Maximum": 30}}},
        }
        assert loop.analyze_reading(reading) is False

    def test_missing_env_params(self, loop):
        reading = {}
        assert loop.analyze_reading(reading) is False

    def test_missing_heatmap(self, loop):
        reading = {"env_params": {"heat_index_celsius": 20}}
        assert loop.analyze_reading(reading) is False

    def test_missing_stats(self, loop):
        reading = {"env_params": {"heat_index_celsius": 20}, "heatmap": {}}
        assert loop.analyze_reading(reading) is False

    def test_zero_heat_index_celsius(self, loop):
        reading = {"env_params": {"heat_index_celsius": 0}}
        assert loop.analyze_reading(reading) is False

    def test_negative_heat_index_celsius(self, loop):
        reading = {"env_params": {"heat_index_celsius": -10}}
        assert loop.analyze_reading(reading) is False

    def test_extreme_heat_index_celsius(self, loop):
        reading = {"env_params": {"heat_index_celsius": 60}}
        assert loop.analyze_reading(reading) is True

    def test_empty_heatmap_stats(self, loop):
        reading = {
            "env_params": {"heat_index_celsius": 20},
            "heatmap": {"stats_data": {"Temperature_stats": {}}},
        }
        assert loop.analyze_reading(reading) is False


class TestTriggerEmergency:
    def test_triggers_emergency_agent(self, mock_api_loop):
        client, mem, agent = mock_api_loop
        loop = MonitorLoop()
        loop.add_zone("Dubai", {"type": "FeatureCollection", "features": []}, 25.0, 55.0)
        reading = {"env_params": {"heat_index_celsius": 50}}
        loop.trigger_emergency(loop.zones[0], reading)
        agent.handle.assert_called_once()
        call_kwargs = agent.handle.call_args[1]
        assert call_kwargs["params"]["latitude"] == 25.0
        assert call_kwargs["params"]["longitude"] == 55.0


class TestRunCheck:
    def test_run_check_calls_check_zone(self, mock_api_loop):
        client, mem, agent = mock_api_loop
        client.create_heatmap.return_value = "hm-123"
        client.create_env_params.return_value = "env-123"
        client.wait_for_result.side_effect = [
            {"stats_data": {}},
            {"heat_index_celsius": 25},
        ]
        loop = MonitorLoop()
        loop.add_zone("Dubai", {"type": "FeatureCollection", "features": []}, 25.0, 55.0)
        loop.run_check()

    def test_run_check_triggers_emergency_on_high(self, mock_api_loop):
        client, mem, agent = mock_api_loop
        client.create_heatmap.return_value = "hm-123"
        client.create_env_params.return_value = "env-123"
        client.wait_for_result.side_effect = [
            {"stats_data": {}},
            {"heat_index_celsius": HEAT_INDEX_THRESHOLD + 10},
        ]
        loop = MonitorLoop()
        loop.add_zone("Dubai", {"type": "FeatureCollection", "features": []}, 25.0, 55.0)
        loop.run_check()
        agent.handle.assert_called_once()

    def test_run_check_handles_api_error(self, mock_api_loop):
        client, mem, agent = mock_api_loop
        client.create_heatmap.side_effect = Exception("API Error")
        loop = MonitorLoop()
        loop.add_zone("Dubai", {"type": "FeatureCollection", "features": []}, 25.0, 55.0)
        loop.run_check()
        agent.handle.assert_not_called()
