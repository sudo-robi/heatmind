"""Tests for context compression (utils/compression.py)."""

from utils.compression import compress_for_synthesis, compress_observations


class TestCompressObservations:
    def test_empty_observations(self):
        result = compress_observations({})
        assert result == ""

    def test_none_values_dropped(self):
        obs = {"env_params": None, "heatmap": None}
        result = compress_observations(obs)
        assert result == ""

    def test_env_params_prioritized(self):
        obs = {
            "streetview": {"image_url": "http://example.com/img.jpg"},
            "env_params": {"heat_index": 42.5, "relative_humidity": 65},
        }
        result = compress_observations(obs)
        lines = result.strip().split("\n")
        assert "heat_index" in lines[0]

    def test_heatmap_stats(self):
        obs = {
            "heatmap": {
                "stats_data": {
                    "Temperature_stats": {"Minimum": 35, "Maximum": 48, "Mean": 41},
                }
            }
        }
        result = compress_observations(obs)
        assert "Minimum" in result or "Temperature_stats" in result

    def test_max_tokens_truncates(self):
        obs = {
            "env_params": {"heat_index": 42, "humidity": 65, "aqi": 120},
            "heatmap": {"data": "x" * 5000},
            "satellite": {"data": "y" * 5000},
        }
        result = compress_observations(obs, max_tokens=50)
        assert "[truncated]" in result or len(result) < 2000

    def test_list_values(self):
        obs = {"alerts": [{"level": "high"}, {"level": "low"}]}
        result = compress_observations(obs)
        assert "2 items" in result

    def test_string_value(self):
        obs = {"summary": "Heat alert for downtown"}
        result = compress_observations(obs)
        assert "Heat alert" in result

    def test_unknown_keys_appended(self):
        obs = {"custom_tool": {"key": "val"}}
        result = compress_observations(obs)
        assert "custom_tool" in result


class TestCompressForSynthesis:
    def test_empty(self):
        result = compress_for_synthesis({})
        assert result == ""

    def test_env_params(self):
        obs = {"env_params": {"heat_index_celsius": 45, "relative_humidity_percent": 70, "air_quality:idx": 150}}
        result = compress_for_synthesis(obs)
        assert "heat_index_celsius: 45" in result
        assert "relative_humidity_percent: 70" in result
        assert "air_quality:idx: 150" in result

    def test_heatmap_stats(self):
        obs = {
            "heatmap": {
                "stats_data": {
                    "Temperature_stats": {"Minimum": 30, "Maximum": 50, "Mean": 40},
                }
            }
        }
        result = compress_for_synthesis(obs)
        assert "HEATMAP" in result
        assert "min=30" in result

    def test_heat_intelligence(self):
        obs = {"heat_intelligence": {"risk_level": "extreme", "summary": "Critical heat"}}
        result = compress_for_synthesis(obs)
        assert "risk=extreme" in result
        assert "Critical heat" in result

    def test_plan_included(self):
        obs = {"env_params": {"heat_index": 40}}
        plan = {"tool_calls": [{"tool": "env_params"}, {"tool": "heatmap"}]}
        result = compress_for_synthesis(obs, plan=plan)
        assert "PLAN tools" in result
        assert "env_params" in result

    def test_max_tokens_truncates(self):
        obs = {"env_params": {"heat_index": 40}, "heatmap": {"data": "x" * 10000}}
        result = compress_for_synthesis(obs, max_tokens=20)
        assert "[compressed]" in result or len(result) < 500
