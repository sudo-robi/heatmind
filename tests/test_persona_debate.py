"""Tests for Multi-Agent Persona Debate (utils/persona_debate.py)."""

from utils.persona_debate import (
    PERSONAS,
    DebateOpinion,
    DebateResult,
    run_debate,
    select_personas,
)


class TestPersonas:
    def test_all_six_personas_defined(self):
        expected = {
            "geo_analyst",
            "health_officer",
            "urban_planner",
            "cost_optimizer",
            "emergency_coordinator",
            "risk_assessor",
        }
        assert set(PERSONAS.keys()) == expected

    def test_each_persona_has_required_keys(self):
        for pid, p in PERSONAS.items():
            assert "name" in p, f"{pid} missing name"
            assert "role" in p, f"{pid} missing role"
            assert "system_prompt" in p, f"{pid} missing system_prompt"
            assert "opinion" in p["system_prompt"].lower(), f"{pid} prompt should request opinion"

    def test_opinion_dataclass_fields(self):
        o = DebateOpinion(persona="test", opinion="hot", recommended_action="evacuate")
        assert o.persona == "test"
        assert o.opinion == "hot"
        assert o.recommended_action == "evacuate"

    def test_debate_result_to_dict(self):
        r = DebateResult(
            opinions=[DebateOpinion(persona="a", opinion="x", recommended_action="y")],
            consensus_action="y",
            dissent="",
        )
        d = r.to_dict()
        assert len(d["opinions"]) == 1
        assert d["consensus_action"] == "y"
        assert d["dissent"] == ""


class TestSelectPersonas:
    def test_extreme_selects_emergency_and_health(self):
        personas = select_personas("extreme", "what is the temperature?")
        assert "emergency_coordinator" in personas
        assert "health_officer" in personas
        assert len(personas) <= 4

    def test_high_selects_health_and_urban(self):
        personas = select_personas("high", "infrastructure impact?")
        assert "health_officer" in personas

    def test_moderate_selects_geo_and_urban(self):
        personas = select_personas("moderate", "general conditions")
        assert "geo_analyst" in personas
        assert "urban_planner" in personas

    def test_low_selects_geo_and_risk(self):
        personas = select_personas("low", "routine check")
        assert "geo_analyst" in personas
        assert "risk_assessor" in personas

    def test_context_keyword_adds_personas(self):
        personas = select_personas("moderate", "vulnerable populations at risk")
        assert "health_officer" in personas

    def test_unknown_severity_falls_back_to_moderate(self):
        personas = select_personas("unknown", "query")
        assert "geo_analyst" in personas

    def test_max_four_personas(self):
        personas = select_personas("extreme", "vulnerable evacuation infrastructure cost spatial")
        assert len(personas) <= 4


class TestRunDebate:
    def test_mock_debate_returns_valid_structure(self):
        result = run_debate("What is the heat index?", {"heat_index": 42.5}, severity="high")
        assert "opinions" in result
        assert "consensus_action" in result
        assert "dissent" in result
        assert len(result["opinions"]) >= 2

    def test_mock_debate_extreme_has_emergency_coordinator(self):
        result = run_debate("Emergency!", {"heat_index": 48.0}, severity="extreme")
        personas = [o["persona"] for o in result["opinions"]]
        assert "emergency_coordinator" in personas

    def test_mock_debate_dissent_on_disagreement(self):
        result = run_debate("High severity situation", {"heat_index": 40.0}, severity="high")
        assert isinstance(result["dissent"], str)

    def test_mock_debate_low_severity(self):
        result = run_debate("Normal conditions", {"heat_index": 25.0}, severity="low")
        assert len(result["opinions"]) >= 1
        assert result["consensus_action"]

    def test_mock_debate_default_severity(self):
        result = run_debate("General query", {"heat_index": 30.0}, severity="unknown")
        assert "opinions" in result

    def test_mock_debate_empty_observations(self):
        result = run_debate("Test query", {}, severity="moderate")
        assert "opinions" in result

    def test_mock_debate_returns_string_actions(self):
        result = run_debate("Query", {}, severity="extreme")
        assert isinstance(result["consensus_action"], str)
        for op in result["opinions"]:
            assert isinstance(op["recommended_action"], str)
