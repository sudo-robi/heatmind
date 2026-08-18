from unittest.mock import MagicMock, patch

import pytest

from api.fortyguard import FortyGuardClient


@pytest.fixture
def client():
    return FortyGuardClient(api_key="test_key_123")


class TestClientInit:
    def test_instantiate(self):
        c = FortyGuardClient(api_key="test")
        assert c.api_key == "test"
        assert c.base_url == "https://api.fortyguard.com/v1"
        assert c.headers["api-key"] == "test"
        assert c.headers["Content-Type"] == "application/json"

    def test_empty_key(self):
        with pytest.raises(ValueError):
            FortyGuardClient(api_key="")

    def test_long_key(self):
        c = FortyGuardClient(api_key="x" * 1000)
        assert len(c.api_key) == 1000


class TestCreateEnvParams:
    def test_success(self, client):
        with patch("api.fortyguard.requests.post") as mock:
            resp = MagicMock()
            resp.json.return_value = {"error": False, "status_code": 200, "data": {"activity_id": "act-123"}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            result = client.create_env_params(
                latitude=25.0,
                longitude=55.0,
                temperature=35.0,
                start_date="2026-08-18",
            )
            assert result == "act-123"

    def test_api_error(self, client):
        with patch("api.fortyguard.requests.post") as mock:
            resp = MagicMock()
            resp.json.return_value = {"error": True, "message": "Invalid"}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            result = client.create_env_params(
                latitude=25.0,
                longitude=55.0,
                temperature=35.0,
                start_date="2026-08-18",
            )
            assert result is None

    def test_connection_error(self, client):
        with patch("api.fortyguard.requests.post") as mock:
            mock.side_effect = Exception("Connection refused")
            result = client.create_env_params(
                latitude=25.0,
                longitude=55.0,
                temperature=35.0,
                start_date="2026-08-18",
            )
            assert result is None

    def test_sends_correct_payload(self, client):
        with patch("api.fortyguard.requests.post") as mock:
            resp = MagicMock()
            resp.json.return_value = {"error": False, "data": {"activity_id": "act-456"}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            client.create_env_params(
                latitude=25.0,
                longitude=55.0,
                temperature=35.0,
                start_date="2026-08-18",
            )
            call_kwargs = mock.call_args
            payload = call_kwargs[1]["json"]
            assert payload["latitude"] == 25.0
            assert payload["longitude"] == 55.0
            assert payload["temperature"] == 35.0
            assert payload["date_time"]["start_date"] == "2026-08-18"


class TestCreateHeatmap:
    def test_success(self, client):
        with patch("api.fortyguard.requests.post") as mock:
            resp = MagicMock()
            resp.json.return_value = {"error": False, "data": {"activity_id": "hm-123"}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            result = client.create_heatmap(
                polygon_aoi={"type": "FeatureCollection", "features": []},
                start_date="2026-08-18",
            )
            assert result == "hm-123"

    def test_with_optional_params(self, client):
        with patch("api.fortyguard.requests.post") as mock:
            resp = MagicMock()
            resp.json.return_value = {"error": False, "data": {"activity_id": "hm-456"}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            result = client.create_heatmap(
                polygon_aoi={"type": "FeatureCollection", "features": []},
                start_date="2026-08-18",
                start_time="12:00",
                end_time="18:00",
                end_date="2026-08-19",
                granularity=50,
            )
            assert result == "hm-456"

    def test_error(self, client):
        with patch("api.fortyguard.requests.post") as mock:
            mock.side_effect = Exception("Bad polygon")
            result = client.create_heatmap(
                polygon_aoi={},
                start_date="2026-08-18",
            )
            assert result is None


class TestCreateHeatIntelligence:
    def test_success(self, client):
        with patch("api.fortyguard.requests.post") as mock:
            resp = MagicMock()
            resp.json.return_value = {"error": False, "data": {"activity_id": "intel-123"}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            result = client.create_heat_intelligence(
                latitude=25.0,
                longitude=55.0,
                temperature=42.5,
                date="2026-08-18",
                analysis=["environmental", "urban"],
            )
            assert result == "intel-123"

    def test_error(self, client):
        with patch("api.fortyguard.requests.post") as mock:
            mock.side_effect = Exception("Invalid")
            result = client.create_heat_intelligence(
                latitude=25.0,
                longitude=55.0,
                temperature=42.5,
                date="2026-08-18",
                analysis=["environmental"],
            )
            assert result is None


class TestCreateSatellite:
    def test_success(self, client):
        with patch("api.fortyguard.requests.post") as mock:
            resp = MagicMock()
            resp.json.return_value = {"error": False, "data": {"activity_id": "sat-123"}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            result = client.create_satellite(
                latitude=25.0,
                longitude=55.0,
                start_date="2026-08-18",
            )
            assert result == "sat-123"


class TestCreateStreetview:
    def test_success(self, client):
        with patch("api.fortyguard.requests.post") as mock:
            resp = MagicMock()
            resp.json.return_value = {"error": False, "data": {"activity_id": "sv-123"}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            result = client.create_streetview(latitude=25.0, longitude=55.0)
            assert result == "sv-123"


class TestWaitForResult:
    def test_immediate_complete(self, client):
        with patch("api.fortyguard.requests.get") as mock:
            resp = MagicMock()
            resp.json.return_value = {"data": {"status": "completed", "result": {"heat_index": 42}}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            result = client.wait_for_result("act-123", timeout=5, poll_interval=0.1)
            assert result == {"heat_index": 42}

    def test_succeeded_status(self, client):
        with patch("api.fortyguard.requests.get") as mock:
            resp = MagicMock()
            resp.json.return_value = {"data": {"status": "succeeded", "result": {"temp": 35}}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            result = client.wait_for_result("act-123", timeout=5, poll_interval=0.1)
            assert result == {"temp": 35}

    def test_poll_then_complete(self, client):
        with patch("api.fortyguard.requests.get") as mock:
            resp_pending = MagicMock()
            resp_pending.json.return_value = {"data": {"status": "pending"}}
            resp_pending.raise_for_status = MagicMock()
            resp_done = MagicMock()
            resp_done.json.return_value = {"data": {"status": "completed", "result": {"temp": 35}}}
            resp_done.raise_for_status = MagicMock()
            mock.side_effect = [resp_pending, resp_done]
            result = client.wait_for_result("act-123", timeout=5, poll_interval=0.01)
            assert result == {"temp": 35}

    def test_timeout(self, client):
        with patch("api.fortyguard.requests.get") as mock:
            resp = MagicMock()
            resp.json.return_value = {"data": {"status": "pending"}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            with pytest.raises(TimeoutError):
                client.wait_for_result("act-123", timeout=0.1, poll_interval=0.05)

    def test_api_error_during_poll(self, client):
        with patch("api.fortyguard.requests.get") as mock:
            mock.side_effect = Exception("Network error")
            with pytest.raises(RuntimeError, match="failed"):
                client.wait_for_result("act-123", timeout=1, poll_interval=0.01)

    def test_failed_activity(self, client):
        with patch("api.fortyguard.requests.get") as mock:
            resp = MagicMock()
            resp.json.return_value = {"data": {"status": "failed", "error": "Processing failed"}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            with pytest.raises(RuntimeError, match="failed"):
                client.wait_for_result("act-123", timeout=5, poll_interval=0.1)

    def test_error_status(self, client):
        with patch("api.fortyguard.requests.get") as mock:
            resp = MagicMock()
            resp.json.return_value = {"data": {"status": "error"}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            with pytest.raises(RuntimeError, match="failed"):
                client.wait_for_result("act-123", timeout=5, poll_interval=0.1)


class TestGetStatus:
    def test_success(self, client):
        with patch("api.fortyguard.requests.get") as mock:
            resp = MagicMock()
            resp.json.return_value = {"data": {"status": "completed"}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            result = client.get_status("act-123")
            assert result == {"data": {"status": "completed"}}

    def test_uses_correct_url(self, client):
        with patch("api.fortyguard.requests.get") as mock:
            resp = MagicMock()
            resp.json.return_value = {"data": {"status": "pending"}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            client.get_status("act-456")
            call_url = mock.call_args[0][0]
            assert "status/act-456" in call_url


class TestAPIClientEdgeCases:
    def test_unicode_latitude(self, client):
        with patch("api.fortyguard.requests.post") as mock:
            mock.side_effect = Exception("Invalid latitude")
            result = client.create_env_params(
                latitude=25.0,
                longitude=55.0,
                temperature=35.0,
                start_date="2026-08-18",
            )
            assert result is None

    def test_extreme_coordinates(self, client):
        with patch("api.fortyguard.requests.post") as mock:
            resp = MagicMock()
            resp.json.return_value = {"error": False, "data": {"activity_id": "act-extreme"}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            result = client.create_env_params(
                latitude=90.0,
                longitude=180.0,
                temperature=35.0,
                start_date="2026-08-18",
            )
            assert result == "act-extreme"

    def test_past_date(self, client):
        with patch("api.fortyguard.requests.post") as mock:
            resp = MagicMock()
            resp.json.return_value = {"error": False, "data": {"activity_id": "act-past"}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            result = client.create_env_params(
                latitude=25.0,
                longitude=55.0,
                temperature=35.0,
                start_date="2020-01-01",
            )
            assert result == "act-past"

    def test_future_date(self, client):
        with patch("api.fortyguard.requests.post") as mock:
            resp = MagicMock()
            resp.json.return_value = {"error": False, "data": {"activity_id": "act-future"}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            result = client.create_env_params(
                latitude=25.0,
                longitude=55.0,
                temperature=35.0,
                start_date="2030-12-31",
            )
            assert result == "act-future"

    def test_empty_polygon(self, client):
        with patch("api.fortyguard.requests.post") as mock:
            resp = MagicMock()
            resp.json.return_value = {"error": False, "data": {"activity_id": "act-empty"}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            result = client.create_heatmap(
                polygon_aoi={"type": "FeatureCollection", "features": []},
                start_date="2026-08-18",
            )
            assert result == "act-empty"

    def test_many_parameters(self, client):
        with patch("api.fortyguard.requests.post") as mock:
            resp = MagicMock()
            resp.json.return_value = {"error": False, "data": {"activity_id": "act-many"}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            result = client.create_env_params(
                latitude=25.0,
                longitude=55.0,
                temperature=35.0,
                start_date="2026-08-18",
            )
            assert result == "act-many"

    def test_headers_sent(self, client):
        with patch("api.fortyguard.requests.post") as mock:
            resp = MagicMock()
            resp.json.return_value = {"error": False, "data": {"activity_id": "act-h"}}
            resp.raise_for_status = MagicMock()
            mock.return_value = resp
            client.create_env_params(
                latitude=25.0,
                longitude=55.0,
                temperature=35.0,
                start_date="2026-08-18",
            )
            headers = mock.call_args[1]["headers"]
            assert headers["api-key"] == "test_key_123"
            assert headers["Content-Type"] == "application/json"
