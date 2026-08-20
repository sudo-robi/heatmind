"""Tests for circuit breaker pattern."""

import time

from utils.circuit_breaker import CircuitBreaker, CircuitState


class TestCircuitBreaker:
    def test_initial_state_closed(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        assert cb.state == CircuitState.CLOSED

    def test_success_keeps_closed(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_failure_increments_count(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        cb.record_failure()
        assert cb._failure_count == 1

    def test_threshold_opens_circuit(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.CLOSED
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_open_circuit_denies_request(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    def test_recovery_timeout_transitions_to_half_open(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN

    def test_success_in_half_open_closes(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED

    def test_failure_in_half_open_opens(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_success_decrements_failure_count(self):
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=1)
        cb.record_failure()
        cb.record_failure()
        cb.record_success()
        assert cb._failure_count == 1

    def test_custom_failure_threshold(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=1)
        cb.record_failure()
        assert cb.state == CircuitState.OPEN

    def test_get_stats(self):
        cb = CircuitBreaker(failure_threshold=3, recovery_timeout=1, name="test")
        stats = cb.get_stats()
        assert stats["name"] == "test"
        assert stats["state"] == "closed"
        assert stats["failure_count"] == 0

    def test_half_open_allows_requests(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, half_open_max=2)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.allow_request() is True
        assert cb.allow_request() is True

    def test_half_open_allow_request_always_true(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, half_open_max=1)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.allow_request() is True
        assert cb.allow_request() is True

    def test_record_success_in_open_state_is_noop(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=10)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == CircuitState.OPEN
        cb.record_success()
        assert cb.state == CircuitState.OPEN
        assert cb._failure_count == 2

    def test_get_stats_after_failures(self):
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=1, name="stats-test")
        cb.record_failure()
        cb.record_failure()
        stats = cb.get_stats()
        assert stats["name"] == "stats-test"
        assert stats["failure_count"] == 2
        assert stats["success_count"] == 0
        assert stats["state"] == "closed"

    def test_get_stats_open_state(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=10, name="open-stats")
        cb.record_failure()
        cb.record_failure()
        stats = cb.get_stats()
        assert stats["state"] == "open"
        assert stats["failure_count"] == 2

    def test_allow_request_closed_returns_true(self):
        cb = CircuitBreaker(failure_threshold=5, recovery_timeout=1)
        assert cb.allow_request() is True

    def test_allow_request_open_returns_false(self):
        cb = CircuitBreaker(failure_threshold=1, recovery_timeout=10)
        cb.record_failure()
        assert cb.allow_request() is False

    def test_half_open_success_count_accumulates(self):
        cb = CircuitBreaker(failure_threshold=2, recovery_timeout=0.1, half_open_max=3)
        cb.record_failure()
        cb.record_failure()
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb._success_count == 1
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb._success_count == 2
        assert cb.state == CircuitState.HALF_OPEN
        cb.record_success()
        assert cb.state == CircuitState.CLOSED
