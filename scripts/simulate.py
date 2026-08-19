#!/usr/bin/env python3
"""HeatMind Daily Simulator — populates real data via FortyGuard API.

Runs once per day, creates realistic user sessions with queries routed
through the actual agents. Generates alerts, events, and decisions.

Usage:
    python scripts/simulate.py              # single run
    python scripts/simulate.py --dry-run    # show what would run, no API calls
    python scripts/simulate.py --sessions 3 # custom session count
"""

import argparse
import logging
import random
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from agents.deep_agent import DeepAgent
from agents.emergency_agent import EmergencyAgent
from agents.quick_agent import QuickAgent
from agents.router import route_query
from memory.session import SessionMemory

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# ── Zones ────────────────────────────────────────────────────────────────────
ZONES = [
    {"name": "Dubai Downtown", "lat": 25.2048, "lng": 55.2708, "temp_base": 42},
    {"name": "Abu Dhabi Central", "lat": 24.4539, "lng": 54.3773, "temp_base": 40},
    {"name": "Sharjah City", "lat": 25.3463, "lng": 55.4209, "temp_base": 41},
    {"name": "Phoenix, AZ", "lat": 33.4484, "lng": -112.0740, "temp_base": 38},
    {"name": "Riyadh, SA", "lat": 24.7136, "lng": 46.6753, "temp_base": 44},
]

# ── Query templates by type ──────────────────────────────────────────────────
SIMPLE_QUERIES = [
    "What's the temperature in {city}?",
    "What's the heat index in {city} right now?",
    "How's the humidity in {city} today?",
    "What's the current AQI in {city}?",
    "Is it hot in {city}?",
    "What's the weather like in {city}?",
    "Show me the heat conditions for {city}",
    "What's the apparent temperature in {city}?",
]

MODERATE_QUERIES = [
    "Compare the heat between {city} and {city2}",
    "What's the heat trend for {city} this week?",
    "Give me a report on heat conditions in {city}",
    "How does {city} compare to {city2} for heat risk?",
    "What's the forecast for {city}?",
    "Analyze the heat patterns in {city}",
]

COMPLEX_QUERIES = [
    "Give me a full heat risk assessment for {city}",
    "Deep dive into the heat conditions for {city} — environmental and urban factors",
    "Comprehensive heat intelligence report for {city}",
    "Multi-dimensional analysis of heat risk in {city} — satellite and ground truth",
    "Full assessment of heat exposure for outdoor workers in {city}",
]

EMERGENCY_QUERIES = [
    "EMERGENCY: Workers collapsing in {city} from heat!",
    "DANGER: Extreme heat hazard in {city} — need immediate assessment",
    "URGENT: Heat index exceeding safe limits in {city}!",
    "CRITICAL: Outdoor workers showing heat stroke symptoms in {city}",
    "Alert: Dangerous heat conditions detected in {city} — activate emergency protocols",
    "Emergency: {city} hit by extreme heat wave — evacuate outdoor workers now",
]

FOLLOW_UP_QUERIES = [
    "What about tomorrow?",
    "How does that compare to last week?",
    "Should I be concerned?",
    "Start monitoring this location",
    "What are the recommended actions?",
    "Is this getting worse?",
    "What's the heat index for the next few hours?",
    "Compare this to {city2}",
]


def build_polygon(lat: float, lng: float, size: float = 0.05) -> dict:
    """Build a simple square polygon around a point."""
    return {
        "type": "FeatureCollection",
        "features": [
            {
                "type": "Feature",
                "properties": {},
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [lng - size, lat - size],
                            [lng + size, lat - size],
                            [lng + size, lat + size],
                            [lng - size, lat + size],
                            [lng - size, lat - size],
                        ]
                    ],
                },
            }
        ],
    }


def pick_city(exclude: str = "") -> str:
    names = [z["name"].split(",")[0] for z in ZONES]
    if exclude:
        names = [n for n in names if n != exclude]
    return random.choice(names)


