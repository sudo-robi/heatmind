"""Tests for the cost-aware autonomy ledger (utils/cost_ledger.py)."""

import pytest

from utils.cost_ledger import TOOL_COST_USD, CostLedger
from utils.llm import MockLLM


class TestCostLedger:
    def test_empty_ledger(self):
        ledger = CostLedger()
        summary = ledger.summary()
        assert summary["usd"] == 0.0
        assert summary["llm_calls"] == 0
        assert summary["tool_calls"] == 0
        assert summary["ledger"] == []

    def test_record_tool_sums_cost(self):
        ledger = CostLedger()
        ledger.record_tool("env_params")
        ledger.record_tool("heat_intelligence")
        expected = TOOL_COST_USD["env_params"] + TOOL_COST_USD["heat_intelligence"]
        assert ledger.total_usd() == pytest.approx(expected)
        assert ledger.tool_calls() == 2

    def test_record_llm(self):
        ledger = CostLedger()
        ledger.record_llm(MockLLM(), "plan", input_chars=500, output_chars=200)
        summary = ledger.summary()
        assert summary["llm_calls"] == 1
        assert summary["ledger"][0]["phase"] == "plan"
        assert summary["ledger"][0]["model"] == "mock"
        assert summary["ledger"][0]["cost_usd"] == 0.0  # mock model is free

    def test_unknown_tool_costs_zero(self):
        ledger = CostLedger()
        ledger.record_tool("not_a_tool")
        assert ledger.total_usd() == 0.0

    def test_len(self):
        ledger = CostLedger()
        ledger.record_tool("env_params")
        ledger.record_tool("satellite")
        assert len(ledger) == 2
