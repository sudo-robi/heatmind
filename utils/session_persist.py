"""Session persistence for Streamlit reruns.

Streamlit reruns the entire script on every interaction. This module persists
agent session state across refreshes using ``st.session_state``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any


def init_session_state() -> None:
    """Initialize all HeatMind session state keys in ``st.session_state``."""
    import streamlit as st

    if "heatmind_session_id" not in st.session_state:
        st.session_state.heatmind_session_id = str(uuid.uuid4())
    if "heatmind_history" not in st.session_state:
        st.session_state.heatmind_history = []
    if "heatmind_traces" not in st.session_state:
        st.session_state.heatmind_traces = []
    if "heatmind_checkpoints" not in st.session_state:
        st.session_state.heatmind_checkpoints = []


def save_to_session(key: str, value: Any) -> None:
    """Persist *value* under *key* in Streamlit session state."""
    import streamlit as st

    st.session_state[key] = value


def load_from_session(key: str, default: Any = None) -> Any:
    """Load a value from session state, returning *default* if absent."""
    import streamlit as st

    return getattr(st.session_state, key, default)


def get_session_id() -> str:
    """Return the current session UUID (created on first call)."""
    import streamlit as st

    if "heatmind_session_id" not in st.session_state:
        st.session_state.heatmind_session_id = str(uuid.uuid4())
    return st.session_state.heatmind_session_id


def add_to_history(entry: dict) -> None:
    """Append a timestamped *entry* to the session history list."""
    import streamlit as st

    if "heatmind_history" not in st.session_state:
        st.session_state.heatmind_history = []
    stamped = {"timestamp": datetime.now(UTC).isoformat(), **entry}
    st.session_state.heatmind_history.append(stamped)


def get_history(limit: int = 50) -> list[dict]:
    """Return the last *limit* history entries (most recent last)."""
    import streamlit as st

    history = getattr(st.session_state, "heatmind_history", [])
    return history[-limit:] if limit > 0 else []
