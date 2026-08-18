import re
from dataclasses import dataclass, field
from datetime import UTC, datetime

US_CITIES = {
    "new york": {"lat": 40.7128, "lon": -74.0060},
    "nyc": {"lat": 40.7128, "lon": -74.0060},
    "manhattan": {"lat": 40.7831, "lon": -73.9712},
    "los angeles": {"lat": 34.0522, "lon": -118.2437},
    "la": {"lat": 34.0522, "lon": -118.2437},
    "chicago": {"lat": 41.8781, "lon": -87.6298},
    "houston": {"lat": 29.7604, "lon": -95.3698},
    "phoenix": {"lat": 33.4484, "lon": -112.0740},
    "philadelphia": {"lat": 39.9526, "lon": -75.1652},
    "san antonio": {"lat": 29.4241, "lon": -98.4936},
    "san diego": {"lat": 32.7157, "lon": -117.1611},
    "dallas": {"lat": 32.7767, "lon": -96.7970},
    "austin": {"lat": 30.2672, "lon": -97.7431},
    "miami": {"lat": 25.7617, "lon": -80.1918},
    "seattle": {"lat": 47.6062, "lon": -122.3321},
    "denver": {"lat": 39.7392, "lon": -104.9903},
    "boston": {"lat": 42.3601, "lon": -71.0589},
    "washington dc": {"lat": 38.9072, "lon": -77.0369},
    "washington": {"lat": 38.9072, "lon": -77.0369},
    "dc": {"lat": 38.9072, "lon": -77.0369},
    "atlanta": {"lat": 33.7490, "lon": -84.3880},
    "detroit": {"lat": 42.3314, "lon": -83.0458},
    "minneapolis": {"lat": 44.9778, "lon": -93.2650},
    "portland": {"lat": 45.5152, "lon": -122.6784},
    "las vegas": {"lat": 36.1699, "lon": -115.1398},
    "vegas": {"lat": 36.1699, "lon": -115.1398},
    "nashville": {"lat": 36.1627, "lon": -86.7816},
    "charlotte": {"lat": 35.2271, "lon": -80.8431},
    "jacksonville": {"lat": 30.3322, "lon": -81.6557},
    "san francisco": {"lat": 37.7749, "lon": -122.4194},
    "sf": {"lat": 37.7749, "lon": -122.4194},
}

INTENT_PATTERNS = {
    "current_conditions": [
        r"what.{0,10}temperature",
        r"how.{0,10}hot",
        r"current.{0,10}heat",
        r"right now",
        r"today.{0,10}temperature",
        r"temperature.{0,10}now",
        r"heat index",
    ],
    "forecast": [
        r"forecast",
        r"tomorrow",
        r"next.{0,10}(day|week|hour)",
        r"will.{0,10}be",
    ],
    "comparison": [
        r"compare",
        r"difference between",
        r"versus|vs\.?",
        r"which.{0,10}(hotter|cooler|warmer)",
    ],
    "risk_assessment": [
        r"risk",
        r"danger",
        r"safe",
        r"unsafe",
        r"hazard",
        r"assessment",
        r"evaluate",
    ],
    "emergency": [
        r"emergency",
        r"critical",
        r"extreme",
        r"immediate",
        r"dangerous",
        r"crisis",
        r"help.{0,10}now",
    ],
    "monitoring": [
        r"monitor",
        r"watch",
        r"track",
        r"alert",
        r"notify",
        r"notify.{0,10}when",
    ],
    "analysis": [
        r"analyze",
        r"analysis",
        r"deep.{0,5}dive",
        r"comprehensive",
        r"full.{0,5}report",
        r"intelligence",
        r"detailed",
    ],
    "environmental": [
        r"air.{0,5}quality",
        r"aqi",
        r"humidity",
        r"solar",
        r"irradiance",
        r"environmental",
    ],
}


@dataclass
class ParsedQuery:
    intent: str = "current_conditions"
    location: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    date: str | None = None
    time: str | None = None
    filter_type: int = 1
    endpoints_needed: list = field(default_factory=list)
    confidence: float = 0.5
    raw_query: str = ""
    entities_found: list = field(default_factory=list)


