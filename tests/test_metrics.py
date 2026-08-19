"""Tests for performance monitoring and analytics."""

from utils.metrics import MetricsCollector, get_metrics


class TestMetricsCollector:
    def test_record_api_call(self):
        mc = MetricsCollector()
        mc.record_api_call("env_params", 500.0, success=True)
        stats = mc.get_api_stats()
        assert stats["total"] == 1
        assert stats["avg_latency_ms"] == 500.0

    def test_record_api_call_failure(self):
        mc = MetricsCollector()
        mc.record_api_call("env_params", 500.0, success=False)
        stats = mc.get_api_stats()
        assert stats["success_rate"] == 0.0

    def test_record_agent_call(self):
        mc = MetricsCollector()
        mc.record_agent_call("quick_agent", 1200.0, query_length=50)
        stats = mc.get_agent_stats()
        assert stats["total"] == 1
        assert stats["avg_latency_ms"] == 1200.0

    def test_record_routing(self):
        mc = MetricsCollector()
        mc.record_routing("test query", "quick", 0.9)
        dashboard = mc.get_dashboard_data()
        assert "api" in dashboard
        assert "agents" in dashboard

    def test_record_cache_hit_miss(self):
        mc = MetricsCollector()
        mc.record_cache_hit()
        mc.record_cache_hit()
        mc.record_cache_miss()
        stats = mc.get_cache_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert abs(stats["hit_rate"] - 2 / 3) < 0.01

    def test_record_escalation(self):
        mc = MetricsCollector()
        mc.record_escalation("zone1", "critical")
        stats = mc.get_escalation_stats()
        assert stats["zone1:critical"] == 1

    def test_record_error(self):
        mc = MetricsCollector()
        mc.record_error("api", "timeout")
        stats = mc.get_error_stats()
        assert stats["total"] == 1
        assert stats["by_component"]["api"] == 1

    def test_record_alert_sent(self):
        mc = MetricsCollector()
        mc.record_alert_sent()
        mc.record_alert_sent()
        dashboard = mc.get_dashboard_data()
        assert dashboard["alerts_sent"] == 2

    def test_dashboard_data(self):
        mc = MetricsCollector()
        mc.record_api_call("env_params", 500.0, success=True)
        mc.record_agent_call("quick_agent", 1200.0, query_length=50)
        dashboard = mc.get_dashboard_data()
        assert "api" in dashboard
        assert "agents" in dashboard
        assert "cache" in dashboard
        assert "escalations" in dashboard
        assert "errors" in dashboard

    def test_get_metrics_returns_singleton(self):
        m1 = get_metrics()
        m2 = get_metrics()
        assert m1 is m2

    def test_empty_stats(self):
        mc = MetricsCollector()
        api_stats = mc.get_api_stats()
        assert api_stats["total"] == 0
        agent_stats = mc.get_agent_stats()
        assert agent_stats["total"] == 0
        cache_stats = mc.get_cache_stats()
        assert cache_stats["hits"] == 0
