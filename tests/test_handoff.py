"""Tests for Structured Handoff Documents (utils/handoff.py)."""

import pytest

from utils.handoff import (
    HandoffDocument,
    create_handoff,
    render_handoff_prompt,
    validate_handoff,
)


class TestHandoffDocument:
    def test_creation_with_defaults(self):
        doc = HandoffDocument(
            from_agent="agent_a",
            to_agent="agent_b",
            context={"data": "test"},
            deliverable="produce report",
            quality_expectations=["accurate", "complete"],
        )
        assert doc.from_agent == "agent_a"
        assert doc.to_agent == "agent_b"
        assert doc.priority == "normal"
        assert doc.timeout_seconds == 120
        assert doc.created_at  # auto-populated

    def test_to_dict(self):
        doc = HandoffDocument(
            from_agent="a",
            to_agent="b",
            context={"k": "v"},
            deliverable="output",
            quality_expectations=["q1"],
            created_at="2026-01-01T00:00:00Z",
        )
        d = doc.to_dict()
        assert d["from_agent"] == "a"
        assert d["to_agent"] == "b"
        assert d["context"] == {"k": "v"}
        assert d["deliverable"] == "output"
        assert d["quality_expectations"] == ["q1"]


class TestCreateHandoff:
    def test_valid_handoff(self):
        doc = create_handoff(
            from_agent="coordinator",
            to_agent="analyst",
            context={"severity": "high", "heat_index": 40.0},
            deliverable="Thermal analysis report",
            quality_expectations=["covers all zones", "cites statistics"],
        )
        assert doc.from_agent == "coordinator"
        assert doc.to_agent == "analyst"

    def test_custom_priority_and_timeout(self):
        doc = create_handoff(
            from_agent="a",
            to_agent="b",
            context={"x": 1},
            deliverable="y",
            quality_expectations=["z"],
            timeout_seconds=60,
            priority="critical",
        )
        assert doc.timeout_seconds == 60
        assert doc.priority == "critical"

    def test_missing_from_agent_raises(self):
        with pytest.raises(ValueError, match="Missing required field"):
            create_handoff(
                from_agent="",
                to_agent="b",
                context={"x": 1},
                deliverable="y",
                quality_expectations=["z"],
            )

    def test_missing_to_agent_raises(self):
        with pytest.raises(ValueError, match="Missing required field"):
            create_handoff(
                from_agent="a",
                to_agent="",
                context={"x": 1},
                deliverable="y",
                quality_expectations=["z"],
            )

    def test_empty_context_raises(self):
        with pytest.raises(ValueError, match="Context cannot be empty"):
            create_handoff(
                from_agent="a",
                to_agent="b",
                context={},
                deliverable="y",
                quality_expectations=["z"],
            )

    def test_empty_quality_expectations_raises(self):
        with pytest.raises(ValueError, match="Quality expectations cannot be empty"):
            create_handoff(
                from_agent="a",
                to_agent="b",
                context={"x": 1},
                deliverable="y",
                quality_expectations=[],
            )

    def test_invalid_priority_raises(self):
        with pytest.raises(ValueError, match="Invalid priority"):
            create_handoff(
                from_agent="a",
                to_agent="b",
                context={"x": 1},
                deliverable="y",
                quality_expectations=["z"],
                priority="urgent",
            )


class TestValidateHandoff:
    def test_valid_handoff_no_errors(self):
        doc = HandoffDocument(
            from_agent="a",
            to_agent="b",
            context={"x": 1},
            deliverable="y",
            quality_expectations=["z"],
        )
        errors = validate_handoff(doc)
        assert errors == []

    def test_missing_from_agent(self):
        doc = HandoffDocument(
            from_agent="", to_agent="b", context={"x": 1}, deliverable="y", quality_expectations=["z"]
        )
        errors = validate_handoff(doc)
        assert any("from_agent" in e for e in errors)

    def test_context_not_dict(self):
        doc = HandoffDocument(from_agent="a", to_agent="b", context="bad", deliverable="y", quality_expectations=["z"])  # type: ignore
        errors = validate_handoff(doc)
        assert any("Context" in e for e in errors)

    def test_quality_expectations_not_list(self):
        doc = HandoffDocument(
            from_agent="a", to_agent="b", context={"x": 1}, deliverable="y", quality_expectations="bad"
        )  # type: ignore
        errors = validate_handoff(doc)
        assert any("Quality" in e for e in errors)

    def test_invalid_priority(self):
        doc = HandoffDocument(
            from_agent="a",
            to_agent="b",
            context={"x": 1},
            deliverable="y",
            quality_expectations=["z"],
            priority="urgent",
        )
        errors = validate_handoff(doc)
        assert any("priority" in e.lower() for e in errors)

    def test_negative_timeout(self):
        doc = HandoffDocument(
            from_agent="a",
            to_agent="b",
            context={"x": 1},
            deliverable="y",
            quality_expectations=["z"],
            timeout_seconds=-1,
        )
        errors = validate_handoff(doc)
        assert any("Timeout" in e for e in errors)


class TestRenderHandoffPrompt:
    def test_contains_agents(self):
        doc = HandoffDocument(
            from_agent="coordinator",
            to_agent="analyst",
            context={"severity": "high"},
            deliverable="analysis",
            quality_expectations=["accurate"],
        )
        prompt = render_handoff_prompt(doc)
        assert "coordinator" in prompt
        assert "analyst" in prompt

    def test_contains_deliverable(self):
        doc = HandoffDocument(
            from_agent="a",
            to_agent="b",
            context={"k": "v"},
            deliverable="Produce a thermal report",
            quality_expectations=["complete"],
        )
        prompt = render_handoff_prompt(doc)
        assert "Produce a thermal report" in prompt

    def test_contains_quality_expectations(self):
        doc = HandoffDocument(
            from_agent="a",
            to_agent="b",
            context={"k": "v"},
            deliverable="output",
            quality_expectations=["no errors", "within 5 minutes"],
        )
        prompt = render_handoff_prompt(doc)
        assert "no errors" in prompt
        assert "within 5 minutes" in prompt

    def test_critical_priority_tagged(self):
        doc = HandoffDocument(
            from_agent="a",
            to_agent="b",
            context={"k": "v"},
            deliverable="output",
            quality_expectations=["q"],
            priority="critical",
        )
        prompt = render_handoff_prompt(doc)
        assert "CRITICAL" in prompt

    def test_normal_priority_not_tagged(self):
        doc = HandoffDocument(
            from_agent="a",
            to_agent="b",
            context={"k": "v"},
            deliverable="output",
            quality_expectations=["q"],
            priority="normal",
        )
        prompt = render_handoff_prompt(doc)
        assert "[NORMAL]" not in prompt

    def test_contains_json_contract(self):
        doc = HandoffDocument(
            from_agent="a",
            to_agent="b",
            context={"k": "v"},
            deliverable="output",
            quality_expectations=["q"],
        )
        prompt = render_handoff_prompt(doc)
        assert "status" in prompt
        assert "complete" in prompt
