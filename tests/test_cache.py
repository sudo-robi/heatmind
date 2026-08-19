"""Tests for response caching."""

import time

from utils.cache import ResponseCache, cached_api_call


class TestResponseCache:
    def test_set_and_get(self):
        cache = ResponseCache(default_ttl=60)
        cache.set("env_params", {"lat": 40, "lon": -74}, {"temp": 85})
        result = cache.get("env_params", {"lat": 40, "lon": -74})
        assert result == {"temp": 85}

    def test_get_nonexistent_returns_none(self):
        cache = ResponseCache(default_ttl=60)
        assert cache.get("missing", {}) is None

    def test_ttl_expiration(self):
        cache = ResponseCache(default_ttl=0.1)
        cache.set("env_params", {"lat": 40}, {"temp": 85})
        time.sleep(0.15)
        assert cache.get("env_params", {"lat": 40}) is None

    def test_custom_ttl(self):
        cache = ResponseCache(default_ttl=60)
        cache.set("env_params", {"lat": 40}, {"temp": 85}, ttl=0.1)
        time.sleep(0.15)
        assert cache.get("env_params", {"lat": 40}) is None

    def test_invalidate_all(self):
        cache = ResponseCache(default_ttl=60)
        cache.set("env_params", {"lat": 40}, {"temp": 85})
        cache.set("heatmap", {"lat": 40}, {"data": []})
        cache.invalidate()
        assert cache.get("env_params", {"lat": 40}) is None
        assert cache.get("heatmap", {"lat": 40}) is None

    def test_get_stats(self):
        cache = ResponseCache(default_ttl=60)
        cache.set("env_params", {"lat": 40}, {"temp": 85})
        cache.get("env_params", {"lat": 40})
        stats = cache.get_stats()
        assert stats["size"] == 1
        assert stats["total_hits"] == 1

    def test_max_size_eviction(self):
        cache = ResponseCache(default_ttl=60, max_size=2)
        cache.set("env_params", {"a": 1}, {"temp": 85})
        cache.set("env_params", {"a": 2}, {"temp": 86})
        cache.set("env_params", {"a": 3}, {"temp": 87})
        stats = cache.get_stats()
        assert stats["size"] == 2

    def test_same_payload_same_key(self):
        cache = ResponseCache(default_ttl=60)
        cache.set("env_params", {"lat": 40, "lon": -74}, {"temp": 85})
        result = cache.get("env_params", {"lon": -74, "lat": 40})
        assert result == {"temp": 85}


class TestCachedApiCall:
    def test_caches_result(self):
        call_count = 0

        class FakeClient:
            def env_params(self, **kwargs):
                nonlocal call_count
                call_count += 1
                return {"temp": 85}

        client = FakeClient()
        result1 = cached_api_call(client, "env_params", lat=40, lon=-74)
        result2 = cached_api_call(client, "env_params", lat=40, lon=-74)
        assert result1 == result2
        assert call_count == 1

    def test_different_args_different_cache(self):
        call_count = 0

        class FakeClient:
            def env_params(self, **kwargs):
                nonlocal call_count
                call_count += 1
                return {"temp": kwargs.get("lat", 0)}

        client = FakeClient()
        cached_api_call(client, "env_params", lat=40)
        cached_api_call(client, "env_params", lat=50)
        assert call_count == 2
