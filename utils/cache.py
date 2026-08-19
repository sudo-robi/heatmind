"""Response caching with TTL and content-hash keys (Winner 4: Customer Support Agent).

Avoids redundant API calls for repeated queries. Uses SHA-256 content hashes
as cache keys so the same query parameters always hit the cache.
"""

import hashlib
import json
import logging
import threading
import time

logger = logging.getLogger(__name__)


class ResponseCache:
    def __init__(self, default_ttl: float = 300.0, max_size: int = 500):
        self.default_ttl = default_ttl
        self.max_size = max_size
        self._cache: dict[str, dict] = {}
        self._lock = threading.Lock()

    def _make_key(self, endpoint: str, payload: dict) -> str:
        raw = json.dumps({"endpoint": endpoint, "payload": payload}, sort_keys=True)
        return hashlib.sha256(raw.encode()).hexdigest()[:32]

    def get(self, endpoint: str, payload: dict) -> dict | None:
        key = self._make_key(endpoint, payload)
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return None
            if time.time() - entry["stored_at"] > entry["ttl"]:
                del self._cache[key]
                return None
            entry["hits"] += 1
            return entry["value"]

    def set(self, endpoint: str, payload: dict, value: dict, ttl: float | None = None):
        key = self._make_key(endpoint, payload)
        with self._lock:
            if len(self._cache) >= self.max_size:
                oldest_key = min(self._cache, key=lambda k: self._cache[k]["stored_at"])
                del self._cache[oldest_key]
            self._cache[key] = {
                "value": value,
                "stored_at": time.time(),
                "ttl": ttl or self.default_ttl,
                "hits": 0,
            }

    def invalidate(self, endpoint: str | None = None):
        with self._lock:
            if endpoint:
                self._cache = {k: v for k, v in self._cache.items() if endpoint not in k}
            else:
                self._cache.clear()

    def get_stats(self) -> dict:
        with self._lock:
            total_hits = sum(e["hits"] for e in self._cache.values())
            return {
                "size": len(self._cache),
                "max_size": self.max_size,
                "total_hits": total_hits,
            }


_response_cache = ResponseCache()


def cached_api_call(client, method_name: str, *args, **kwargs) -> dict | None:
    """Call an API method with caching. Returns cached result if available."""
    endpoint = method_name
    payload = {"args": args, "kwargs": kwargs}

    cached = _response_cache.get(endpoint, payload)
    if cached is not None:
        logger.debug("Cache hit for %s", endpoint)
        return cached

    method = getattr(client, method_name, None)
    if method is None:
        return None

    result = method(*args, **kwargs)
    if result is not None:
        _response_cache.set(endpoint, payload, result, ttl=600)
    return result