def extract_location(query: str) -> tuple[str | None, float | None, float | None]:
    query_lower = query.lower()
    for city, coords in sorted(US_CITIES.items(), key=lambda x: -len(x[0])):
        if city in query_lower:
            return city, coords["lat"], coords["lon"]
    lat_match = re.search(r'latitude[:\s]+(-?\d+\.?\d*)', query_lower)
    lon_match = re.search(r'longitude[:\s]+(-?\d+\.?\d*)', query_lower)
    if lat_match and lon_match:
        return "custom", float(lat_match.group(1)), float(lon_match.group(1))
    coord_match = re.search(r'\((-?\d+\.?\d*)\s*,\s*(-?\d+\.?\d*)\)', query)
    if coord_match:
        return "custom", float(coord_match.group(1)), float(coord_match.group(2))
    return None, None, None


def extract_date(query: str) -> str | None:
    query_lower = query.lower()
    today = datetime.now(UTC)
    if "today" in query_lower:
        return today.strftime("%Y-%m-%d")
    if "tomorrow" in query_lower:
        from datetime import timedelta
        return (today + timedelta(days=1)).strftime("%Y-%m-%d")
    if "yesterday" in query_lower:
        from datetime import timedelta
        return (today - timedelta(days=1)).strftime("%Y-%m-%d")
    date_match = re.search(r'(\d{4}-\d{2}-\d{2})', query)
    if date_match:
        return date_match.group(1)
    date_match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{2,4})', query)
    if date_match:
        month, day, year = date_match.groups()
        if len(year) == 2:
            year = "20" + year
        return f"{year}-{month.zfill(2)}-{day.zfill(2)}"
    return today.strftime("%Y-%m-%d")


def extract_time(query: str) -> str | None:
    query_lower = query.lower()
    time_match = re.search(r'(\d{1,2}):(\d{2})\s*(am|pm)?', query_lower)
    if time_match:
        hour = int(time_match.group(1))
        minute = time_match.group(2)
        ampm = time_match.group(3)
        if ampm == "pm" and hour < 12:
            hour += 12
        elif ampm == "am" and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute}"
    if "morning" in query_lower:
        return "08:00"
    if "afternoon" in query_lower:
        return "14:00"
    if "evening" in query_lower:
        return "18:00"
    if "night" in query_lower:
        return "21:00"
    return None


def classify_intent(query: str) -> tuple[str, float]:
    query_lower = query.lower()
    scores = {}
    for intent, patterns in INTENT_PATTERNS.items():
        score = 0
        for pattern in patterns:
            if re.search(pattern, query_lower):
                score += 1
        if score > 0:
            scores[intent] = score
    if not scores:
        return "current_conditions", 0.5
    best_intent = max(scores, key=scores.get)
    confidence = min(0.5 + scores[best_intent] * 0.15, 0.95)
    return best_intent, confidence


def get_endpoints_for_intent(intent: str) -> list[str]:
    endpoint_map = {
        "current_conditions": ["env_params"],
        "forecast": ["heatmap"],
        "comparison": ["env_params", "heatmap"],
        "risk_assessment": ["env_params", "heatmap", "heat_intelligence"],
        "emergency": ["env_params"],
        "monitoring": ["env_params", "heatmap"],
        "analysis": ["env_params", "heatmap", "heat_intelligence"],
        "environmental": ["env_params"],
    }
    return endpoint_map.get(intent, ["env_params"])


def parse_query(query: str) -> ParsedQuery:
    intent, confidence = classify_intent(query)
    location, lat, lon = extract_location(query)
    date = extract_date(query)
    time = extract_time(query)
    endpoints = get_endpoints_for_intent(intent)

    entities = []
    if location:
        entities.append(f"location:{location}")
    if date:
        entities.append(f"date:{date}")
    if time:
        entities.append(f"time:{time}")
    entities.append(f"intent:{intent}")

    filter_type = 1
    if time:
        filter_type = 1
    elif "week" in query.lower():
        filter_type = 4
    elif "month" in query.lower():
        filter_type = 5
    elif "today" in query.lower() and not time:
        filter_type = 3

    return ParsedQuery(
        intent=intent,
        location=location,
        latitude=lat,
        longitude=lon,
        date=date,
        time=time,
        filter_type=filter_type,
        endpoints_needed=endpoints,
        confidence=confidence,
        raw_query=query,
        entities_found=entities,
    )
