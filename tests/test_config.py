import os

import pytest


class TestConfigLoading:
    def test_default_values(self):
        os.environ["MONGO_DB"] = "heatmind_test"
        import importlib

        import config

        importlib.reload(config)
        assert config.FORTYGUARD_BASE_URL == "https://api.fortyguard.com/v1"
        assert config.MONGO_DB == "heatmind_test"
        assert config.HEAT_THRESHOLD_C == 40.0
        assert config.HEAT_INDEX_THRESHOLD == 45
        assert config.MONITOR_INTERVAL_MINUTES == 30

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("HEAT_THRESHOLD_C", "35")
        monkeypatch.setenv("HEAT_INDEX_THRESHOLD", "40")
        import importlib

        import config

        importlib.reload(config)
        assert config.HEAT_THRESHOLD_C == 35.0
        assert config.HEAT_INDEX_THRESHOLD == 40

    def test_empty_api_key(self):
        import importlib

        import config

        importlib.reload(config)
        assert isinstance(config.FORTYGUARD_API_KEY, str)

    def test_mongo_uri_format(self):
        import importlib

        import config

        importlib.reload(config)
        if config.MONGO_URI:
            assert config.MONGO_URI.startswith("mongodb://") or config.MONGO_URI.startswith("mongodb+srv://")

    def test_smtp_port_is_int(self):
        import importlib

        import config

        importlib.reload(config)
        assert isinstance(config.SMTP_PORT, int)
        assert 1 <= config.SMTP_PORT <= 65535


class TestConfigEdgeCases:
    def test_invalid_port_env(self, monkeypatch):
        monkeypatch.setenv("SMTP_PORT", "not_a_number")
        with pytest.raises(ValueError):
            import importlib

            import config

            importlib.reload(config)

    def test_negative_threshold(self, monkeypatch):
        monkeypatch.setenv("HEAT_THRESHOLD_C", "-10")
        import importlib

        import config

        importlib.reload(config)
        assert config.HEAT_THRESHOLD_C == -10.0

    def test_zero_interval(self, monkeypatch):
        monkeypatch.setenv("MONITOR_INTERVAL_MINUTES", "0")
        import importlib

        import config

        importlib.reload(config)
        assert config.MONITOR_INTERVAL_MINUTES == 0

    def test_large_threshold(self, monkeypatch):
        monkeypatch.setenv("HEAT_THRESHOLD_C", "1000")
        import importlib

        import config

        importlib.reload(config)
        assert config.HEAT_THRESHOLD_C == 1000.0

    def test_atlas_uri_format(self, monkeypatch):
        monkeypatch.setenv(
            "MONGO_URI", "mongodb+srv://user:pass@cluster0.mongodb.net/heatmind?retryWrites=true&w=majority"
        )
        import importlib

        import config

        importlib.reload(config)
        assert "mongodb+srv://" in config.MONGO_URI
        assert "cluster0" in config.MONGO_URI
