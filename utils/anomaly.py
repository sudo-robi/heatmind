"""Anomaly detection with trend analysis (Winner 3: Kong AI Auto Rollback).

Goes beyond simple threshold comparison. Tracks historical readings per zone,
detects deviations from baseline, identifies trending temperatures, and
predicts when thresholds will be breached.
"""

import logging
import math
from collections import defaultdict
from datetime import UTC, datetime

logger = logging.getLogger(__name__)


class AnomalyDetector:
    def __init__(self, window_size: int = 10, z_score_threshold: float = 2.0):
        self.window_size = window_size
        self.z_score_threshold = z_score_threshold
        self._readings: dict[str, list[dict]] = defaultdict(list)

    def add_reading(self, zone: str, heat_index: float, timestamp: str | None = None):
        ts = timestamp or datetime.now(UTC).isoformat()
        self._readings[zone].append({"heat_index": heat_index, "timestamp": ts})
        if len(self._readings[zone]) > self.window_size * 3:
            self._readings[zone] = self._readings[zone][-self.window_size * 2 :]

    def get_baseline(self, zone: str) -> dict:
        readings = self._readings.get(zone, [])
        if len(readings) < 3:
            return {"mean": 0, "std": 0, "count": 0, "sufficient_data": False}

        values = [r["heat_index"] for r in readings[-self.window_size :]]
        mean = sum(values) / len(values)
        variance = sum((v - mean) ** 2 for v in values) / len(values)
        std = math.sqrt(variance)

        return {
            "mean": round(mean, 2),
            "std": round(std, 2),
            "count": len(values),
            "sufficient_data": len(values) >= 3,
        }

    def detect_anomaly(self, zone: str, current_value: float) -> dict:
        baseline = self.get_baseline(zone)

        if not baseline["sufficient_data"]:
            return {
                "is_anomaly": False,
                "reason": "insufficient_data",
                "baseline": baseline,
            }

        mean = baseline["mean"]
        std = baseline["std"]

        if std == 0:
            is_anomaly = abs(current_value - mean) > 5.0
            z_score = 0
        else:
            z_score = (current_value - mean) / std
            is_anomaly = abs(z_score) > self.z_score_threshold

        return {
            "is_anomaly": is_anomaly,
            "z_score": round(z_score, 2),
            "deviation": round(current_value - mean, 2),
            "baseline": baseline,
            "reason": "statistical_outlier" if is_anomaly else "within_normal_range",
        }

    def detect_trend(self, zone: str) -> dict:
        readings = self._readings.get(zone, [])
        recent = readings[-self.window_size :]

        if len(recent) < 3:
            return {"trend": "insufficient_data", "slope": 0, "direction": "stable"}

        values = [r["heat_index"] for r in recent]
        n = len(values)
        x_mean = (n - 1) / 2
        y_mean = sum(values) / n

        numerator = sum((i - x_mean) * (v - y_mean) for i, v in enumerate(values))
        denominator = sum((i - x_mean) ** 2 for i in range(n))

        slope = numerator / denominator if denominator != 0 else 0

        if slope > 0.5:
            direction = "rising"
        elif slope < -0.5:
            direction = "falling"
        else:
            direction = "stable"

        return {
            "trend": "trending" if abs(slope) > 0.3 else "stable",
            "slope": round(slope, 3),
            "direction": direction,
            "recent_values": [round(v, 1) for v in values],
        }

    def predict_breach(self, zone: str, threshold: float, minutes_ahead: int = 60) -> dict:
        trend = self.detect_trend(zone)
        baseline = self.get_baseline(zone)

        if not baseline["sufficient_data"] or trend["trend"] == "insufficient_data":
            return {
                "will_breach": False,
                "confidence": 0,
                "reason": "insufficient_data",
            }

        current = baseline["mean"]
        slope_per_check = trend["slope"]

        checks_ahead = minutes_ahead / 30
        predicted = current + slope_per_check * checks_ahead

        will_breach = predicted >= threshold
        confidence = min(abs(slope_per_check) * 0.5 + 0.3, 0.9) if will_breach else 0.5

        return {
            "will_breach": will_breach,
            "predicted_value": round(predicted, 1),
            "threshold": threshold,
            "confidence": round(confidence, 2),
            "minutes_ahead": minutes_ahead,
        }

    def get_zone_summary(self, zone: str) -> dict:
        baseline = self.get_baseline(zone)
        trend = self.detect_trend(zone)
        readings = self._readings.get(zone, [])

        return {
            "zone": zone,
            "baseline": baseline,
            "trend": trend,
            "total_readings": len(readings),
            "last_reading": readings[-1] if readings else None,
        }
