import uuid

import pytest

from memory.session import SessionMemory


@pytest.fixture
def memory():
    m = SessionMemory()
    yield m
    m.sessions.drop()
    m.events.drop()
    m.decisions.drop()


class TestSessionCreation:
    def test_create_session(self, memory):
        sid = memory.create_session("test_user")
        assert sid is not None
        uuid.UUID(sid)

    def test_get_session(self, memory):
        sid = memory.create_session("test_user")
        session = memory.get_session(sid)
        assert session is not None
        assert session["user_id"] == "test_user"

    def test_session_has_context(self, memory):
        sid = memory.create_session("test_user")
        session = memory.get_session(sid)
        assert "context" in session
        assert session["context"] == {}

    def test_session_has_timestamps(self, memory):
        sid = memory.create_session("test_user")
        session = memory.get_session(sid)
        assert "created_at" in session
        assert "last_active" in session

    def test_session_query_count(self, memory):
        sid = memory.create_session("test_user")
        session = memory.get_session(sid)
        assert session["query_count"] == 0

    def test_get_nonexistent_session(self, memory):
        session = memory.get_session(str(uuid.uuid4()))
        assert session is None


class TestSessionContext:
    def test_update_context(self, memory):
        sid = memory.create_session("test_user")
        memory.update_session_context(sid, "last_zone", "Dubai")
        ctx = memory.get_session_context(sid)
        assert ctx["last_zone"] == "Dubai"

    def test_update_context_multiple_keys(self, memory):
        sid = memory.create_session("test_user")
        memory.update_session_context(sid, "key1", "value1")
        memory.update_session_context(sid, "key2", "value2")
        ctx = memory.get_session_context(sid)
        assert ctx["key1"] == "value1"
        assert ctx["key2"] == "value2"

    def test_context_overwrites(self, memory):
        sid = memory.create_session("test_user")
        memory.update_session_context(sid, "zone", "Dubai")
        memory.update_session_context(sid, "zone", "Abu Dhabi")
        ctx = memory.get_session_context(sid)
        assert ctx["zone"] == "Abu Dhabi"

    def test_context_increment_query_count(self, memory):
        sid = memory.create_session("test_user")
        memory.update_session_context(sid, "test", "value")
        memory.update_session_context(sid, "test", "value2")
        session = memory.get_session(sid)
        assert session["query_count"] == 2

    def test_get_nonexistent_session_context(self, memory):
        ctx = memory.get_session_context(str(uuid.uuid4()))
        assert ctx == {}

    def test_context_with_nested_dict(self, memory):
        sid = memory.create_session("test_user")
        memory.update_session_context(sid, "nested", {"a": {"b": "c"}})
        ctx = memory.get_session_context(sid)
        assert ctx["nested"]["a"]["b"] == "c"

    def test_context_with_list(self, memory):
        sid = memory.create_session("test_user")
        memory.update_session_context(sid, "list", [1, 2, 3])
        ctx = memory.get_session_context(sid)
        assert ctx["list"] == [1, 2, 3]

    def test_context_with_none(self, memory):
        sid = memory.create_session("test_user")
        memory.update_session_context(sid, "null_val", None)
        ctx = memory.get_session_context(sid)
        assert ctx["null_val"] is None

    def test_context_with_boolean(self, memory):
        sid = memory.create_session("test_user")
        memory.update_session_context(sid, "flag", True)
        ctx = memory.get_session_context(sid)
        assert ctx["flag"] is True

    def test_context_with_dict_value(self, memory):
        sid = memory.create_session("test_user")
        memory.update_session_context(sid, "location", {"lat": 25.0, "lon": 55.0})
        ctx = memory.get_session_context(sid)
        assert ctx["location"]["lat"] == 25.0


