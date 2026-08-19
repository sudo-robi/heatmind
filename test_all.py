#!/usr/bin/env python3
"""HeatMind end-to-end smoke test — runs every subsystem without external deps."""

import os
import sys

# Set API key before any project imports (must override conftest.py default)
os.environ["FORTYGUARD_API_KEY"] = "test-smoke-key"

import json
import time
from unittest.mock import MagicMock, patch

PASS = 0
FAIL = 0


def check(label, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"  ✅ {label}")
    else:
        FAIL += 1
        print(f"  ❌ {label}  {detail}")


def section(title):
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


# ── 1. Config ────────────────────────────────────────────────────────
section("1. CONFIG")
import config

check("FORTYGUARD_BASE_URL set", config.FORTYGUARD_BASE_URL == "https://api.fortyguard.com/v1")
check("HEAT_THRESHOLD_C is float", isinstance(config.HEAT_THRESHOLD_C, float))
check("HEAT_INDEX_THRESHOLD is float", isinstance(config.HEAT_INDEX_THRESHOLD, float))
check("MONITOR_INTERVAL_MINUTES is int", isinstance(config.MONITOR_INTERVAL_MINUTES, int))


# ── 2. NLP Parser ────────────────────────────────────────────────────
section("2. NLP PARSER")
from agents.nlp_parser import (
    ParsedQuery,
    classify_intent,
    extract_date,
    extract_location,
    extract_time,
    parse_query,
)

loc, lat, lon = extract_location("What's the temperature in Miami?")
check("Extract Miami", loc == "miami" and lat is not None, f"got {loc}")

loc, lat, lon = extract_location("temperature in LA today")
check("Extract LA (short city)", loc == "la", f"got {loc}")

loc, lat, lon = extract_location("temperature in latitude 33.5 longitude -112")
check("Extract coordinates", loc == "custom" and lat == 33.5, f"got {loc}, {lat}, {lon}")

loc, lat, lon = extract_location("random text")
check("No location found", loc is None)

intent, conf = classify_intent("What's the temperature in Miami?")
check("Intent: current_conditions", intent == "current_conditions", f"got {intent}")

intent, conf = classify_intent("emergency extreme heat")
check("Intent: emergency", intent == "emergency", f"got {intent}")

intent, conf = classify_intent("comprehensive heat analysis")
check("Intent: analysis", intent == "analysis", f"got {intent}")

intent, conf = classify_intent("compare cities")
check("Intent: comparison", intent == "comparison", f"got {intent}")

intent, conf = classify_intent("random unrelated text")
check("Default intent fallback", intent == "current_conditions")

date = extract_date("What's the temperature today?")
check("Date: today", date is not None)

date = extract_date("temperature tomorrow")
check("Date: tomorrow", date is not None)

date = extract_date("2026-08-15 temperature")
check("Date: explicit", date == "2026-08-15", f"got {date}")

time_str = extract_time("temperature at 3 pm")
check("Time: 3pm", time_str == "15:00", f"got {time_str}")

time_str = extract_time("temperature at 14:30")
check("Time: 14:30", time_str == "14:30", f"got {time_str}")

time_str = extract_time("morning temperature")
check("Time: morning", time_str == "08:00", f"got {time_str}")

pq = parse_query("What's the temperature in Miami today at 3pm?")
check("ParsedQuery has intent", pq.intent == "current_conditions")
check("ParsedQuery has location", pq.location == "miami")
check("ParsedQuery has date", pq.date is not None)
check("ParsedQuery has time", pq.time == "15:00")
check("ParsedQuery has endpoints", len(pq.endpoints_needed) > 0)
check("ParsedQuery confidence > 0", pq.confidence > 0)

check("ALL_CITIES dict not empty", len(__import__("utils.cities", fromlist=["ALL_CITIES"]).ALL_CITIES) > 10)


# ── 3. Router ────────────────────────────────────────────────────────
section("3. ROUTER")
from agents.router import (
    QueryComplexity,
    QueryUrgency,
    classify_complexity,
    classify_urgency,
    route_query,
)

c = classify_complexity("What's the temperature right now?")
check("Simple query classified", c == QueryComplexity.SIMPLE, f"got {c}")

c = classify_complexity("comprehensive deep dive risk assessment")
check("Complex query classified", c == QueryComplexity.COMPLEX, f"got {c}")

u = classify_urgency("emergency dangerous extreme")
check("Critical urgency", u == QueryUrgency.CRITICAL, f"got {u}")

u = classify_urgency("show me overview")
check("Low urgency", u == QueryUrgency.LOW, f"got {u}")

dec = route_query("What's the temperature in Miami?")
check("Route simple → quick agent", dec.agent == "quick", f"got {dec.agent}")

dec = route_query("emergency extreme heat danger")
check("Route emergency → emergency agent", dec.agent == "emergency", f"got {dec.agent}")

