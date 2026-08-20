"""Tests for map rendering helpers (utils/maps.py)."""

from utils.maps import extract_geojson, heat_color, render_heat_map, render_zones_map


class TestHeatColor:
    def test_cool_below_scale(self):
        assert heat_color(5.0) == [53, 151, 217]

    def test_hot_above_scale(self):
        assert heat_color(60.0) == [140, 20, 60]

    def test_mid_range_interpolates(self):
        assert heat_color(33.0) == [250, 200, 50]

    def test_none_returns_grey(self):
        assert heat_color(None) == [90, 90, 90]


class TestExtractGeojson:
    def test_map_data_key(self):
        geojson = {"type": "FeatureCollection", "features": []}
        assert extract_geojson({"map_data": geojson}) == geojson

    def test_geojson_key(self):
        geojson = {"type": "FeatureCollection", "features": []}
        assert extract_geojson({"geojson": geojson}) == geojson

    def test_none_result(self):
        assert extract_geojson(None) is None

    def test_not_geojson(self):
        assert extract_geojson({"map_data": {"type": "Point"}}) is None


class TestRenderHeatMap:
    def test_returns_deck(self):
        deck = render_heat_map(25.2, 55.3, "Dubai", heat_index=46.0)
        assert deck is not None
        assert hasattr(deck, "to_json")

    def test_returns_deck_with_geojson(self):
        geojson = {"type": "FeatureCollection", "features": []}
        deck = render_heat_map(25.2, 55.3, "Dubai", heatmap_result={"map_data": geojson}, heat_index=40.0)
        assert deck is not None


class TestRenderZonesMap:
    def test_returns_deck(self):
        zones = [{"name": "Dubai", "lat": 25.2, "lng": 55.3, "heat_index": 46.0}]
        deck = render_zones_map(zones)
        assert deck is not None

    def test_empty_zones_returns_none(self):
        assert render_zones_map([]) is None

    def test_lat_lng_key_styles(self):
        zones = [{"name": "Dubai", "latitude": 25.2, "longitude": 55.3, "heat_index": 46.0}]
        deck = render_zones_map(zones)
        assert deck is not None

    def test_invalid_zone_skipped(self):
        zones = [{"name": "Missing coords"}]
        assert render_zones_map(zones) is None
