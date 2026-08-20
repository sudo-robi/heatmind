def validate_coords(lat: float, lon: float) -> None:
    if not (-90 <= lat <= 90):
        raise ValueError(f"Invalid latitude: {lat}")
    if not (-180 <= lon <= 180):
        raise ValueError(f"Invalid longitude: {lon}")


def flatten_location_data(raw: dict) -> dict:
    """Flatten nested API response format into a flat dict.

    The FortyGuard API returns parameters as arrays:
    {"locations": [{"parameters": {"heat_index_celsius": [39.9], ...}}]}

    This extracts the first value from each array to produce:
    {"heat_index_celsius": 39.9, ...}
    """
    locations = raw.get("locations", [])
    if locations:
        loc = locations[0]
        params = loc.get("parameters", {})
        flat = {}
        for key, val in params.items():
            if isinstance(val, list) and len(val) > 0:
                flat[key] = val[0]
            else:
                flat[key] = val
        return flat
    return raw


_ENV_KEYS = [
    "heat_index_celsius",
    "apparent_temperature_celsius",
    "relative_humidity_percent",
    "air_quality:idx",
]


def format_env_conditions(data: dict) -> list[str]:
    """Return formatted lines for environmental conditions from a flat env dict."""
    lines = ["**Environmental Conditions:**"]
    for key in _ENV_KEYS:
        if key in data and data[key] is not None:
            label = key.replace("_", " ").replace(":", " ").title()
            lines.append(f"  - {label}: {data[key]}")
    lines.append("")
    return lines


def format_heatmap_stats(data: dict) -> list[str]:
    """Return formatted lines for heatmap temperature statistics."""
    hm = data.get("heatmap") or data
    stats = (hm.get("stats_data") or {}).get("Temperature_stats") if isinstance(hm, dict) else None
    if not stats:
        return []
    lines = ["**Heatmap Statistics:**"]
    lines.append(f"  - Min: {stats.get('Minimum', 'N/A')}\u00b0C")
    lines.append(f"  - Max: {stats.get('Maximum', 'N/A')}\u00b0C")
    lines.append(f"  - Mean: {stats.get('Mean', 'N/A')}\u00b0C")
    lines.append("")
    return lines