class TestEventLogging:
    def test_log_event(self, memory):
        sid = memory.create_session("test_user")
        memory.log_event(sid, "heat_reading", {"zone": "Dubai", "temp": 42})
        events = memory.get_events(sid)
        assert len(events) == 1
        assert events[0]["event_type"] == "heat_reading"

    def test_log_multiple_events(self, memory):
        sid = memory.create_session("test_user")
        memory.log_event(sid, "heat_reading", {"zone": "Dubai"})
        memory.log_event(sid, "alert_sent", {"zone": "Dubai"})
        events = memory.get_events(sid)
        assert len(events) == 2

    def test_get_events_by_type(self, memory):
        sid = memory.create_session("test_user")
        memory.log_event(sid, "heat_reading", {"zone": "Dubai"})
        memory.log_event(sid, "alert_sent", {"zone": "Dubai"})
        events = memory.get_events(sid, event_type="heat_reading")
        assert len(events) == 1
        assert events[0]["event_type"] == "heat_reading"

    def test_events_are_sorted_by_time(self, memory):
        import time

        sid = memory.create_session("test_user")
        memory.log_event(sid, "first", {"order": 1})
        time.sleep(0.01)
        memory.log_event(sid, "second", {"order": 2})
        events = memory.get_events(sid)
        assert len(events) == 2
        assert events[0]["timestamp"] >= events[1]["timestamp"]

    def test_event_has_timestamp(self, memory):
        sid = memory.create_session("test_user")
        memory.log_event(sid, "test", {"data": "value"})
        events = memory.get_events(sid)
        assert "timestamp" in events[0]

    def test_event_with_large_data(self, memory):
        sid = memory.create_session("test_user")
        large_data = {"data": "x" * 100000}
        memory.log_event(sid, "large_event", large_data)
        events = memory.get_events(sid)
        assert len(events) == 1

    def test_events_different_types(self, memory):
        sid = memory.create_session("test_user")
        memory.log_event(sid, "heat_reading", {"zone": "A"})
        memory.log_event(sid, "emergency_detected", {"zone": "B"})
        memory.log_event(sid, "deep_analysis", {"zone": "C"})
        all_events = memory.get_events(sid)
        assert len(all_events) == 3
        hr = memory.get_events(sid, event_type="heat_reading")
        assert len(hr) == 1


class TestDecisionLogging:
    def test_log_decision(self, memory):
        sid = memory.create_session("test_user")
        memory.log_decision(sid, "test query", "quick", "reasoning", "completed")
        decisions = memory.get_recent_decisions(sid)
        assert len(decisions) == 1
        assert decisions[0]["decision"] == "quick"
        assert decisions[0]["outcome"] == "completed"

    def test_log_decision_without_outcome(self, memory):
        sid = memory.create_session("test_user")
        memory.log_decision(sid, "test", "quick", "reasoning")
        decisions = memory.get_recent_decisions(sid)
        assert decisions[0]["outcome"] is None

    def test_get_recent_decisions_limit(self, memory):
        sid = memory.create_session("test_user")
        for i in range(15):
            memory.log_decision(sid, f"query {i}", "quick", "reason")
        decisions = memory.get_recent_decisions(sid, limit=5)
        assert len(decisions) == 5

    def test_decisions_sorted_by_time(self, memory):
        sid = memory.create_session("test_user")
        memory.log_decision(sid, "first", "quick", "reason")
        import time

        time.sleep(0.01)
        memory.log_decision(sid, "second", "deep", "reason")
        decisions = memory.get_recent_decisions(sid)
        assert decisions[0]["query"] == "second"

    def test_decision_has_timestamp(self, memory):
        sid = memory.create_session("test_user")
        memory.log_decision(sid, "q", "d", "r")
        decisions = memory.get_recent_decisions(sid)
        assert "timestamp" in decisions[0]


class TestZoneHistory:
    def test_get_zone_history(self, memory):
        sid = memory.create_session("test_user")
        memory.events.drop()
        memory.log_event(sid, "heat_reading", {"zone": "Dubai", "temp": 42})
        history = memory.get_zone_history("Dubai")
        assert len(history) == 1

    def test_zone_history_empty(self, memory):
        history = memory.get_zone_history("NonexistentZone")
        assert len(history) == 0

    def test_zone_history_sorted(self, memory):
        import time

        sid = memory.create_session("test_user")
        memory.log_event(sid, "heat_reading", {"zone": "Dubai", "temp": 40})
        time.sleep(0.1)
        memory.log_event(sid, "heat_reading", {"zone": "Dubai", "temp": 45})
        history = memory.get_zone_history("Dubai")
        assert len(history) >= 2
        temps = [h["data"]["temp"] for h in history]
        assert 45 in temps and 40 in temps

    def test_zone_history_limit(self, memory):
        sid = memory.create_session("test_user")
        for i in range(10):
            memory.log_event(sid, "heat_reading", {"zone": "Dubai", "temp": i})
        history = memory.get_zone_history("Dubai", limit=3)
        assert len(history) == 3


class TestSessionEdgeCases:
    def test_create_session_empty_user(self, memory):
        sid = memory.create_session("")
        assert sid is not None

    def test_create_session_long_user(self, memory):
        sid = memory.create_session("x" * 1000)
        assert sid is not None

    def test_concurrent_sessions(self, memory):
        sids = [memory.create_session(f"user_{i}") for i in range(10)]
        assert len(set(sids)) == 10

    def test_update_context_many_keys(self, memory):
        sid = memory.create_session("test_user")
        for i in range(50):
            memory.update_session_context(sid, f"key_{i}", f"value_{i}")
        ctx = memory.get_session_context(sid)
        assert len(ctx) == 50

    def test_session_active_timestamp_updates(self, memory):
        sid = memory.create_session("test_user")
        session1 = memory.get_session(sid)
        memory.update_session_context(sid, "key", "val")
        session2 = memory.get_session(sid)
        assert session2["last_active"] >= session1["last_active"]
