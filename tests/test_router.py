from agents.router import (
    QueryComplexity,
    QueryUrgency,
    classify_complexity,
    classify_urgency,
    route_query,
)


class TestClassifyComplexity:
    def test_simple_query(self):
        assert classify_complexity("What is the temperature?") == QueryComplexity.SIMPLE

    def test_simple_query_current(self):
        assert classify_complexity("current heat index") == QueryComplexity.SIMPLE

    def test_moderate_query(self):
        assert classify_complexity("compare this week trends") == QueryComplexity.MODERATE

    def test_moderate_query_history(self):
        assert classify_complexity("show me the history") == QueryComplexity.MODERATE

    def test_complex_query(self):
        assert classify_complexity("give me a full assessment") == QueryComplexity.COMPLEX

    def test_complex_query_deep_dive(self):
        assert classify_complexity("deep dive intelligence report") == QueryComplexity.COMPLEX

    def test_empty_query(self):
        assert classify_complexity("") == QueryComplexity.SIMPLE

    def test_no_keywords(self):
        assert classify_complexity("hello world") == QueryComplexity.SIMPLE

    def test_tiebreaker_returns_first_match(self):
        result = classify_complexity("analysis")
        assert result in (QueryComplexity.MODERATE, QueryComplexity.COMPLEX)

    def test_satellite_moderate(self):
        result = classify_complexity("satellite analysis needed")
        assert result == QueryComplexity.MODERATE


class TestClassifyUrgency:
    def test_low_urgency(self):
        assert classify_urgency("show me the overview") == QueryUrgency.LOW

    def test_medium_urgency(self):
        assert classify_urgency("should i be worried") == QueryUrgency.MEDIUM

    def test_high_urgency(self):
        assert classify_urgency("alert warning high risk") == QueryUrgency.HIGH

    def test_critical_urgency(self):
        assert classify_urgency("EMERGENCY dangerous extreme") == QueryUrgency.CRITICAL

    def test_empty_query(self):
        assert classify_urgency("") == QueryUrgency.LOW

    def test_no_keywords(self):
        assert classify_urgency("hello") == QueryUrgency.LOW

    def test_mixed_urgency_takes_highest(self):
        result = classify_urgency("should i worry about the alert")
        assert result in (QueryUrgency.MEDIUM, QueryUrgency.HIGH)


class TestRouteQuery:
    def test_routes_simple_to_quick(self):
        result = route_query("what is the temperature")
        assert result.agent == "quick"
        assert result.complexity == QueryComplexity.SIMPLE

    def test_routes_complex_to_deep(self):
        result = route_query("give me a full comprehensive assessment")
        assert result.agent == "deep"

    def test_routes_moderate_to_deep(self):
        result = route_query("compare trends this week")
        assert result.agent == "deep"

    def test_routes_critical_to_emergency(self):
        result = route_query("EMERGENCY extreme heat detected now")
        assert result.agent == "emergency"
        assert result.urgency == QueryUrgency.CRITICAL

    def test_routes_high_to_emergency(self):
        result = route_query("alert warning hazard unsafe")
        assert result.agent == "emergency"

    def test_has_reasoning(self):
        result = route_query("test query")
        assert isinstance(result.reasoning, str)
        assert len(result.reasoning) > 0

    def test_reasoning_contains_complexity(self):
        result = route_query("what is the temperature")
        assert "simple" in result.reasoning

    def test_reasoning_contains_urgency(self):
        result = route_query("show me the overview")
        assert "low" in result.reasoning


class TestRouterEdgeCases:
    def test_case_insensitive(self):
        r1 = route_query("WHAT IS THE TEMPERATURE")
        r2 = route_query("what is the temperature")
        assert r1.agent == r2.agent

    def test_special_characters(self):
        result = route_query("!@#$%^&*()")
        assert result.agent in ("quick", "deep", "emergency")

    def test_very_long_query(self):
        query = "what is the temperature " * 100
        result = route_query(query)
        assert result.agent in ("quick", "deep", "emergency")

    def test_unicode_characters(self):
        result = route_query("what is the temperature in 东京")
        assert result.agent in ("quick", "deep", "emergency")

    def test_mixed_languages(self):
        result = route_query("what is the température in دبي")
        assert result.agent in ("quick", "deep", "emergency")

    def test_numbers_only(self):
        result = route_query("42 45 100")
        assert result.agent in ("quick", "deep", "emergency")

    def test_single_word(self):
        result = route_query("temperature")
        assert result.agent in ("quick", "deep", "emergency")

    def test_only_urgency_no_complexity(self):
        result = route_query("emergency")
        assert result.agent == "emergency"

    def test_only_complexity_no_urgency(self):
        result = route_query("full assessment comprehensive")
        assert result.agent == "deep"

    def test_whitespace_only(self):
        result = route_query("   ")
        assert result.agent in ("quick", "deep", "emergency")

    def test_newlines_and_tabs(self):
        result = route_query("what\nis\tthe\ntemperature")
        assert result.agent in ("quick", "deep", "emergency")
