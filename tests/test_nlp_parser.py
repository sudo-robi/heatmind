"""Tests for NLP Parser — location extraction, date/time parsing, intent classification."""

import pytest

from agents.nlp_parser import (
    ParsedQuery,
    classify_intent,
    extract_date,
    extract_location,
    extract_time,
    get_endpoints_for_intent,
    parse_query,
)


class TestExtractLocation:
    def test_known_city_new_york(self):
        name, lat, lon = extract_location("What's the temperature in New York?")
        assert name == "new york"
        assert lat == pytest.approx(40.7128, abs=0.01)
        assert lon == pytest.approx(-74.006, abs=0.01)

    def test_known_city_la(self):
        name, lat, lon = extract_location("How hot is LA right now?")
        assert name == "la"
        assert lat == pytest.approx(34.0522, abs=0.01)

    def test_city_case_insensitive(self):
        name, lat, lon = extract_location("Check PHOENIX temperature")
        assert name == "phoenix"

    def test_city_longest_match_first(self):
        name, lat, lon = extract_location("San Francisco weather")
        assert name == "san francisco"
        assert lat == pytest.approx(37.7749, abs=0.01)

    def test_explicit_latitude_longitude(self):
        name, lat, lon = extract_location("temperature at latitude 40.7 and longitude -74.0")
        assert name == "custom"
        assert lat == 40.7
        assert lon == -74.0

    def test_parenthetical_coords(self):
        name, lat, lon = extract_location("heat at (33.45, -112.07)")
        assert name == "custom"
        assert lat == 33.45
        assert lon == -112.07

    def test_no_location(self):
        name, lat, lon = extract_location("what is the temperature")
        assert name is None
        assert lat is None
        assert lon is None

    def test_dc_shorthand(self):
        name, lat, lon = extract_location("temperature in DC")
        assert name == "dc"


class TestExtractDate:
    def test_today(self):
        result = extract_date("temperature today")
        assert result is not None
        assert len(result) == 10  # YYYY-MM-DD

    def test_tomorrow(self):
        result = extract_date("forecast for tomorrow")
        assert result is not None

    def test_yesterday(self):
        result = extract_date("what was it yesterday")
        assert result is not None

    def test_explicit_date(self):
        result = extract_date("temperature on 2026-08-15")
        assert result == "2026-08-15"

    def test_us_format(self):
        result = extract_date("temperature on 8/15/2026")
        assert result == "2026-08-15"

    def test_two_digit_year(self):
        result = extract_date("temperature on 8/15/26")
        assert result == "2026-08-15"

    def test_no_date_defaults_to_today(self):
        result = extract_date("what is the temperature")
        assert result is not None

    def test_slash_separator(self):
        result = extract_date("03-15-2026 heat")
        assert result == "2026-03-15"


class TestExtractTime:
    def test_12h_format(self):
        result = extract_time("temperature at 3:30 pm")
        assert result == "15:30"

    def test_24h_format(self):
        result = extract_time("heat at 14:00")
        assert result == "14:00"

    def test_morning(self):
        result = extract_time("temperature this morning")
        assert result == "08:00"

    def test_afternoon(self):
        result = extract_time("heat in the afternoon")
        assert result == "14:00"

    def test_evening(self):
        result = extract_time("evening temperature")
        assert result == "18:00"

    def test_night(self):
        result = extract_time("night temperature")
        assert result == "21:00"

    def test_no_time(self):
        result = extract_time("what is the temperature")
        assert result is None

    def test_12am(self):
        result = extract_time("12:00 am")
        assert result == "00:00"


class TestClassifyIntent:
    def test_current_conditions(self):
        intent, conf = classify_intent("what is the temperature right now")
        assert intent == "current_conditions"
        assert conf > 0.5

    def test_forecast(self):
        intent, conf = classify_intent("what will the forecast be tomorrow")
        assert intent == "forecast"

    def test_emergency(self):
        intent, conf = classify_intent("emergency extreme heat")
        assert intent == "emergency"
        assert conf >= 0.8

    def test_comparison(self):
        intent, conf = classify_intent("compare temperature between NYC and LA")
        assert intent == "comparison"

    def test_analysis(self):
        intent, conf = classify_intent("comprehensive analysis of heat conditions")
        assert intent == "analysis"

    def test_risk_assessment(self):
        intent, conf = classify_intent("is it safe to go outside")
        assert intent == "risk_assessment"

    def test_monitoring(self):
        intent, conf = classify_intent("monitor temperature and alert me")
        assert intent == "monitoring"

    def test_environmental(self):
        intent, conf = classify_intent("what is the air quality and humidity")
        assert intent == "environmental"

    def test_unknown_defaults_current(self):
        intent, conf = classify_intent("hello")
        assert intent == "current_conditions"
        assert conf == 0.5


class TestGetEndpointsForIntent:
    def test_current_conditions(self):
        assert get_endpoints_for_intent("current_conditions") == ["env_params"]

    def test_forecast(self):
        assert get_endpoints_for_intent("forecast") == ["heatmap"]

    def test_analysis(self):
        assert get_endpoints_for_intent("analysis") == [
            "env_params",
            "heatmap",
            "heat_intelligence",
        ]

    def test_emergency(self):
        assert get_endpoints_for_intent("emergency") == ["env_params"]

    def test_unknown_intent(self):
        assert get_endpoints_for_intent("unknown") == ["env_params"]


class TestParseQuery:
    def test_full_query(self):
        result = parse_query("what is the temperature in Phoenix today at 3 pm")
        assert result.location == "phoenix"
        assert result.intent == "current_conditions"
        assert result.date is not None
        assert result.time == "15:00"
        assert result.confidence > 0.5

    def test_parsed_query_dataclass(self):
        result = parse_query("heat in Chicago")
        assert isinstance(result, ParsedQuery)
        assert result.location == "chicago"
        assert result.endpoints_needed == ["env_params"]

    def test_entities_found(self):
        result = parse_query("temperature in Miami today")
        assert any("location:miami" in e for e in result.entities_found)
        assert any("intent:" in e for e in result.entities_found)

    def test_filter_type_week(self):
        result = parse_query("heat this week")
        assert result.filter_type == 4

    def test_filter_type_month(self):
        result = parse_query("temperature this month")
        assert result.filter_type == 5

    def test_raw_query_preserved(self):
        q = "how hot is it in Seattle"
        result = parse_query(q)
        assert result.raw_query == q

    def test_confidence_range(self):
        result = parse_query("what is the temperature")
        assert 0.0 <= result.confidence <= 1.0
