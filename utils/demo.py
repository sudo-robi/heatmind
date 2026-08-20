"""Synthetic FortyGuard payloads for offline/demo mode.

Used when no FORTYGUARD_API_KEY is set so the full LLM agent loop — planning,
tool execution, reflection, alerting — can be demoed and tested end to end
without network access. Values are labeled ``demo: true``.
"""

import random
from datetime import UTC, datetime


def _rng(lat: float, lng: float) -> random.Random:
    return random.Random(abs(int(lat * 1000)) + abs(int(lng * 1000)))


def demo_env_params(lat: float, lng: float) -> dict:
    rng = _rng(lat, lng)
    heat_index = round(rng.uniform(37.0, 51.0), 1)
    return {
        "heat_index_celsius": heat_index,
        "apparent_temperature_celsius": round(heat_index + rng.uniform(1.0, 3.5), 1),
        "relative_humidity_percent": round(rng.uniform(18, 58), 0),
        "air_quality:idx": round(rng.uniform(35, 170), 0),
        "demo": True,
    }


def demo_heatmap(lat: float, lng: float) -> dict:
    rng = _rng(lat, lng)
    mean = rng.uniform(34.0, 46.0)
    return {
        "stats_data": {
            "Temperature_stats": {
                "Minimum": round(mean - rng.uniform(3, 6), 1),
                "Maximum": round(mean + rng.uniform(3, 7), 1),
                "Mean": round(mean, 1),
            }
        },
        "demo": True,
    }


def demo_heat_intelligence(lat: float, lng: float) -> dict:
    rng = _rng(lat, lng)
    return {
        "analysis": {
            "risk_level": rng.choice(["moderate", "high", "extreme"]),
            "summary": "Multi-dimensional heat analysis based on environmental, geographic, and urban factors.",
        },
        "demo": True,
    }


def demo_satellite(lat: float, lng: float) -> dict:
    return {"segmentation": {"vegetation": 12.0, "bare_land": 40.0, "built_up": 48.0}, "demo": True}


def demo_streetview(lat: float, lng: float) -> dict:
    return {"segmentation": {"sky": 30.0, "ground": 45.0, "structure": 25.0}, "demo": True}


def demo_reading(lat: float, lng: float, zone: str) -> dict:
    """Full synthetic reading mirroring MonitorLoop.check_zone output."""
    return {
        "zone": zone,
        "timestamp": datetime.now(UTC).isoformat(),
        "heatmap": demo_heatmap(lat, lng),
        "env_params": demo_env_params(lat, lng),
        "demo": True,
    }
