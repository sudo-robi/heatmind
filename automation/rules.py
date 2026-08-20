"""Event-driven automation rules for HeatMind.

Rules define condition → action mappings that the system evaluates on each
monitor check. When conditions are met, actions fire automatically — the system
acts proactively, not just reactively to user queries.
"""

import logging
import re
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class Rule:
    """A single automation rule."""
    name: str
    condition: str
    action: str
    enabled: bool = True
    description: str = ""
    last_triggered: str | None = None
    trigger_count: int = 0


# Default rules for heat monitoring
DEFAULT_RULES: list[Rule] = [
    Rule(
        name="heat_alert",
        condition="heat_index >= 45",
        action="trigger_emergency",
        description="Auto-trigger emergency protocol when heat index exceeds 45°C",
    ),
    Rule(
        name="rising_trend",
        condition="trend == 'rising' AND heat_index >= 40",
        action="send_warning",
        description="Send warning when heat is rising and above 40°C",
    ),
    Rule(
        name="anomaly_detected",
        condition="anomaly == True",
        action="deep_analysis",
        description="Run deep analysis when anomaly is detected",
    ),
    Rule(
        name="daily_report",
        condition="time == '08:00'",
        action="generate_report",
        description="Generate daily heat report at 8 AM",
        enabled=False,
    ),
]


class RuleEngine:
    """Evaluates automation rules against zone data."""

    def __init__(self, rules: list[Rule] | None = None):
        self.rules = rules or list(DEFAULT_RULES)

    def evaluate(self, zone_data: dict) -> list[dict]:
        """Evaluate all enabled rules against zone data. Returns list of triggered actions."""
        triggered = []
        for rule in self.rules:
            if not rule.enabled:
                continue
            if self._check_condition(rule.condition, zone_data):
                rule.trigger_count += 1
                action = {
                    "rule": rule.name,
                    "action": rule.action,
                    "condition": rule.condition,
                    "zone": zone_data.get("name", "unknown"),
                    "heat_index": zone_data.get("heat_index"),
                    "description": rule.description,
                }
                triggered.append(action)
                logger.info("Rule triggered: %s in %s (action: %s)", rule.name, action["zone"], rule.action)
        return triggered

    def _check_condition(self, condition: str, data: dict) -> bool:
        """Simple condition evaluator. Supports: >=, <=, ==, !=, AND, OR, in."""
        try:
            # Normalize the condition
            cond = condition.strip()

            # Handle AND conditions
            if " AND " in cond:
                parts = cond.split(" AND ")
                return all(self._check_condition(p.strip(), data) for p in parts)

            # Handle OR conditions
            if " OR " in cond:
                parts = cond.split(" OR ")
                return any(self._check_condition(p.strip(), data) for p in parts)

            # Parse simple conditions: field operator value
            for op in [">=", "<=", "==", "!=", ">", "<"]:
                if op in cond:
                    field_name, value_str = cond.split(op, 1)
                    field_name = field_name.strip()
                    value_str = value_str.strip().strip("'\"")

                    actual = data.get(field_name)
                    if actual is None:
                        return False

                    # Type coercion
                    if isinstance(actual, (int, float)):
                        try:
                            compare_val = float(value_str)
                        except ValueError:
                            return False
                        if op == ">=":
                            return actual >= compare_val
                        elif op == "<=":
                            return actual <= compare_val
                        elif op == ">":
                            return actual > compare_val
                        elif op == "<":
                            return actual < compare_val
                        elif op == "==":
                            return actual == compare_val
                        elif op == "!=":
                            return actual != compare_val
                    else:
                        # String comparison
                        if op == "==":
                            return str(actual).lower() == value_str.lower()
                        elif op == "!=":
                            return str(actual).lower() != value_str.lower()

            return False
        except Exception as e:
            logger.warning("Failed to evaluate condition '%s': %s", condition, e)
            return False

    def toggle_rule(self, name: str, enabled: bool) -> bool:
        """Enable or disable a rule by name. Returns True if found."""
        for rule in self.rules:
            if rule.name == name:
                rule.enabled = enabled
                logger.info("Rule %s: %s", name, "enabled" if enabled else "disabled")
                return True
        return False

    def get_rules(self) -> list[dict]:
        """Return all rules as dicts."""
        return [
            {
                "name": r.name,
                "condition": r.condition,
                "action": r.action,
                "enabled": r.enabled,
                "description": r.description,
                "trigger_count": r.trigger_count,
            }
            for r in self.rules
        ]

    def add_rule(self, name: str, condition: str, action: str, description: str = "") -> Rule:
        """Add a new rule."""
        rule = Rule(name=name, condition=condition, action=action, description=description)
        self.rules.append(rule)
        return rule

    def remove_rule(self, name: str) -> bool:
        """Remove a rule by name."""
        for i, rule in enumerate(self.rules):
            if rule.name == name:
                self.rules.pop(i)
                return True
        return False
