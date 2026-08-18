import os
import uuid
from datetime import UTC, datetime

import pytest

# Set test env vars BEFORE any project imports (config.py reads at import time)
os.environ.setdefault("MONGO_URI", "mongodb://localhost:27017")
os.environ.setdefault("MONGO_DB", "heatmind_test")
os.environ.setdefault("FORTYGUARD_API_KEY", "")
os.environ.setdefault("TEST_MODE", "true")
os.environ.setdefault("SMTP_USER", "")
os.environ.setdefault("SMTP_PASS", "")
os.environ.setdefault("ALERT_EMAIL_TO", "")
os.environ.setdefault("ALERT_WEBHOOK_URL", "")


@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    yield


@pytest.fixture
def sample_polygon():
    return {
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


@pytest.fixture
def sample_env_params():
    return {
        "heat_index": 42.5,
        "relative_humidity": 65,
        "aqi": 120,
        "solar_irradiance_ghi": 850,
    }


@pytest.fixture
def sample_heatmap_result():
    return {
        "stats_data": {
            "Temperature_stats": {
                "Minimum": 35.2,
                "Maximum": 48.7,
                "Mean": 41.3,
                "Standard_deviation": 3.2,
            }
        },
        "map_data": {"type": "FeatureCollection", "features": []},
    }


@pytest.fixture
def sample_alert_payload():
    return {
        "zone": "Dubai Downtown",
        "severity": "warning",
        "heat_index": 38.5,
        "timestamp": datetime.now(UTC).isoformat(),
        "recommendations": [
            "Monitor conditions closely",
            "Ensure water availability",
        ],
    }


@pytest.fixture
def valid_session_id():
    return str(uuid.uuid4())
