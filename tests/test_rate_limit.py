"""Tests for API rate limiting and client behavior."""

import time
from unittest.mock import MagicMock, patch

import pytest

from api.fortyguard import FortyGuardClient


@pytest.fixture
def client():
    return FortyGuardClient(api_key="test-key-123")


class TestRateLimiter:
    def test_rate_limit_deque_maxlen(self, client):
        assert client._request_timestamps.maxlen == 50

    def test_call_log_maxlen(self, client):
        assert client._call_log.maxlen == 100

    def test_check_rate_limit_allows_normal_usage(self, client):
        client._check_rate_limit()
        assert len(client._request_timestamps) == 1

    def test_check_rate_limit_tracks_timestamps(self, client):
        for _ in range(5):
            client._check_rate_limit()
        assert len(client._request_timestamps) == 5

    def test_check_rate_limit_prunes_old_timestamps(self, client):
        client._check_rate_limit()
        client._request_timestamps.append(time.time() - 120)
        client._check_rate_limit()
        assert len(client._request_timestamps) == 2

    def test_check_rate_limit_sleeps_when_exceeded(self, client):
        client._rate_limit = 2
        client._rate_window = 60.0
        client._check_rate_limit()
        client._check_rate_limit()
        with patch("api.fortyguard.time.sleep") as mock_sleep:
            client._check_rate_limit()
            mock_sleep.assert_called_once()

    def test_get_call_log_returns_and_clears(self, client):
        client._call_log.append({"method": "POST", "url": "/v1/test", "timestamp": time.time()})
        log = client.get_call_log()
        assert len(log) == 1
        assert len(client._call_log) == 0

    def test_get_call_log_empty(self, client):
        log = client.get_call_log()
        assert log == []


class TestFortyGuardClient:
    def test_init_requires_api_key(self):
        with pytest.raises(ValueError, match="FORTYGUARD_API_KEY"):
            FortyGuardClient(api_key="")

    def test_init_with_key(self, client):
        assert client.api_key == "test-key-123"
        assert client.base_url == "https://api.fortyguard.com/v1"

    def test_headers_include_api_key(self, client):
        assert client.headers["api-key"] == "test-key-123"
        assert client.headers["Content-Type"] == "application/json"

    @patch("api.fortyguard.requests.post")
    def test_post_records_call_log(self, mock_post, client):
        mock_post.return_value = MagicMock(
            json=lambda: {"data": {"activity_id": "123"}},
            raise_for_status=lambda: None,
        )
        client._post("env_params", {})
        log = client.get_call_log()
        assert len(log) == 1
        assert log[0]["method"] == "POST"
        assert "/v1/env_params" in log[0]["url"]

    @patch("api.fortyguard.requests.get")
    def test_get_records_call_log(self, mock_get, client):
        mock_get.return_value = MagicMock(
            json=lambda: {"data": {"status": "completed"}},
            raise_for_status=lambda: None,
        )
        client._get("status/test-id")
        log = client.get_call_log()
        assert len(log) == 1
        assert log[0]["method"] == "GET"

    @patch("api.fortyguard.requests.post")
    def test_create_env_params_returns_activity_id(self, mock_post, client):
        mock_post.return_value = MagicMock(
            json=lambda: {"data": {"activity_id": "abc-123"}},
            raise_for_status=lambda: None,
        )
        result = client.create_env_params(latitude=33.45, longitude=-112.07, temperature=35.0, start_date="2026-08-15")
        assert result == "abc-123"

    @patch("api.fortyguard.requests.post")
    def test_create_env_params_handles_error(self, mock_post, client):
        mock_post.return_value = MagicMock(raise_for_status=MagicMock(side_effect=Exception("500 error")))
        result = client.create_env_params(latitude=33.45, longitude=-112.07, temperature=35.0, start_date="2026-08-15")
        assert result is None

    @patch("api.fortyguard.requests.post")
    def test_create_heatmap_returns_activity_id(self, mock_post, client):
        mock_post.return_value = MagicMock(
            json=lambda: {"data": {"activity_id": "heat-456"}},
            raise_for_status=lambda: None,
        )
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
        result = client.create_heatmap(polygon_aoi=polygon, start_date="2026-08-15")
        assert result == "heat-456"

    @patch("api.fortyguard.requests.get")
    def test_get_credits_returns_type_on_error(self, mock_get, client):
        mock_get.return_value = MagicMock(raise_for_status=MagicMock(side_effect=Exception("timeout")))
        result = client.get_credits()
        assert "error" in result
        assert result["error"] == "Exception"

    @patch("api.fortyguard.requests.post")
    def test_create_satellite(self, mock_post, client):
        mock_post.return_value = MagicMock(
            json=lambda: {"data": {"activity_id": "sat-789"}},
            raise_for_status=lambda: None,
        )
        result = client.create_satellite(latitude=33.45, longitude=-112.07, start_date="2026-08-15")
        assert result == "sat-789"

    @patch("api.fortyguard.requests.post")
    def test_create_streetview(self, mock_post, client):
        mock_post.return_value = MagicMock(
            json=lambda: {"data": {"activity_id": "sv-012"}},
            raise_for_status=lambda: None,
        )
        result = client.create_streetview(latitude=33.45, longitude=-112.07)
        assert result == "sv-012"

    @patch("api.fortyguard.requests.post")
    def test_create_heat_intelligence(self, mock_post, client):
        mock_post.return_value = MagicMock(
            json=lambda: {"data": {"activity_id": "hi-345"}},
            raise_for_status=lambda: None,
        )
        result = client.create_heat_intelligence(
            latitude=33.45,
            longitude=-112.07,
            temperature=42.0,
            date="2026-08-15",
            analysis=["geographic"],
        )
        assert result == "hi-345"

    @patch("api.fortyguard.requests.get")
    def test_get_status(self, mock_get, client):
        mock_get.return_value = MagicMock(
            json=lambda: {"data": {"status": "completed", "result": {}}},
            raise_for_status=lambda: None,
        )
        result = client.get_status("activity-123")
        assert result["data"]["status"] == "completed"

    def test_wait_for_result_success(self, client):
        client.get_status = MagicMock(return_value={"data": {"status": "completed", "result": {"temp": 42}}})
        result = client.wait_for_result("act-123", timeout=10, poll_interval=0.1)
        assert result == {"temp": 42}

    def test_wait_for_result_succeeded(self, client):
        client.get_status = MagicMock(return_value={"data": {"status": "succeeded", "result": {"temp": 42}}})
        result = client.wait_for_result("act-123", timeout=10, poll_interval=0.1)
        assert result == {"temp": 42}

    def test_wait_for_result_failed(self, client):
        client.get_status = MagicMock(return_value={"data": {"status": "failed"}})
        with pytest.raises(RuntimeError, match="failed"):
            client.wait_for_result("act-123", timeout=10, poll_interval=0.1)

    def test_wait_for_result_timeout(self, client):
        client.get_status = MagicMock(return_value={"data": {"status": "pending"}})
        with pytest.raises(TimeoutError, match="timed out"):
            client.wait_for_result("act-123", timeout=0.1, poll_interval=0.05)
