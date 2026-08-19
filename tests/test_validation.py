"""Tests for utils/validation.py — coordinate validation and data flattening."""

import pytest

from utils.validation import flatten_location_data, validate_coords


class TestValidateCoords:
    def test_valid_coords(self):
        validate_coords(0, 0)

    def test_valid_north_pole(self):
        validate_coords(90, 0)

    def test_valid_south_pole(self):
        validate_coords(-90, 0)

    def test_valid_date_line(self):
        validate_coords(0, 180)

    def test_valid_antimeridian(self):
        validate_coords(0, -180)

    def test_invalid_latitude_too_high(self):
        with pytest.raises(ValueError, match="Invalid latitude"):
            validate_coords(91, 0)

    def test_invalid_latitude_too_low(self):
        with pytest.raises(ValueError, match="Invalid latitude"):
            validate_coords(-91, 0)

    def test_invalid_longitude_too_high(self):
        with pytest.raises(ValueError, match="Invalid longitude"):
            validate_coords(0, 181)

    def test_invalid_longitude_too_low(self):
        with pytest.raises(ValueError, match="Invalid longitude"):
            validate_coords(0, -181)

    def test_both_invalid(self):
        with pytest.raises(ValueError):
            validate_coords(100, 200)


class TestFlattenLocationData:
    def test_api_format(self):
        raw = {
            "locations": [
                {
                    "parameters": {
                        "heat_index_celsius": [39.9],
                        "relative_humidity_percent": [65],
                        "air_quality_idx": [42],
                    }
                }
            ]
        }
        flat = flatten_location_data(raw)
        assert flat["heat_index_celsius"] == 39.9
        assert flat["relative_humidity_percent"] == 65
        assert flat["air_quality_idx"] == 42

    def test_empty_locations(self):
        flat = flatten_location_data({"locations": []})
        assert flat == {"locations": []}

    def test_no_locations_key(self):
        flat = flatten_location_data({"key": "value"})
        assert flat == {"key": "value"}

    def test_empty_parameters(self):
        raw = {"locations": [{"parameters": {}}]}
        flat = flatten_location_data(raw)
        assert flat == {}

    def test_non_array_values(self):
        raw = {"locations": [{"parameters": {"temp": 35}}]}
        flat = flatten_location_data(raw)
        assert flat["temp"] == 35

    def test_mixed_array_and_scalar(self):
        raw = {"locations": [{"parameters": {"a": [1], "b": "x", "c": []}}]}
        flat = flatten_location_data(raw)
        assert flat["a"] == 1
        assert flat["b"] == "x"
        assert flat["c"] == []

    def test_nested_dict_not_flattened(self):
        raw = {"locations": [{"parameters": {"nested": {"key": "val"}}}]}
        flat = flatten_location_data(raw)
        assert flat["nested"] == {"key": "val"}

    def test_first_location_only(self):
        raw = {
            "locations": [
                {"parameters": {"temp": [35]}},
                {"parameters": {"temp": [40]}},
            ]
        }
        flat = flatten_location_data(raw)
        assert flat["temp"] == 35

    def test_empty_raw(self):
        flat = flatten_location_data({})
        assert flat == {}
