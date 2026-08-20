"""Tests for the eval harness (utils/eval_harness.py)."""

from utils.eval_harness import (
    EVAL_CASES,
    EvalCase,
    aggregate_results,
    print_report,
    run_eval,
    score_result,
)


def _make_result(severity="moderate", tools=None, actions=None, recs=None, response="ok"):
    """Helper to build a mock agent result."""
    reasoning = []
    for t in tools or []:
        reasoning.append({"endpoint": f"POST /v1/{t}", "status": "success"})
    if "send_alert" in (actions or []):
        reasoning.append({"action": "Trigger alert", "status": "success"})
    return {
        "severity": severity,
        "recommendations": recs or [],
        "response": response,
        "reasoning": reasoning,
        "actions": actions or [],
    }


class TestEvalCase:
    def test_eval_cases_count(self):
        assert len(EVAL_CASES) == 15

    def test_eval_case_ids_unique(self):
        ids = [c.id for c in EVAL_CASES]
        assert len(ids) == len(set(ids))

    def test_eval_case_categories(self):
        categories = {c.category for c in EVAL_CASES}
        assert "emergency" in categories
        assert "edge" in categories


class TestScoreResult:
    def test_perfect_score(self):
        case = EVAL_CASES[0]  # emergency_01
        result = _make_result(
            severity="extreme",
            tools=["env_params"],
            actions=["send_alert"],
            recs=["Evacuate immediately", "Seek emergency shelter", "Call 911"],
        )
        scores = score_result(result, case)
        assert scores["pass"] is True
        assert scores["severity"] is True
        assert scores["tools"] is True
        assert scores["actions"] is True
        assert scores["recommendations"] is True

    def test_wrong_severity(self):
        case = EVAL_CASES[0]
        result = _make_result(severity="low")
        scores = score_result(result, case)
        assert scores["severity"] is False
        assert scores["pass"] is False

    def test_missing_tools(self):
        case = EVAL_CASES[0]
        result = _make_result(severity="extreme", tools=[])
        scores = score_result(result, case)
        assert scores["tools"] is False
        assert scores["pass"] is False

    def test_insufficient_recommendations(self):
        case = EVAL_CASES[0]  # min_recommendations=3
        result = _make_result(
            severity="extreme",
            tools=["env_params"],
            actions=["send_alert"],
            recs=["one"],
        )
        scores = score_result(result, case)
        assert scores["recommendations"] is False

    def test_no_expected_tools_always_pass(self):
        case = EvalCase(id="custom", query="test", expected_severity="low", expected_tools=[])
        result = _make_result(severity="low")
        scores = score_result(result, case)
        assert scores["tools"] is True

    def test_no_expected_actions_always_pass(self):
        case = EvalCase(id="custom", query="test", expected_severity="low", expected_actions=[])
        result = _make_result(severity="low")
        scores = score_result(result, case)
        assert scores["actions"] is True

    def test_empty_response_fails(self):
        case = EvalCase(id="custom", query="test", expected_severity="low")
        result = _make_result(severity="low", response="")
        scores = score_result(result, case)
        assert scores["has_response"] is False

    def test_alert_detected_from_trace(self):
        case = EvalCase(id="custom", query="test", expected_severity="extreme", expected_actions=["send_alert"])
        result = _make_result(severity="extreme", tools=["env_params"])
        # No send_alert in actions, but Trigger alert in trace
        result["reasoning"].append({"action": "Trigger alert", "status": "success"})
        scores = score_result(result, case)
        assert scores["actions"] is True


class TestAggregateResults:
    def test_all_pass(self):
        results = [
            {"case": EVAL_CASES[0], "scores": {"pass": True, "severity": True}, "latency_ms": 100},
            {"case": EVAL_CASES[1], "scores": {"pass": True, "severity": True}, "latency_ms": 200},
        ]
        agg = aggregate_results(results)
        assert agg["pass_rate"] == 1.0
        assert agg["passed"] == 2

    def test_mixed_results(self):
        results = [
            {"case": EVAL_CASES[0], "scores": {"pass": True, "severity": True}, "latency_ms": 100},
            {"case": EVAL_CASES[1], "scores": {"pass": False, "severity": False}, "latency_ms": 200},
        ]
        agg = aggregate_results(results)
        assert agg["pass_rate"] == 0.5

    def test_empty_results(self):
        agg = aggregate_results([])
        assert agg["total"] == 0
        assert agg["pass_rate"] == 0.0

    def test_by_category(self):
        results = [
            {"case": EVAL_CASES[0], "scores": {"pass": True}, "latency_ms": 100},  # emergency
            {"case": EVAL_CASES[1], "scores": {"pass": False}, "latency_ms": 200},  # emergency
        ]
        agg = aggregate_results(results)
        assert "emergency" in agg["by_category"]
        assert agg["by_category"]["emergency"]["total"] == 2
        assert agg["by_category"]["emergency"]["passed"] == 1

    def test_by_field(self):
        results = [
            {
                "case": EVAL_CASES[0],
                "scores": {"pass": True, "severity": True, "tools": True, "has_response": True},
                "latency_ms": 100,
            },
        ]
        agg = aggregate_results(results)
        assert agg["by_field"]["severity"]["rate"] == 1.0


class TestRunEval:
    def test_run_eval_with_mock_agent(self):
        def mock_agent(query, params):
            return _make_result(
                severity="extreme",
                tools=["env_params"],
                actions=["send_alert"],
                recs=["Evacuate immediately", "Seek shelter", "Call emergency services"],
            )

        results = run_eval(mock_agent, cases=EVAL_CASES[:3])
        assert len(results) == 3
        for r in results:
            assert "scores" in r
            assert "latency_ms" in r

    def test_run_eval_exception_handling(self):
        def failing_agent(query, params):
            raise RuntimeError("Agent crashed")

        results = run_eval(failing_agent, cases=EVAL_CASES[:1])
        assert len(results) == 1
        assert results[0]["scores"]["pass"] is False
        assert "error" in results[0]["result"]

    def test_run_eval_custom_cases(self):
        custom = [EvalCase(id="c1", query="test", expected_severity="low")]
        results = run_eval(lambda q, p: _make_result(severity="low"), cases=custom)
        assert len(results) == 1
        assert results[0]["scores"]["pass"] is True


class TestPrintReport:
    def test_print_report(self, capsys):
        results = [
            {
                "case": EVAL_CASES[0],
                "scores": {"pass": True, "severity": True},
                "latency_ms": 50,
                "result": _make_result(severity="extreme"),
            },
        ]
        report = print_report(results)
        assert "HeatMind Eval Report" in report
        assert "PASS" in report
        captured = capsys.readouterr()
        assert "HeatMind Eval Report" in captured.out
