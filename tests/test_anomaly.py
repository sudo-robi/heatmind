"""Tests for anomaly detection."""

from utils.anomaly import AnomalyDetector


class TestAnomalyDetector:
    def test_add_reading(self):
        ad = AnomalyDetector()
        ad.add_reading("zone1", 95.0)
        summary = ad.get_zone_summary("zone1")
        assert summary["total_readings"] == 1

    def test_detect_anomaly_high(self):
        ad = AnomalyDetector(window_size=5, z_score_threshold=2.0)
        for _ in range(5):
            ad.add_reading("zone1", 80.0)
        result = ad.detect_anomaly("zone1", 120.0)
        assert result["is_anomaly"] is True

    def test_detect_anomaly_low(self):
        ad = AnomalyDetector(window_size=5, z_score_threshold=2.0)
        for _ in range(5):
            ad.add_reading("zone1", 100.0)
        result = ad.detect_anomaly("zone1", 50.0)
        assert result["is_anomaly"] is True

    def test_no_anomaly_normal(self):
        ad = AnomalyDetector(window_size=5, z_score_threshold=2.0)
        for _ in range(5):
            ad.add_reading("zone1", 85.0)
        result = ad.detect_anomaly("zone1", 86.0)
        assert result["is_anomaly"] is False

    def test_trend_direction_rising(self):
        ad = AnomalyDetector(window_size=5)
        for i in range(5):
            ad.add_reading("zone1", 80.0 + i * 2)
        result = ad.detect_trend("zone1")
        assert result["direction"] == "rising"

    def test_trend_direction_falling(self):
        ad = AnomalyDetector(window_size=5)
        for i in range(5):
            ad.add_reading("zone1", 100.0 - i * 2)
        result = ad.detect_trend("zone1")
        assert result["direction"] == "falling"

    def test_trend_direction_stable(self):
        ad = AnomalyDetector(window_size=5)
        for _ in range(5):
            ad.add_reading("zone1", 85.0)
        result = ad.detect_trend("zone1")
        assert result["direction"] == "stable"

    def test_predict_breach(self):
        ad = AnomalyDetector(window_size=5)
        for i in range(5):
            ad.add_reading("zone1", 80.0 + i * 5)
        result = ad.predict_breach("zone1", threshold=110.0, minutes_ahead=60)
        assert "will_breach" in result

    def test_get_zone_summary(self):
        ad = AnomalyDetector()
        ad.add_reading("zone1", 85.0)
        ad.add_reading("zone1", 90.0)
        summary = ad.get_zone_summary("zone1")
        assert summary["zone"] == "zone1"
        assert summary["total_readings"] == 2

    def test_insufficient_data(self):
        ad = AnomalyDetector(window_size=5)
        ad.add_reading("zone1", 85.0)
        result = ad.detect_anomaly("zone1", 120.0)
        assert result["is_anomaly"] is False
        assert result["reason"] == "insufficient_data"

    def test_get_baseline(self):
        ad = AnomalyDetector(window_size=5)
        for _ in range(5):
            ad.add_reading("zone1", 85.0)
        baseline = ad.get_baseline("zone1")
        assert baseline["mean"] == 85.0
        assert baseline["sufficient_data"] is True
