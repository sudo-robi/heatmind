"""Tests for utils/agent_circuit_breaker.py - LLM Provider Protection."""

from utils.agent_circuit_breaker import CircuitBreaker, all_breakers_status


def test_circuit_breaker_initial_state():
    cb = CircuitBreaker("test_provider")
    assert cb.state.value == "closed"


def test_circuit_breaker_record_success():
    cb = CircuitBreaker("test_provider")
    cb.record_success()
    status = cb.status()
    assert status["successes"] == 1


def test_circuit_breaker_record_failure():
    cb = CircuitBreaker("test_provider")
    cb.record_failure()
    status = cb.status()
    assert status["failures"] == 1


def test_circuit_breaker_opens_after_threshold():
    cb = CircuitBreaker("test_provider", failure_threshold=3)
    for _ in range(3):
        cb.record_failure()
    assert cb.state.value == "open"
    assert cb.allow_request() is False


def test_circuit_breaker_reset():
    cb = CircuitBreaker("test_provider")
    cb.record_failure()
    cb.record_failure()
    cb.reset()
    assert cb.state.value == "closed"
    assert cb.status()["failures"] == 0


def test_all_breakers_status():
    breakers = all_breakers_status()
    assert isinstance(breakers, list)
