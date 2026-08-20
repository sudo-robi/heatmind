"""Tests for Failure Mode Taxonomy (utils/failure_modes.py)."""

from utils.failure_modes import (
    FailureRecord,
    FailureType,
    classify,
    recover,
)


class TestFailureType:
    def test_all_seven_types_exist(self):
        assert len(FailureType) == 7
        expected = {"HARD", "SILENT", "PARTIAL", "CONTRADICTION", "CASCADE", "LOOP", "CONTEXT"}
        assert {ft.value for ft in FailureType} == expected

    def test_failure_record_to_dict(self):
        rec = FailureRecord(
            type=FailureType.HARD, error="timeout", recovery_strategy="retry", attempts=1, resolved=False
        )
        d = rec.to_dict()
        assert d["type"] == "HARD"
        assert d["error"] == "timeout"
        assert d["attempts"] == 1
        assert d["resolved"] is False


class TestClassify:
    def test_hard_timeout(self):
        assert classify("Connection timed out") == FailureType.HARD

    def test_hard_connection_error(self):
        assert classify("ECONNREFUSED: service unavailable") == FailureType.HARD

    def test_hard_http_500(self):
        assert classify("HTTP 500 Internal Server Error") == FailureType.HARD

    def test_silent_wrong_output(self):
        assert classify("unexpected output format", {"output_valid": False}) == FailureType.SILENT

    def test_silent_empty_error(self):
        assert classify(None) == FailureType.SILENT

    def test_silent_empty_string(self):
        assert classify("") == FailureType.SILENT

    def test_partial_data(self):
        assert classify("incomplete response", {"partial": True}) == FailureType.PARTIAL

    def test_partial_context(self):
        assert classify("data missing", {"partial": True}) == FailureType.PARTIAL

    def test_contradiction_detected(self):
        assert classify("data conflict", {"contradiction_detected": True}) == FailureType.CONTRADICTION

    def test_contradiction_keyword(self):
        assert classify("sources contradict each other") == FailureType.CONTRADICTION

    def test_cascade_context(self):
        assert classify("dependency failed", {"cascade": True}) == FailureType.CASCADE

    def test_cascade_keyword(self):
        assert classify("cascade failure in pipeline") == FailureType.CASCADE

    def test_loop_high_iteration_count(self):
        assert classify("retry attempt", {"iteration_count": 5}) == FailureType.LOOP

    def test_loop_keyword(self):
        assert classify("stuck in loop") == FailureType.LOOP

    def test_context_window_exceeded(self):
        assert classify("context window exceeded") == FailureType.CONTEXT

    def test_context_token_limit(self):
        assert classify("token limit reached") == FailureType.CONTEXT

    def test_exception_as_error(self):
        assert classify(TimeoutError("request timed out")) == FailureType.HARD

    def test_dict_as_error(self):
        assert classify({"message": "connection refused"}) == FailureType.HARD

    def test_unknown_error_defaults_to_hard(self):
        assert classify("something weird happened") == FailureType.HARD


class TestRecover:
    def test_hard_first_retry(self):
        strategy = recover(FailureType.HARD, "timeout", {"attempts": 0})
        assert "retry" in strategy.lower()
        assert "1/3" in strategy

    def test_hard_second_retry(self):
        strategy = recover(FailureType.HARD, "timeout", {"attempts": 1})
        assert "retry" in strategy.lower()
        assert "2/3" in strategy

    def test_hard_max_retries_exceeded(self):
        strategy = recover(FailureType.HARD, "timeout", {"attempts": 3})
        assert "max retries" in strategy.lower() or "escalate" in strategy.lower()

    def test_silent_recovery(self):
        strategy = recover(FailureType.SILENT, "wrong output")
        assert "schema" in strategy.lower() or "retry" in strategy.lower()

    def test_partial_with_fields(self):
        strategy = recover(FailureType.PARTIAL, "missing data", {"missing_fields": ["temp", "humidity"]})
        assert "temp" in strategy
        assert "humidity" in strategy

    def test_partial_without_fields(self):
        strategy = recover(FailureType.PARTIAL, "incomplete")
        assert "missing" in strategy.lower() or "fill" in strategy.lower()

    def test_contradiction_with_sources(self):
        strategy = recover(FailureType.CONTRADICTION, "conflict", {"conflicting_sources": ["sensor_a", "sensor_b"]})
        assert "sensor_a" in strategy
        assert "sensor_b" in strategy

    def test_cascade_with_checkpoint(self):
        strategy = recover(FailureType.CASCADE, "dep failed", {"last_checkpoint": "step_2"})
        assert "step_2" in strategy
        assert "rollback" in strategy.lower()

    def test_cascade_without_checkpoint(self):
        strategy = recover(FailureType.CASCADE, "dep failed")
        assert "rollback" in strategy.lower()

    def test_loop_with_last_best(self):
        strategy = recover(FailureType.LOOP, "stuck", {"last_best_output": "partial result"})
        assert "partial result" in strategy
        assert "force exit" in strategy.lower()

    def test_loop_without_last_best(self):
        strategy = recover(FailureType.LOOP, "stuck")
        assert "force exit" in strategy.lower() or "escalate" in strategy.lower()

    def test_context_recovery(self):
        strategy = recover(FailureType.CONTEXT, "too long")
        assert "compress" in strategy.lower() or "retry" in strategy.lower()
