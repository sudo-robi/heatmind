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
