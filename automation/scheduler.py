"""Event-driven scheduler for HeatMind automation.

Evaluates rules on each monitor check and fires actions. Integrates with the
monitor loop to enable proactive system behavior.
"""

import logging
from datetime import UTC, datetime

from automation.rules import RuleEngine

logger = logging.getLogger(__name__)


class AutomationScheduler:
    """Evaluates rules against zone data and queues actions."""

    def __init__(self, rule_engine: RuleEngine | None = None):
        self.rule_engine = rule_engine or RuleEngine()
        self._event_log: list[dict] = []

    def check_zone(self, zone_data: dict) -> list[dict]:
        """Evaluate rules for a single zone. Returns triggered actions."""
        triggered = self.rule_engine.evaluate(zone_data)
        for action in triggered:
            event = {
                "timestamp": datetime.now(UTC).isoformat(),
                "zone": zone_data.get("name", "unknown"),
                "rule": action["rule"],
                "action": action["action"],
                "heat_index": zone_data.get("heat_index"),
                "description": action["description"],
            }
            self._event_log.append(event)
        return triggered

    def check_all_zones(self, zones: list[dict]) -> list[dict]:
        """Evaluate rules for multiple zones."""
        all_triggered = []
        for zone in zones:
            triggered = self.check_zone(zone)
            all_triggered.extend(triggered)
        return all_triggered

    def get_event_log(self, limit: int = 20) -> list[dict]:
        """Return recent automation events."""
        return self._event_log[-limit:]

    def get_stats(self) -> dict:
        """Return automation statistics."""
        rules = self.rule_engine.get_rules()
        enabled = sum(1 for r in rules if r["enabled"])
        total_triggers = sum(r["trigger_count"] for r in rules)
        return {
            "total_rules": len(rules),
            "enabled_rules": enabled,
            "disabled_rules": len(rules) - enabled,
            "total_triggers": total_triggers,
            "recent_events": len(self._event_log),
        }