dec = route_query("comprehensive deep dive analysis")
check("Route complex → deep agent", dec.agent == "deep", f"got {dec.agent}")

check("RoutingDecision has confidence", dec.confidence > 0)


# ── 4. Validation ────────────────────────────────────────────────────
section("4. VALIDATION")
from utils.validation import flatten_location_data, validate_coords

validate_coords(33.5, -112.0)
check("Valid coords pass", True)

try:
    validate_coords(100, -112)
    check("Invalid lat raises", False)
except ValueError:
    check("Invalid lat raises ValueError", True)

data = {"locations": [{"parameters": {"heat_index_celsius": [35.0], "humidity": [60]}}]}
flat = flatten_location_data(data)
check(
    "flatten_location_data flattens API format",
    flat["heat_index_celsius"] == 35.0 and flat["humidity"] == 60,
    f"got {flat}",
)

data2 = {"heat_index_celsius": 35.0, "nested": {"key": "val"}}
flat2 = flatten_location_data(data2)
check("flatten leaves non-API dicts as-is", flat2["heat_index_celsius"] == 35.0)


# ── 5. Session Memory (in-memory) ───────────────────────────────────
section("5. SESSION MEMORY")
from memory.session import SessionMemory

mem = SessionMemory()
sid = mem.create_session("test_user")
check("Session created", sid is not None and len(sid) > 0)

sess = mem.get_session(sid)
check("Session retrievable", sess is not None)
check("Session has messages array", "messages" in sess)

mem.add_message(sid, "user", "hello")
mem.add_message(sid, "assistant", "hi there")
msgs = mem.get_messages(sid)
check("Messages stored", len(msgs) == 2, f"got {len(msgs)}")
check("Message has role", msgs[0]["role"] == "user")
check("Message has content", msgs[0]["content"] == "hello")

mem.add_message_bulk(sid, [("user", "a"), ("assistant", "b"), ("user", "c")])
msgs = mem.get_messages(sid)
check("Bulk add works", len(msgs) == 5, f"got {len(msgs)}")

mem.update_session_context(sid, "last_query", "test query")
ctx = mem.get_session_context(sid)
check("Context updated", ctx.get("last_query") == "test query")

mem.log_decision(sid, "test", decision="quick", reasoning="test", outcome="completed")
decisions = mem.get_recent_decisions(sid)
check("Decision logged", len(decisions) >= 1)

mem.log_event(sid, "heat_reading", {"zone": "test", "temp": 42})
events = mem.get_events(sid)
check("Event logged", len(events) >= 1)

check("Session not expired", not mem.is_session_expired(sid))


# ── 6. API Client (mocked) ──────────────────────────────────────────
section("6. API CLIENT")
from api.fortyguard import FortyGuardClient

c = FortyGuardClient(api_key="test_key")
check("Client instantiation", c.api_key == "test_key")

c._session = MagicMock()

resp = MagicMock()
resp.json.return_value = {"data": {"activity_id": "env-123"}}
resp.raise_for_status = MagicMock()
c._session.post.return_value = resp
aid = c.create_env_params(latitude=33.5, longitude=-112, temperature=35, start_date="2026-08-19")
check("create_env_params returns activity_id", aid == "env-123")

resp.json.return_value = {"data": {"activity_id": "hm-456"}}
aid = c.create_heatmap(polygon_aoi={"type": "FeatureCollection", "features": []}, start_date="2026-08-19")
check("create_heatmap returns activity_id", aid == "hm-456")

resp.json.return_value = {"data": {"activity_id": "sat-789"}}
aid = c.create_satellite(latitude=33.5, longitude=-112, start_date="2026-08-19")
check("create_satellite returns activity_id", aid == "sat-789")

resp.json.return_value = {"data": {"activity_id": "sv-012"}}
aid = c.create_streetview(latitude=33.5, longitude=-112)
check("create_streetview returns activity_id", aid == "sv-012")

resp.json.return_value = {"data": {"activity_id": "intel-345"}}
aid = c.create_heat_intelligence(latitude=33.5, longitude=-112, temperature=42, date="2026-08-19", analysis=["urban"])
check("create_heat_intelligence returns activity_id", aid == "intel-345")

get_resp = MagicMock()
get_resp.json.return_value = {"data": {"status": "completed", "result": {"temp": 42}}}
get_resp.raise_for_status = MagicMock()
c._session.get.return_value = get_resp
result = c.wait_for_result("act-123", timeout=5, poll_interval=0.01)
check("wait_for_result returns result", result == {"temp": 42})

check("get_call_log works", isinstance(c.get_call_log(), list))


# ── 7. Agents (mocked) ──────────────────────────────────────────────
section("7. AGENTS")
from agents.quick_agent import QuickAgent
from agents.deep_agent import DeepAgent
from agents.emergency_agent import EmergencyAgent
from agents.chain_agent import ChainAgent

qa = QuickAgent(memory=mem)
check("QuickAgent instantiated", qa is not None)

