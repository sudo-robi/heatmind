"""Tests for the Root Cause Analysis protocol (utils/rca.py)."""

from utils.rca import (
    RCAReport,
    analyze_failure,
    classify_failure,
    rca_to_dict,
)


class TestClassifyFailure:
    def test_timeout(self):
        assert classify_failure("Connection timed out") == "api_timeout"

    def test_api_error(self):
        assert classify_failure("API error 500") == "api_error"

    def test_rate_limit(self):
        assert classify_failure("Rate limit exceeded 429") == "api_error"

    def test_json_parse_error(self):
        assert classify_failure("json parse error: expecting value") == "llm_parse_error"

    def test_json_decode(self):
        assert classify_failure("JSONDecodeError: Expecting value") == "llm_parse_error"

    def test_llm_unavailable(self):
        assert classify_failure("LLM unavailable: connection refused") == "llm_unavailable"

    def test_tool_error_with_context(self):
        ctx = {"phase": "tool execution", "tool": "env_params"}
        assert classify_failure("RuntimeError: unexpected response format", ctx) == "tool_error"

    def test_data_missing(self):
        ctx = {"phase": "synthesize"}
        assert classify_failure("Field not found in response", ctx) == "data_missing"

    def test_synthesis_failure(self):
        assert classify_failure("Synthesis returned empty response") == "synthesis_failure"

    def test_delegation_failure(self):
        assert classify_failure("Sub-agent delegation returned empty response") == "delegation_failure"

    def test_exception_type(self):
        assert classify_failure(TimeoutError("connection timed out")) == "api_timeout"

    def test_none_error(self):
        assert classify_failure(None) == "unknown"

    def test_string_error_unknown(self):
        assert classify_failure("something weird happened") == "unknown"

    def test_unknown_exception(self):
        assert classify_failure(ValueError("unexpected value")) == "unknown"


class TestAnalyzeFailure:
    def test_api_timeout(self):
        error = TimeoutError("request timed out after 30s")
        context = {"phase": "tool execution", "tool": "env_params", "zone": "Dubai"}
        report = analyze_failure(error, context)
        assert report.failure_type == "api_timeout"
        assert report.severity == "P2"
        assert "timeout" in report.blast_radius.lower() or "incomplete" in report.blast_radius.lower()
        assert len(report.evidence) > 0
        assert len(report.recommendation) > 0

    def test_api_error(self):
        error = "HTTP 500: Internal Server Error from FortyGuard API"
        context = {"phase": "synthesis"}
        report = analyze_failure(error, context)
        assert report.failure_type == "api_error"
        assert report.severity == "P2"

    def test_llm_parse_error_in_plan(self):
        error = "json decode error"
        context = {"phase": "plan"}
        report = analyze_failure(error, context)
        assert report.failure_type == "llm_parse_error"
        assert "ChainAgent" in report.blast_radius or "fallback" in report.blast_radius.lower()

    def test_llm_parse_error_in_synthesize(self):
        error = "json decode error: Expecting value: line 1 column 1"
        context = {"phase": "synthesize"}
        report = analyze_failure(error, context)
        assert report.failure_type == "llm_parse_error"
        assert "no user-facing" in report.blast_radius.lower() or "answer" in report.blast_radius.lower()

    def test_llm_unavailable(self):
        error = "Connection refused to api.openai.com"
        context = {"phase": "plan"}
        report = analyze_failure(error, context)
        assert report.failure_type == "llm_unavailable"
        assert report.severity == "P1"

    def test_tool_error_with_trace(self):
        error = RuntimeError("unexpected response format")
        context = {"phase": "tool execution", "tool": "satellite", "zone": "Cairo"}
        tool_results = [
            {"endpoint": "POST /v1/env_params", "status": "success", "result_summary": "OK"},
            {"endpoint": "POST /v1/satellite", "status": "error", "result_summary": "Rate limit"},
        ]
        report = analyze_failure(error, context, tool_results)
        assert report.failure_type == "tool_error"
        assert any("satellite" in e.lower() for e in report.evidence)

    def test_data_missing(self):
        error = "Key 'heat_index_celsius' not found"
        context = {"phase": "synthesize"}
        report = analyze_failure(error, context)
        assert report.failure_type == "data_missing"

    def test_synthesis_failure(self):
        error = "Synthesis returned no summary"
        context = {"phase": "synthesize"}
        report = analyze_failure(error, context)
        assert report.failure_type == "synthesis_failure"

    def test_delegation_failure(self):
        error = "Sub-agent emergency-coordinator returned empty response"
        context = {"phase": "delegation"}
        report = analyze_failure(error, context)
        assert report.failure_type == "delegation_failure"

    def test_none_error(self):
        context = {"phase": "unknown"}
        report = analyze_failure(None, context)
        assert report.failure_type == "unknown"
        assert report.severity == "P4"

    def test_evidence_includes_query(self):
        error = "timeout"
        context = {"phase": "tool", "query": "Heat in Dubai?", "zone": "Dubai"}
        report = analyze_failure(error, context)
        assert any("Dubai" in e for e in report.evidence)

    def test_blast_radius_for_llm_unavailable(self):
        error = "openai connect error: connection refused"
        context = {"phase": "plan"}
        report = analyze_failure(error, context)
        assert "ChainAgent" in report.blast_radius or "fallback" in report.blast_radius.lower()


class TestRCAToDict:
    def test_to_dict(self):
        report = RCAReport(
            failure_type="api_timeout",
            blast_radius="Tool results incomplete",
            root_cause="API did not respond",
            evidence=["Error: timeout", "Phase: tool execution"],
            recommendation="Increase timeout",
            severity="P2",
        )
        d = rca_to_dict(report)
        assert d["failure_type"] == "api_timeout"
        assert d["severity"] == "P2"
        assert isinstance(d["evidence"], list)
        assert isinstance(d["recommendation"], str)

    def test_to_dict_empty_evidence(self):
        report = RCAReport(
            failure_type="unknown",
            blast_radius="Unknown",
            root_cause="Unknown",
        )
        d = rca_to_dict(report)
        assert d["evidence"] == []


class TestRCAReportDataclass:
    def test_defaults(self):
        report = RCAReport(failure_type="test", blast_radius="none", root_cause="none")
        assert report.evidence == []
        assert report.recommendation == ""
        assert report.severity == "P3"
