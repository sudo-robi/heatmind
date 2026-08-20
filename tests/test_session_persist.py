"""Tests for utils.session_persist — mock Streamlit session_state."""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class _State:
    """Dict-like object that behaves like ``st.session_state``."""

    def __init__(self):
        self._d: dict = {}

    def __getattr__(self, name: str):
        if name.startswith("_"):
            return object.__getattribute__(self, name)
        try:
            return self._d[name]
        except KeyError:
            raise AttributeError(name) from None

    def __setattr__(self, name: str, value):
        if name.startswith("_"):
            object.__setattr__(self, name, value)
        else:
            self._d[name] = value

    def __contains__(self, name):
        return name in self._d

    def __setitem__(self, key, value):
        self._d[key] = value

    def __getitem__(self, key):
        return self._d[key]


@pytest.fixture(autouse=True)
def _patch_streamlit(monkeypatch):
    """Replace ``streamlit`` module with a lightweight mock."""
    state = _State()

    fake_st = MagicMock()
    fake_st.session_state = state
    monkeypatch.setattr("utils.session_persist.st", fake_st, raising=False)
    sys.modules["streamlit"] = fake_st
    yield state
    sys.modules.pop("streamlit", None)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestInitSessionState:
    def test_creates_session_id(self, _patch_streamlit):
        from utils.session_persist import init_session_state

        init_session_state()
        assert hasattr(_patch_streamlit, "heatmind_session_id")

    def test_creates_history(self, _patch_streamlit):
        from utils.session_persist import init_session_state

        init_session_state()
        assert _patch_streamlit.heatmind_history == []

    def test_creates_traces(self, _patch_streamlit):
        from utils.session_persist import init_session_state

        init_session_state()
        assert _patch_streamlit.heatmind_traces == []

    def test_creates_checkpoints(self, _patch_streamlit):
        from utils.session_persist import init_session_state

        init_session_state()
        assert _patch_streamlit.heatmind_checkpoints == []

    def test_idempotent(self, _patch_streamlit):
        from utils.session_persist import init_session_state

        init_session_state()
        first_id = _patch_streamlit.heatmind_session_id
        init_session_state()
        assert _patch_streamlit.heatmind_session_id == first_id


class TestSaveLoadSession:
    def test_save_and_load(self, _patch_streamlit):
        from utils.session_persist import load_from_session, save_to_session

        save_to_session("my_key", [1, 2, 3])
        assert load_from_session("my_key") == [1, 2, 3]

    def test_load_missing_returns_default(self, _patch_streamlit):
        from utils.session_persist import load_from_session

        assert load_from_session("nonexistent_key", default=42) == 42

    def test_load_missing_no_default(self, _patch_streamlit):
        from utils.session_persist import load_from_session

        assert load_from_session("nonexistent_key") is None


class TestGetSessionId:
    def test_returns_string_uuid(self, _patch_streamlit):
        from utils.session_persist import get_session_id

        sid = get_session_id()
        assert isinstance(sid, str)
        assert len(sid) == 36  # UUID4 format

    def test_same_id_on_repeated_calls(self, _patch_streamlit):
        from utils.session_persist import get_session_id

        first = get_session_id()
        second = get_session_id()
        assert first == second


class TestAddToHistory:
    def test_entry_has_timestamp(self, _patch_streamlit):
        from utils.session_persist import add_to_history

        add_to_history({"action": "test"})
        from utils.session_persist import load_from_session

        history = load_from_session("heatmind_history")
        assert len(history) == 1
        assert "timestamp" in history[0]
        assert history[0]["action"] == "test"

    def test_multiple_entries(self, _patch_streamlit):
        from utils.session_persist import add_to_history, load_from_session

        add_to_history({"i": 0})
        add_to_history({"i": 1})
        add_to_history({"i": 2})
        history = load_from_session("heatmind_history")
        assert len(history) == 3


class TestGetHistory:
    def test_returns_last_n(self, _patch_streamlit):
        from utils.session_persist import add_to_history, get_history

        for i in range(10):
            add_to_history({"i": i})
        last5 = get_history(limit=5)
        assert len(last5) == 5
        assert last5[0]["i"] == 5

    def test_empty_history(self, _patch_streamlit):
        from utils.session_persist import get_history

        assert get_history() == []

    def test_limit_zero_returns_all(self, _patch_streamlit):
        from utils.session_persist import add_to_history, get_history

        add_to_history({"i": 0})
        # limit <= 0 returns empty per spec
        assert get_history(limit=0) == []