with (
    patch.object(qa.api, "create_env_params", return_value="env-test"),
    patch.object(qa.api, "wait_for_result", return_value={"heat_index_celsius": 38}),
):
    result = qa.handle("What's the temperature?", sid, {"latitude": 33.5, "longitude": -112, "date": "2026-08-19"})
    check("QuickAgent returns result", "agent" in result and result["agent"] == "quick")

da = DeepAgent(memory=mem)
check("DeepAgent instantiated", da is not None)

with (
    patch.object(da.api, "create_env_params", return_value="env-test"),
    patch.object(da.api, "wait_for_result", return_value={"heat_index_celsius": 38}),
    patch.object(da.api, "create_heat_intelligence", return_value="intel-test"),
    patch.object(da.api, "get_call_log", return_value=[]),
):
    result = da.handle("comprehensive analysis", sid, {"latitude": 33.5, "longitude": -112, "date": "2026-08-19"})
    check("DeepAgent returns result", "agent" in result and result["agent"] == "deep")

ea = EmergencyAgent(memory=mem)
check("EmergencyAgent instantiated", ea is not None)

with (
    patch.object(ea.api, "create_env_params", return_value="env-test"),
    patch.object(ea.api, "wait_for_result", return_value={"heat_index_celsius": 50}),
    patch.object(ea.api, "get_call_log", return_value=[]),
):
    result = ea.handle("emergency heat!", sid, {"latitude": 33.5, "longitude": -112, "date": "2026-08-19"})
    check("EmergencyAgent returns result", "agent" in result and result["agent"] == "emergency")

ca = ChainAgent(memory=mem)
check("ChainAgent instantiated", ca is not None)


# ── 8. Datasets ──────────────────────────────────────────────────────
section("8. DATASETS")
from utils.datasets import get_location_context, format_location_context

ctx = get_location_context(33.45, -112.07)
check("LocationContext for Phoenix", ctx is not None and hasattr(ctx, "population_density"))
check("LocationContext has risk_score", hasattr(ctx, "risk_score"))

fmt = format_location_context(ctx)
check("format_location_context returns string", isinstance(fmt, str) and len(fmt) > 0)


# ── 9. Alerts (mocked) ──────────────────────────────────────────────
section("9. ALERTS")
from utils.alerts import send_alert, send_console_alert

payload = {"severity": "warning", "zone": "test", "heat_index": 40, "recommendations": ["stay hydrated"]}
send_console_alert(payload)
check("send_console_alert runs without error", True)

with patch("utils.alerts.requests.post") as mock_post:
    mock_post.return_value = MagicMock(status_code=200, raise_for_status=MagicMock())
    import utils.alerts as _alerts

    _alerts.SLACK_WEBHOOK_URL = "https://hooks.slack.com/test"
    _alerts.send_slack_alert(payload)
    check("send_slack_alert fires POST", mock_post.called)
    _alerts.SLACK_WEBHOOK_URL = ""


# ── 10. Streamlit app imports ────────────────────────────────────────
section("10. STREAMLIT APP")
import importlib

spec = importlib.util.find_spec("streamlit_app")
check("streamlit_app module found", spec is not None)


# ── 11. MCP Client ──────────────────────────────────────────────────
section("11. MCP CLIENT")
from utils.mcp_client import HeatMindMCPClient, _validate_mcp_tool_args

mc = HeatMindMCPClient()
check("HeatMindMCPClient instantiation", mc is not None)

err = _validate_mcp_tool_args("query_heat_conditions", {"latitude": 33.5, "longitude": -112, "date": "2026-08-19"})
check("Valid MCP request passes", err is None)

err = _validate_mcp_tool_args("query_heat_conditions", {})
check("Missing MCP params fails", err is not None)


# ── 12. Monitor Loop ────────────────────────────────────────────────
section("12. MONITOR LOOP")
from monitor.loop import MonitorLoop

ml = MonitorLoop(memory=mem)
check("MonitorLoop instantiated", ml is not None)

ml.add_zone("test_zone", {"type": "FeatureCollection", "features": []}, 33.5, -112)
check("Zone added", len(ml.zones) == 1)

reading = {
    "zone": "test",
    "env_params": {"heat_index_celsius": 38},
    "heatmap": {"stats_data": {"Temperature_stats": {"Maximum": 38}}},
}
check("analyze_reading normal", ml.analyze_reading(reading) is False)

reading_hot = {
    "zone": "test",
    "env_params": {"heat_index_celsius": 50},
    "heatmap": {"stats_data": {"Temperature_stats": {"Maximum": 50}}},
}
check("analyze_reading alert", ml.analyze_reading(reading_hot) is True)


# ── SUMMARY ──────────────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"  RESULTS: {PASS} passed, {FAIL} failed, {PASS + FAIL} total")
print(f"{'=' * 60}")
if __name__ == "__main__":
    sys.exit(0 if FAIL == 0 else 1)
