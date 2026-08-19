"""Tests for auto-append history middleware."""

from utils.middleware import AgentContext, HistoryMiddleware


class MockMemory:
    def __init__(self):
        self.messages = {}

    def get_messages(self, session_id):
        return self.messages.get(session_id, [])

    def add_message(self, session_id, role, content):
        if session_id not in self.messages:
            self.messages[session_id] = []
        self.messages[session_id].append({"role": role, "content": content})


class TestHistoryMiddleware:
    def test_enrich_context_returns_agent_context(self):
        memory = MockMemory()
        mw = HistoryMiddleware(memory)
        result = mw.enrich_context("session1", "test query")
        assert isinstance(result, AgentContext)
        assert result.query == "test query"
        assert result.session_id == "session1"

    def test_enrich_context_includes_history(self):
        memory = MockMemory()
        memory.add_message("session1", "user", "prev query")
        memory.add_message("session1", "assistant", "prev response")
        mw = HistoryMiddleware(memory)
        result = mw.enrich_context("session1", "new query")
        assert len(result.history) == 2

    def test_enrich_context_empty_session(self):
        memory = MockMemory()
        mw = HistoryMiddleware(memory)
        result = mw.enrich_context("session1", "new query")
        assert result.history == []

    def test_record_interaction(self):
        memory = MockMemory()
        mw = HistoryMiddleware(memory)
        mw.record_interaction("session1", "user query", "agent response")
        messages = memory.get_messages("session1")
        assert len(messages) == 2
        assert messages[0]["role"] == "user"
        assert messages[1]["role"] == "assistant"

    def test_format_history_for_prompt(self):
        memory = MockMemory()
        memory.add_message("session1", "user", "query1")
        memory.add_message("session1", "assistant", "response1")
        mw = HistoryMiddleware(memory)
        context = mw.enrich_context("session1", "new query")
        prompt = mw.format_history_for_prompt(context)
        assert "Previous conversation context:" in prompt
        assert "query1" in prompt

    def test_format_history_empty(self):
        memory = MockMemory()
        mw = HistoryMiddleware(memory)
        context = mw.enrich_context("session1", "new query")
        prompt = mw.format_history_for_prompt(context)
        assert prompt == ""

    def test_max_history_limit(self):
        memory = MockMemory()
        for i in range(5):
            memory.add_message("session1", "user", f"query{i}")
        mw = HistoryMiddleware(memory, max_history=3)
        result = mw.enrich_context("session1", "new query")
        assert len(result.history) == 3

    def test_metadata_includes_history_count(self):
        memory = MockMemory()
        memory.add_message("session1", "user", "query1")
        mw = HistoryMiddleware(memory)
        result = mw.enrich_context("session1", "new query")
        assert result.metadata["history_count"] == 1

    def test_empty_session_id(self):
        memory = MockMemory()
        mw = HistoryMiddleware(memory)
        result = mw.enrich_context("", "new query")
        assert result.history == []
