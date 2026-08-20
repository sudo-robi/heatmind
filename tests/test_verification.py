"""Tests for the verification loop (utils/verification.py)."""

from utils.verification import (
    VerificationResult,
    _extract_heat_index,
    _extract_severity,
    _normalize,
    _rec_matches_any,
    verify_answer,
)


class TestExtractHelpers:
    def test_extract_heat_index_from_env_params(self):
        obs = {"env_params": {"heat_index_celsius": 45.0}}
        assert _extract_heat_index(obs) == 45.0

    def test_extract_heat_index_from_heat_index_key(self):
        obs = {"env_params": {"heat_index": 38.5}}
        assert _extract_heat_index(obs) == 38.5

    def test_extract_heat_index_missing(self):
        obs = {"env_params": {"humidity": 60}}
        assert _extract_heat_index(obs) is None

    def test_extract_heat_index_no_env_params(self):
        obs = {}
        assert _extract_heat_index(obs) is None

    def test_extract_severity_valid(self):
        assert _extract_severity({"severity": "extreme"}) == "extreme"
        assert _extract_severity({"severity": "low"}) == "low"

    def test_extract_severity_invalid(self):
        assert _extract_severity({"severity": "unknown"}) is None
        assert _extract_severity({}) is None

    def test_normalize(self):
        assert _normalize("Stay Indoors!") == "stay indoors"
        assert _normalize("  EVACUATE  ") == "evacuate"

    def test_rec_matches_exact(self):
        assert _rec_matches_any("stay indoors", {"stay indoors"})

    def test_rec_matches_partial(self):
        assert _rec_matches_any("stay indoors immediately", {"stay indoors"})

    def test_rec_no_match(self):
        assert not _rec_matches_any("go for a walk", {"stay indoors"})


class TestVerifyAnswer:
    def test_valid_extreme_severity(self):
        answer = {
            "severity": "extreme",
            "recommendations": ["Evacuate immediately", "Seek emergency shelter"],
        }
        obs = {"env_params": {"heat_index_celsius": 47.0}}
        result = verify_answer(answer, obs)
        assert result["verified"] is True
        assert result["hallucination_risk"] == "low"
        assert len(result["results"]) > 0

    def test_valid_high_severity(self):
        answer = {
            "severity": "high",
            "recommendations": ["Stay indoors", "Limit outdoor exposure"],
        }
        obs = {"env_params": {"heat_index_celsius": 40.0}}
        result = verify_answer(answer, obs)
        assert result["verified"] is True

    def test_invalid_severity_too_low(self):
        """heat_index=47 should be extreme, not moderate."""
        answer = {
            "severity": "moderate",
            "recommendations": ["Stay hydrated"],
        }
        obs = {"env_params": {"heat_index_celsius": 47.0}}
        result = verify_answer(answer, obs)
        assert result["verified"] is False
        assert result["hallucination_risk"] == "high"

    def test_invalid_extreme_rec_for_low_severity(self):
        """'evacuate' recommendation is inappropriate for low severity."""
        answer = {
            "severity": "low",
            "recommendations": ["Evacuate immediately", "Enjoy the weather"],
        }
        obs = {"env_params": {"heat_index_celsius": 25.0}}
        result = verify_answer(answer, obs)
        # The evacuate recommendation should be flagged
        rec_results = [r for r in result["results"] if "recommendation" in r["claim"]]
        assert any(not r["supported"] for r in rec_results)

    def test_heat_index_in_answer_matches_observations(self):
        answer = {
            "severity": "extreme",
            "heat_index": 47.0,
            "recommendations": ["Evacuate"],
        }
        obs = {"env_params": {"heat_index_celsius": 47.0}}
        result = verify_answer(answer, obs)
        hi_results = [r for r in result["results"] if "heat_index value" in r["claim"]]
        assert all(r["supported"] for r in hi_results)

    def test_heat_index_in_answer_mismatches_observations(self):
        answer = {
            "severity": "extreme",
            "heat_index": 99.0,
            "recommendations": ["Evacuate"],
        }
        obs = {"env_params": {"heat_index_celsius": 47.0}}
        result = verify_answer(answer, obs)
        assert result["verified"] is False

    def test_no_severity_when_data_available(self):
        answer = {
            "recommendations": ["Stay cool"],
        }
        obs = {"env_params": {"heat_index_celsius": 42.0}}
        result = verify_answer(answer, obs)
        sev_results = [r for r in result["results"] if "severity" in r["claim"] and "recommendation" not in r["claim"]]
        assert any(not r["supported"] for r in sev_results)

    def test_empty_answer_and_observations(self):
        result = verify_answer({}, {})
        assert result["verified"] is True
        assert result["results"] == []

    def test_moderate_severity_valid(self):
        answer = {
            "severity": "moderate",
            "recommendations": ["Stay hydrated", "Wear sunscreen"],
        }
        obs = {"env_params": {"heat_index_celsius": 35.0}}
        result = verify_answer(answer, obs)
        assert result["verified"] is True

    def test_high_severity_valid(self):
        answer = {
            "severity": "high",
            "recommendations": ["Stay indoors", "Avoid outdoor activities"],
        }
        obs = {"env_params": {"heat_index_celsius": 40.0}}
        result = verify_answer(answer, obs)
        assert result["verified"] is True

    def test_verification_result_dataclass(self):
        vr = VerificationResult(
            claim="test claim",
            source_data="test source",
            supported=True,
            confidence=0.95,
        )
        assert vr.claim == "test claim"
        assert vr.supported is True
        assert vr.issue == ""
