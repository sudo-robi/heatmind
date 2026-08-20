"""Tests for shadow testing (utils/shadow_testing.py)."""

from utils.shadow_testing import ShadowResult, ShadowTester, _quality_score


class TestQualityScore:
    def test_empty_result(self):
        assert _quality_score({}) == 0.0

    def test_full_result(self):
        result = {
            "summary": "Heat alert issued",
            "severity": "high",
            "recommendations": ["Stay hydrated", "Avoid outdoor activity"],
            "reasoning": "Heat index exceeds threshold",
        }
        score = _quality_score(result, heat_index=40)
        assert score == 1.0

    def test_partial_result(self):
        result = {"summary": "Heat alert", "severity": "moderate"}
        score = _quality_score(result)
        assert 0.3 <= score <= 0.5

    def test_severity_mismatch(self):
        result = {"summary": "Report", "severity": "low", "recommendations": ["x"]}
        score = _quality_score(result, heat_index=50)
        # severity=low but heat_index=50 expects extreme, so no match bonus
        assert score < 0.8

    def test_severity_match(self):
        result = {"summary": "Report", "severity": "extreme", "recommendations": ["x"]}
        score = _quality_score(result, heat_index=50)
        assert score >= 0.8

    def test_recommendations_as_dict(self):
        result = {
            "summary": "Alert",
            "severity": "high",
            "recommendations": {"action1": "Do something"},
        }
        score = _quality_score(result, heat_index=40)
        assert score >= 0.6


class TestShadowTester:
    def test_should_shadow_deterministic(self):
        tester = ShadowTester()
        r1 = tester.should_shadow("test query same time")
        r2 = tester.should_shadow("test query same time")
        # Same seed should produce same result
        assert r1 == r2

    def test_compare_results_primary_wins(self):
        tester = ShadowTester()
        primary = {"summary": "Alert", "severity": "high", "recommendations": ["x"], "reasoning": "because"}
        shadow = {"summary": "Report"}
        result = tester.compare_results(primary, shadow, primary_model="gpt-4o", shadow_model="haiku")
        assert result.winner == "primary"
        assert result.primary_score > result.shadow_score

    def test_compare_results_shadow_wins(self):
        tester = ShadowTester()
        primary = {"summary": "Brief"}
        shadow = {"summary": "Alert", "severity": "extreme", "recommendations": ["x"], "reasoning": "trace"}
        result = tester.compare_results(primary, shadow, query="heat emergency", heat_index=50)
        assert result.winner == "shadow"

    def test_compare_results_tie(self):
        tester = ShadowTester()
        primary = {"summary": "A"}
        shadow = {"summary": "B"}
        result = tester.compare_results(primary, shadow)
        assert result.winner == "tie"

    def test_record_comparison(self):
        tester = ShadowTester()
        r = ShadowResult(
            query="test",
            primary_model="a",
            shadow_model="b",
            primary_result={},
            shadow_result={},
            primary_score=0.5,
            shadow_score=0.5,
            winner="tie",
        )
        tester.record_comparison(r)
        stats = tester.get_stats()
        assert stats["total"] == 1

    def test_promotion_not_enough_data(self):
        tester = ShadowTester()
        rec = tester.get_promotion_recommendation()
        assert rec["promote"] is False
        assert "Need" in rec["reason"]

    def test_promotion_shadow_wins(self):
        tester = ShadowTester()
        for i in range(25):
            tester.record_comparison(
                ShadowResult(
                    query=f"q{i}",
                    primary_model="old",
                    shadow_model="new",
                    primary_result={},
                    shadow_result={},
                    primary_score=0.3,
                    shadow_score=0.9,
                    winner="shadow",
                )
            )
        rec = tester.get_promotion_recommendation()
        assert rec["promote"] is True
        assert rec["shadow_model"] == "new"
        assert rec["win_rate"] >= 0.6

    def test_promotion_shadow_loses(self):
        tester = ShadowTester()
        for i in range(25):
            tester.record_comparison(
                ShadowResult(
                    query=f"q{i}",
                    primary_model="old",
                    shadow_model="new",
                    primary_result={},
                    shadow_result={},
                    primary_score=0.9,
                    shadow_score=0.3,
                    winner="primary",
                )
            )
        rec = tester.get_promotion_recommendation()
        assert rec["promote"] is False

    def test_get_stats_empty(self):
        tester = ShadowTester()
        stats = tester.get_stats()
        assert stats["total"] == 0
        assert stats["win_rates"] == {}

    def test_get_stats_mixed(self):
        tester = ShadowTester()
        for i in range(10):
            winner = "shadow" if i % 2 == 0 else "primary"
            tester.record_comparison(
                ShadowResult(
                    query=f"q{i}",
                    primary_model="old",
                    shadow_model="new",
                    primary_result={},
                    shadow_result={},
                    winner=winner,
                )
            )
        stats = tester.get_stats()
        assert stats["total"] == 10
        assert "old" in stats["win_rates"]
        assert "new" in stats["win_rates"]
