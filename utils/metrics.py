"""Performance monitoring and metrics (Winner 4: Customer Support Agent).

Tracks API call latency, agent response times, routing accuracy,
cache hit rates, and escalation counts. Feeds the analytics dashboard.
"""

import logging
import threading
import time
from collections import defaultdict, deque

logger = logging.getLogger(__name__)


class MetricsCollector:
    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self._lock = threading.Lock()

        self._api_calls: deque = deque(maxlen=max_samples)
        self._agent_calls: deque = deque(maxlen=max_samples)
        self._routing_decisions: deque = deque(maxlen=max_samples)
        self._cache_hits = 0
        self._cache_misses = 0
        self._escalations: dict[str, int] = defaultdict(int)
        self._errors: deque = deque(maxlen=max_samples)
        self._alerts_sent = 0

    def record_api_call(self, endpoint: str, latency_ms: float, success: bool):
        with self._lock:
            self._api_calls.append(
                {
                    "endpoint": endpoint,
                    "latency_ms": round(latency_ms, 1),
                    "success": success,
                    "timestamp": time.time(),
                }
            )

    def record_agent_call(self, agent: str, latency_ms: float, query_length: int):
        with self._lock:
            self._agent_calls.append(
                {
                    "agent": agent,
                    "latency_ms": round(latency_ms, 1),
                    "query_length": query_length,
                    "timestamp": time.time(),
                }
            )

    def record_routing(self, query: str, agent: str, confidence: float):
        with self._lock:
            self._routing_decisions.append(
                {
                    "query_preview": query[:50],
                    "agent": agent,
                    "confidence": confidence,
                    "timestamp": time.time(),
                }
            )

    def record_cache_hit(self):
        with self._lock:
            self._cache_hits += 1

    def record_cache_miss(self):
        with self._lock:
            self._cache_misses += 1

    def record_escalation(self, zone: str, level: str):
        with self._lock:
            self._escalations[f"{zone}:{level}"] += 1

    def record_error(self, component: str, error: str):
        with self._lock:
            self._errors.append(
                {
                    "component": component,
                    "error": error,
                    "timestamp": time.time(),
                }
            )

    def record_alert_sent(self):
        with self._lock:
            self._alerts_sent += 1

    def get_api_stats(self) -> dict:
        with self._lock:
            calls = list(self._api_calls)
        if not calls:
            return {"total": 0, "avg_latency_ms": 0, "success_rate": 1.0}

        latencies = [c["latency_ms"] for c in calls]
        successes = sum(1 for c in calls if c["success"])

        by_endpoint = defaultdict(list)
        for c in calls:
            by_endpoint[c["endpoint"]].append(c["latency_ms"])

        return {
            "total": len(calls),
            "avg_latency_ms": round(sum(latencies) / len(latencies), 1),
            "p95_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 1)
            if len(latencies) > 1
            else round(latencies[0], 1),
            "success_rate": round(successes / len(calls), 3),
            "by_endpoint": {
                ep: {
                    "count": len(lats),
                    "avg_ms": round(sum(lats) / len(lats), 1),
                }
                for ep, lats in by_endpoint.items()
            },
        }

    def get_agent_stats(self) -> dict:
        with self._lock:
            calls = list(self._agent_calls)
        if not calls:
            return {"total": 0, "avg_latency_ms": 0}

        by_agent = defaultdict(list)
        for c in calls:
            by_agent[c["agent"]].append(c["latency_ms"])

        return {
            "total": len(calls),
            "avg_latency_ms": round(sum(c["latency_ms"] for c in calls) / len(calls), 1),
            "by_agent": {
                agent: {
                    "count": len(lats),
                    "avg_ms": round(sum(lats) / len(lats), 1),
                }
                for agent, lats in by_agent.items()
            },
        }

    def get_cache_stats(self) -> dict:
        with self._lock:
            total = self._cache_hits + self._cache_misses
            return {
                "hits": self._cache_hits,
                "misses": self._cache_misses,
                "hit_rate": round(self._cache_hits / total, 3) if total > 0 else 0,
            }

    def get_escalation_stats(self) -> dict:
        with self._lock:
            return dict(self._escalations)

    def get_error_stats(self) -> dict:
        with self._lock:
            errors = list(self._errors)
        by_component = defaultdict(int)
        for e in errors:
            by_component[e["component"]] += 1
        return {"total": len(errors), "by_component": dict(by_component)}

    def get_dashboard_data(self) -> dict:
        return {
            "api": self.get_api_stats(),
            "agents": self.get_agent_stats(),
            "cache": self.get_cache_stats(),
            "escalations": self.get_escalation_stats(),
            "errors": self.get_error_stats(),
            "alerts_sent": self._alerts_sent,
        }


_metrics = MetricsCollector()


def get_metrics() -> MetricsCollector:
    return _metrics
