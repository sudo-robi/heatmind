"""Tests for utils/trust.py - HITL Trust Gates."""

from utils.trust import get_trust, reset_trust


def test_trust_default_score():
    reset_trust()
    trust = get_trust()
    stats = trust.stats()
    assert stats["score"] >= 0.0
    assert stats["score"] <= 1.0
    assert stats["score"] == 0.5


def test_trust_approval():
    reset_trust()
    trust = get_trust()
    initial = trust.stats()["score"]
    trust.record_approval()
    after = trust.stats()["score"]
    assert after > initial


def test_trust_rejection():
    reset_trust()
    trust = get_trust()
    initial = trust.stats()["score"]
    trust.record_rejection()
    after = trust.stats()["score"]
    assert after < initial


def test_trust_gate_check():
    reset_trust()
    trust = get_trust()
    gate = trust.check_gate("test_action")
    assert "allowed" in gate
    assert "reason" in gate
    assert "trust_score" in gate
    assert "threshold" in gate


def test_trust_gate_known_actions():
    reset_trust()
    trust = get_trust()
    gate = trust.check_gate("daily_report")
    assert gate["threshold"] == 0.3
    assert gate["allowed"] is True

    gate2 = trust.check_gate("emergency_escalation")
    assert gate2["threshold"] == 0.7
    assert gate2["allowed"] is False


def test_trust_score_bounds():
    reset_trust()
    trust = get_trust()
    for _ in range(20):
        trust.record_rejection()
    assert trust.score == 0.0

    reset_trust()
    trust = get_trust()
    for _ in range(20):
        trust.record_approval()
    assert trust.score == 1.0
