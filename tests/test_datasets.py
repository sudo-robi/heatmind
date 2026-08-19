"""Tests for utils/datasets.py — public census and health data."""

from utils.datasets import (
    CDC_HEAT_VULNERABILITY,
    HEAT_RISK_FACTORS,
    US_CENSUS_TRACTS,
    LocationContext,
    _calculate_risk_score,
    _find_closest_tract,
    format_location_context,
    get_location_context,
)


class TestLocationContext:
    def test_defaults(self):
        ctx = LocationContext(latitude=33.0, longitude=-112.0)
        assert ctx.city == "Unknown"
        assert ctx.state == "Unknown"
        assert ctx.census_tract is None
        assert ctx.risk_score == 0.0
        assert ctx.risk_factors == []
        assert ctx.data_sources == []

    def test_to_dict(self):
        ctx = LocationContext(latitude=33.0, longitude=-112.0, city="Phoenix")
        d = ctx.to_dict()
        assert d["latitude"] == 33.0
        assert d["city"] == "Phoenix"
        assert "risk_factors" in d


class TestFindClosestTract:
    def test_exact_match(self):
        tract = _find_closest_tract(40.71, -74.01)
        assert tract is not None
        assert tract["tract"] == "36061000100"

    def test_near_match(self):
        tract = _find_closest_tract(40.72, -74.00)
        assert tract is not None

    def test_no_match_too_far(self):
        tract = _find_closest_tract(0.0, 0.0)
        assert tract is None

    def test_phoenix(self):
        tract = _find_closest_tract(33.45, -112.07)
        assert tract is not None
        assert tract["tract"] == "04013107600"


class TestCalculateRiskScore:
    def test_low_risk(self):
        ctx = LocationContext(
            latitude=0,
            longitude=0,
            elderly_pct=0.10,
            median_income=80000,
            population_density=5000,
        )
        score, factors = _calculate_risk_score(ctx)
        assert score == 0.0
        assert factors == []

    def test_high_risk(self):
        ctx = LocationContext(
            latitude=0,
            longitude=0,
            elderly_pct=0.20,
            median_income=30000,
            population_density=15000,
        )
        score, factors = _calculate_risk_score(ctx)
        assert score > 0.3
        assert len(factors) >= 2

    def test_partial_risk(self):
        ctx = LocationContext(
            latitude=0,
            longitude=0,
            elderly_pct=0.16,
            median_income=60000,
            population_density=5000,
        )
        score, factors = _calculate_risk_score(ctx)
        assert 0 < score <= 0.25
        assert len(factors) == 1

    def test_score_capped_at_1(self):
        ctx = LocationContext(
            latitude=0,
            longitude=0,
            elderly_pct=0.30,
            median_income=10000,
            population_density=50000,
        )
        score, _ = _calculate_risk_score(ctx)
        assert score <= 1.0


class TestGetLocationContext:
    def test_known_city(self):
        ctx = get_location_context(33.45, -112.07)
        assert ctx.census_tract == "04013107600"
        assert ctx.population_density is not None
        assert ctx.risk_score >= 0
        assert ctx.heat_vulnerability in ("low", "medium", "high")

    def test_unknown_location(self):
        ctx = get_location_context(0.0, 0.0)
        assert ctx.census_tract is None
        assert ctx.heat_vulnerability == "low"
        assert ctx.risk_score == 0.0

    def test_high_vulnerability(self):
        ctx = get_location_context(25.76, -80.19)
        assert ctx.heat_vulnerability in ("medium", "high")

    def test_data_sources_populated(self):
        ctx = get_location_context(40.71, -74.01)
        assert len(ctx.data_sources) >= 2


class TestFormatLocationContext:
    def test_known_location(self):
        ctx = get_location_context(33.45, -112.07)
        fmt = format_location_context(ctx)
        assert "33.4500" in fmt
        assert "Census Tract" in fmt
        assert "Risk Score" in fmt

    def test_unknown_location(self):
        ctx = LocationContext(latitude=0, longitude=0)
        fmt = format_location_context(ctx)
        assert "N/A" in fmt

    def test_with_risk_factors(self):
        ctx = get_location_context(33.45, -112.07)
        fmt = format_location_context(ctx)
        if ctx.risk_factors:
            assert "Risk Factors" in fmt


class TestDataIntegrity:
    def test_census_tracts_not_empty(self):
        assert len(US_CENSUS_TRACTS) == 10

    def test_risk_factors_sum_to_1(self):
        total = sum(f["weight"] for f in HEAT_RISK_FACTORS.values())
        assert abs(total - 1.0) < 0.01

    def test_heat_vulnerability_levels(self):
        assert "high" in CDC_HEAT_VULNERABILITY
        assert "medium" in CDC_HEAT_VULNERABILITY
        assert "low" in CDC_HEAT_VULNERABILITY
