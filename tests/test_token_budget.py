"""Tests for token budget enforcement (utils/token_budget.py)."""

import pytest

from utils.token_budget import PHASE_DEFAULTS, BudgetManager, TokenBudget


class TestTokenBudget:
    def test_defaults(self):
        b = TokenBudget(phase="plan")
        assert b.max_input_tokens == 2000
        assert b.max_output_tokens == 500
        assert b.used_input_tokens == 0
        assert b.used_output_tokens == 0

    def test_remaining(self):
        b = TokenBudget(phase="plan", max_input_tokens=100, max_output_tokens=50)
        b.used_input_tokens = 30
        b.used_output_tokens = 20
        assert b.remaining_input == 70
        assert b.remaining_output == 30

    def test_pct_used(self):
        b = TokenBudget(phase="plan", max_input_tokens=100, max_output_tokens=100)
        b.used_input_tokens = 50
        b.used_output_tokens = 80
        assert b.input_pct_used == pytest.approx(0.5)
        assert b.output_pct_used == pytest.approx(0.8)

    def test_pct_used_zero_max(self):
        b = TokenBudget(phase="plan", max_input_tokens=0, max_output_tokens=0)
        assert b.input_pct_used == 1.0
        assert b.output_pct_used == 1.0

    def test_is_over(self):
        b = TokenBudget(phase="plan", max_input_tokens=100, max_output_tokens=100)
        assert not b.is_over()
        b.used_input_tokens = 100
        assert b.is_over()
        b.used_input_tokens = 50
        b.used_output_tokens = 100
        assert b.is_over()


class TestBudgetManager:
    def test_check_budget_returns_defaults(self):
        mgr = BudgetManager()
        info = mgr.check_budget("plan")
        assert info["remaining_input"] == 2000
        assert info["remaining_output"] == 500

    def test_record_usage(self):
        mgr = BudgetManager()
        mgr.record_usage("plan", input_tokens=500, output_tokens=100)
        info = mgr.check_budget("plan")
        assert info["remaining_input"] == 1500
        assert info["remaining_output"] == 400

    def test_compress_if_needed_no_compress(self):
        mgr = BudgetManager()
        text = "short text"
        result = mgr.compress_if_needed(text, "plan")
        assert result == text

    def test_compress_if_needed_truncates(self):
        mgr = BudgetManager()
        # Exhaust output budget
        mgr.record_usage("plan", input_tokens=0, output_tokens=490)
        text = "x" * 2000
        result = mgr.compress_if_needed(text, "plan")
        assert len(result) < len(text)
        assert "[compressed]" in result or "[truncated]" in result

    def test_compress_if_needed_small_remaining(self):
        mgr = BudgetManager()
        # Leave very small remaining budget
        mgr.record_usage("plan", input_tokens=0, output_tokens=498)
        text = "x" * 2000
        result = mgr.compress_if_needed(text, "plan")
        assert "[truncated]" in result

    def test_get_daily_summary(self):
        mgr = BudgetManager()
        mgr.record_usage("plan", input_tokens=100, output_tokens=50)
        mgr.record_usage("reflect", input_tokens=200, output_tokens=80)
        summary = mgr.get_daily_summary()
        assert summary["input_tokens"] == 300
        assert summary["output_tokens"] == 130
        assert summary["total_tokens"] == 430

    def test_is_over_budget(self):
        mgr = BudgetManager()
        assert not mgr.is_over_budget()

    def test_reset_phase(self):
        mgr = BudgetManager()
        mgr.record_usage("plan", input_tokens=500, output_tokens=100)
        mgr.reset_phase("plan")
        info = mgr.check_budget("plan")
        assert info["remaining_input"] == 2000

    def test_phase_defaults_all_phases(self):
        for phase in ("plan", "reflect", "synthesize", "debate"):
            assert phase in PHASE_DEFAULTS
            inp, out = PHASE_DEFAULTS[phase]
            assert inp > 0
            assert out > 0