def simulate_session(memory: SessionMemory, session_num: int, dry_run: bool = False) -> dict:
    """Run one realistic user session through the agents."""
    user_id = f"sim_user_{session_num:03d}"
    session_id = memory.create_session(user_id)
    zone = random.choice(ZONES)
    city = zone["name"].split(",")[0]

    logger.info("Session %d: %s in %s", session_num, user_id, city)

    # Pick a conversation pattern: simple-only, mixed, or emergency
    pattern = random.choices(
        ["simple", "mixed", "deep_dive", "emergency"],
        weights=[30, 40, 20, 10],
        k=1,
    )[0]

    if pattern == "simple":
        queries = random.sample(SIMPLE_QUERIES, k=min(random.randint(2, 4), len(SIMPLE_QUERIES)))
    elif pattern == "mixed":
        n = random.randint(3, 6)
        queries = (
            random.sample(SIMPLE_QUERIES, k=min(2, len(SIMPLE_QUERIES)))
            + random.sample(MODERATE_QUERIES, k=min(2, len(MODERATE_QUERIES)))
            + random.sample(COMPLEX_QUERIES, k=min(1, len(COMPLEX_QUERIES)))
        )
        queries = random.sample(queries, k=min(n, len(queries)))
    elif pattern == "deep_dive":
        queries = random.sample(COMPLEX_QUERIES, k=min(random.randint(2, 4), len(COMPLEX_QUERIES)))
    else:  # emergency
        queries = random.sample(EMERGENCY_QUERIES, k=min(random.randint(1, 3), len(EMERGENCY_QUERIES)))
        queries += random.sample(FOLLOW_UP_QUERIES, k=min(2, len(FOLLOW_UP_QUERIES)))

    results = {
        "session_id": session_id,
        "user_id": user_id,
        "city": city,
        "pattern": pattern,
        "queries": [],
        "alerts": 0,
        "escalations": 0,
    }

    agents_used = {"quick": 0, "deep": 0, "emergency": 0}

    for i, query_template in enumerate(queries):
        city2 = pick_city(exclude=city)
        query = query_template.format(city=city, city2=city2)

        routing = route_query(query)
        agent_name = routing.agent

        logger.info("  [%d/%d] Q: %s → %s (%s/%s)", i + 1, len(queries), query[:60], agent_name, routing.complexity.value, routing.urgency.value)

        if dry_run:
            agents_used[agent_name] = agents_used.get(agent_name, 0) + 1
            results["queries"].append({"query": query, "agent": agent_name, "status": "dry_run"})
            continue

        date = datetime.now(UTC).strftime("%Y-%m-%d")
        params = {
            "latitude": zone["lat"],
            "longitude": zone["lng"],
            "date": date,
            "zone": zone["name"],
            "temperature": zone["temp_base"] + random.uniform(-3, 5),
        }

        try:
            if agent_name == "emergency":
                agent = EmergencyAgent(memory=memory)
                result = agent.handle(query, session_id, params)
                results["escalations"] += 1
            elif agent_name == "deep":
                polygon = build_polygon(zone["lat"], zone["lng"])
                params["polygon_aoi"] = polygon
                agent = DeepAgent(memory=memory)
                result = agent.handle(query, session_id, params)
            else:
                agent = QuickAgent(memory=memory)
                result = agent.handle(query, session_id, params)

            status = "error" if "error" in result else "ok"
            severity = result.get("severity")

            if severity and severity in ("extreme", "dangerous", "emergency"):
                results["alerts"] += 1

            agents_used[agent_name] = agents_used.get(agent_name, 0) + 1
            results["queries"].append({
                "query": query,
                "agent": agent_name,
                "status": status,
                "severity": severity,
                "response_time": result.get("api_calls", []),
            })
            logger.info("    → %s (severity=%s)", status, severity or "n/a")

        except Exception as e:
            logger.error("    → ERROR: %s", e)
            results["queries"].append({"query": query, "agent": agent_name, "status": f"error: {e}"})

        # Space out API calls to respect rate limits
        time.sleep(random.uniform(1.0, 3.0))

    results["agents_used"] = agents_used
    return results


def run_simulation(num_sessions: int = 5, dry_run: bool = False) -> list[dict]:
    """Run the full daily simulation."""
    logger.info("=" * 60)
    logger.info("HeatMind Daily Simulation — %s", datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC"))
    logger.info("Sessions: %d | Dry run: %s", num_sessions, dry_run)
    logger.info("=" * 60)

    memory = SessionMemory()
    all_results = []

    for i in range(1, num_sessions + 1):
        result = simulate_session(memory, i, dry_run=dry_run)
        all_results.append(result)

        # Pause between sessions
        if i < num_sessions and not dry_run:
            pause = random.uniform(2.0, 5.0)
            logger.info("Pausing %.1fs before next session...", pause)
            time.sleep(pause)

    # Summary
    total_queries = sum(len(r["queries"]) for r in all_results)
    total_alerts = sum(r["alerts"] for r in all_results)
    total_escalations = sum(r["escalations"] for r in all_results)
    agent_totals = {}
    for r in all_results:
        for agent, count in r.get("agents_used", {}).items():
            agent_totals[agent] = agent_totals.get(agent, 0) + count

    logger.info("=" * 60)
    logger.info("SIMULATION COMPLETE")
    logger.info("  Sessions:      %d", len(all_results))
    logger.info("  Total queries: %d", total_queries)
    logger.info("  Alerts:        %d", total_alerts)
    logger.info("  Escalations:   %d", total_escalations)
    logger.info("  Agents used:   %s", agent_totals)
    logger.info("=" * 60)

    return all_results


def main():
    parser = argparse.ArgumentParser(description="HeatMind Daily Simulator")
    parser.add_argument("--sessions", type=int, default=5, help="Number of sessions to simulate (default: 5)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would run without making API calls")
    args = parser.parse_args()

    try:
        run_simulation(num_sessions=args.sessions, dry_run=args.dry_run)
    except KeyboardInterrupt:
        logger.info("Simulation interrupted.")
        sys.exit(1)
    except Exception as e:
        logger.error("Simulation failed: %s", e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
