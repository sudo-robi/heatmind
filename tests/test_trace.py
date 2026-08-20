"""Tests for utils/trace.py - Structured Evidence Trail."""

from utils.trace import Trace, TraceCollector


def test_trace_collector_record():
    tc = TraceCollector()
    t = Trace(trace_id="tr_test1", query="test query")
    t.complete(outcome="success", confidence=0.8, severity="moderate")
    tc.record(t)
    assert len(tc._traces) == 1


def test_trace_collector_stats():
    tc = TraceCollector()
    t = Trace(trace_id="tr_test1", query="test query")
    t.add_span(phase="fetch", cost_usd=0.01)
    t.complete(outcome="success", confidence=0.8, severity="moderate")
    tc.record(t)
    stats = tc.stats()
    assert stats["total"] == 1
    assert stats["avg_confidence"] == 0.8
    assert stats["avg_cost"] == 0.01


def test_trace_collector_get_all():
    tc = TraceCollector()
    for i in range(5):
        t = Trace(trace_id=f"tr_{i}", query=f"query_{i}")
        t.complete(outcome="success", confidence=0.8, severity="low")
        tc.record(t)
    assert len(tc.get_all(limit=3)) == 3
    assert len(tc.get_all(limit=10)) == 5


def test_trace_complete_calculates_cost():
    t = Trace(trace_id="tr_test", query="test")
    t.add_span(phase="fetch", cost_usd=0.01)
    t.add_span(phase="analyze", cost_usd=0.02)
    t.complete(outcome="success", confidence=0.9, severity="low")
    assert t.total_cost_usd == 0.03
    assert len(t.spans) == 2


def test_trace_to_dict():
    t = Trace(trace_id="tr_test", query="test query", zone="Dubai")
    t.complete(outcome="success", confidence=0.85, severity="high")
    d = t.to_dict()
    assert d["trace_id"] == "tr_test"
    assert d["query"] == "test query"
    assert d["zone"] == "Dubai"
    assert d["outcome"] == "success"
    assert d["confidence"] == 0.85
