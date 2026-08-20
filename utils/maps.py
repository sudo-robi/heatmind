"""Map rendering helpers for HeatMind.

Turn FortyGuard heatmap results and zone state into pydeck layers so the
Streamlit app can show live thermal intelligence. pydeck is imported lazily —
everything degrades gracefully to ``None`` when it is unavailable, keeping the
app runnable on a minimal install.
"""

import logging

logger = logging.getLogger(__name__)

HEAT_COLOR_STOPS = [
    (15.0, (53, 151, 217)),  # cool blue
    (25.0, (64, 196, 108)),  # green
    (33.0, (250, 200, 50)),  # amber
    (38.0, (240, 130, 40)),  # orange
    (42.0, (220, 60, 45)),  # red
    (47.0, (140, 20, 60)),  # deep red
]


def heat_color(temp: float) -> list:
    """Return [r, g, b] for a temperature using the HEAT_COLOR_STOPS scale."""
    if temp is None:
        return [90, 90, 90]
    for i, (threshold, color) in enumerate(HEAT_COLOR_STOPS):
        if temp <= threshold:
            if i == 0:
                return list(color)
            prev_t, prev_c = HEAT_COLOR_STOPS[i - 1]
            t = (temp - prev_t) / max(threshold - prev_t, 1e-6)
            return [int(prev_c[j] + (color[j] - prev_c[j]) * t) for j in range(3)]
    return list(HEAT_COLOR_STOPS[-1][1])


def extract_geojson(heatmap_result) -> dict | None:
    """Pull the GeoJSON FeatureCollection out of a heatmap result if present."""
    if not isinstance(heatmap_result, dict):
        return None
    geojson = heatmap_result.get("map_data") or heatmap_result.get("geojson")
    if isinstance(geojson, dict) and geojson.get("type") == "FeatureCollection":
        return geojson
    return None


def render_heat_map(lat: float, lng: float, zone: str, heatmap_result=None, heat_index: float | None = None):
    """Render an interactive heat map centered on a location.

    Returns a pydeck Deck, or None if pydeck is not installed.
    """
    try:
        import pydeck as pdk
    except ImportError:
        logger.debug("pydeck not installed; skipping heat map")
        return None

    layers = []

    geojson = extract_geojson(heatmap_result)
    if geojson is not None:
        layers.append(
            pdk.Layer(
                "GeoJsonLayer",
                geojson,
                get_fill_color="[255, 120, 40, 140]",
                get_line_color=[255, 255, 255, 120],
                line_width_min_pixels=1,
                opacity=0.35,
            )
        )

    if heat_index is not None:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=[
                    {
                        "position": [lng, lat],
                        "radius": 1400,
                        "color": heat_color(heat_index),
                        "heat_index": heat_index,
                    }
                ],
                get_position="position",
                get_radius="radius",
                get_fill_color="color",
                get_line_color=[255, 255, 255, 160],
                line_width_min_pixels=2,
                pickable=True,
            )
        )
    else:
        layers.append(
            pdk.Layer(
                "ScatterplotLayer",
                data=[{"position": [lng, lat], "radius": 900, "color": heat_color(33)}],
                get_position="position",
                get_radius="radius",
                get_fill_color="color",
                get_line_color=[255, 255, 255, 160],
                line_width_min_pixels=2,
            )
        )

    layers.append(
        pdk.Layer(
            "TextLayer",
            data=[{"position": [lng, lat], "text": zone, "size": 16}],
            get_position="position",
            get_text="text",
            get_size="size",
            get_color=[255, 255, 255, 220],
        )
    )

    return pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(latitude=lat, longitude=lng, zoom=11, pitch=45, bearing=-20),
        tooltip={"text": "{heat_index}°C"},
        map_style="dark",
    )


def render_zones_map(zones: list):
    """Render all monitored zones as a heat-risk map.

    Returns a pydeck Deck, or None if pydeck is not installed.
    """
    try:
        import pydeck as pdk
    except ImportError:
        logger.debug("pydeck not installed; skipping zones map")
        return None

    if not zones:
        return None

    points = []
    for z in zones:
        lat = z.get("latitude") if z.get("latitude") is not None else z.get("lat")
        lng = z.get("longitude") if z.get("longitude") is not None else z.get("lng")
        heat = z.get("last_heat_index", z.get("heat_index"))
        if lat is None or lng is None:
            continue
        points.append(
            {
                "position": [lng, lat],
                "radius": 700,
                "color": heat_color(heat if heat is not None else 33),
                "name": z["name"],
                "heat_index": heat if heat is not None else "n/a",
            }
        )

    layers = [
        pdk.Layer(
            "ScatterplotLayer",
            data=points,
            get_position="position",
            get_radius="radius",
            get_fill_color="color",
            get_line_color=[255, 255, 255, 160],
            line_width_min_pixels=2,
            pickable=True,
        ),
        pdk.Layer(
            "TextLayer",
            data=points,
            get_position="position",
            get_text="name",
            get_size=13,
            get_color=[255, 255, 255, 220],
        ),
    ]

    if not points:
        return None

    mid_lat = sum(p["position"][1] for p in points) / len(points)
    mid_lng = sum(p["position"][0] for p in points) / len(points)
    return pdk.Deck(
        layers=layers,
        initial_view_state=pdk.ViewState(latitude=mid_lat, longitude=mid_lng, zoom=9, pitch=35),
        tooltip={"text": "{name} — {heat_index}°C"},
        map_style="dark",
    )
