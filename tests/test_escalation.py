"""Tests for escalation management."""

from utils.escalation import EscalationManager


class TestEscalationManager:
    def test_initial_state(self):
        em = EscalationManager()
        status = em.get_status("zone1")
        assert status["level"] == "none"

    def test_escalate_level_1(self):
        em = EscalationManager()
        result = em.evaluate("zone1", heat_index=35.0)
        assert result["escalated"] is True
        assert result["level"] == "monitor"

    def test_escalate_level_2(self):
        em = EscalationManager()
        result = em.evaluate("zone1", heat_index=42.0)
        assert result["escalated"] is True
        assert result["level"] == "notify"

    def test_escalate_level_3(self):
        em = EscalationManager()
        result = em.evaluate("zone1", heat_index=47.0)
        assert result["escalated"] is True
        assert result["level"] == "alert"

    def test_escalate_level_4(self):
        em = EscalationManager()
        result = em.evaluate("zone1", heat_index=52.0)
        assert result["escalated"] is True
        assert result["level"] == "emergency"

    def test_escalate_level_5(self):
        em = EscalationManager()
        result = em.evaluate("zone1", heat_index=55.0)
        assert result["escalated"] is True
        assert result["level"] == "critical"

    def test_same_level_no_escalation(self):
        em = EscalationManager()
        em.evaluate("zone1", heat_index=42.0)
        result = em.evaluate("zone1", heat_index=43.0)
        assert result["escalated"] is False
        assert result["reason"] == "already_at_same_level"

    def test_acknowledge(self):
        em = EscalationManager()
        em.evaluate("zone1", heat_index=42.0)
        assert em.acknowledge("zone1") is True
        status = em.get_status("zone1")
        assert status["acknowledged"] is True

    def test_acknowledge_nonexistent(self):
        em = EscalationManager()
        assert em.acknowledge("nonexistent") is False

    def test_get_all_status(self):
        em = EscalationManager()
        em.evaluate("zone1", heat_index=42.0)
        em.evaluate("zone2", heat_index=52.0)
        all_status = em.get_status()
        assert "zone1" in all_status
        assert "zone2" in all_status

    def test_actions_included(self):
        em = EscalationManager()
        result = em.evaluate("zone1", heat_index=52.0)
        assert "actions" in result
        assert "send_alert" in result["actions"]
        assert "channels" in result
