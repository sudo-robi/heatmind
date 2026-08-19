"""Escalation management (Winner 4: Customer Support Agent).

Defines escalation paths, severity levels, and automatic escalation rules.
Maps detected conditions to appropriate response tiers.
"""

import logging
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class EscalationLevel(Enum):
    LEVEL_1 = "monitor"
    LEVEL_2 = "notify"
    LEVEL_3 = "alert"
    LEVEL_4 = "emergency"
    LEVEL_5 = "critical"


@dataclass
class EscalationRule:
    level: EscalationLevel
    heat_index_min: float
    actions: list[str]
    channels: list[str]
    cooldown_minutes: int = 30


@dataclass
class EscalationState:
    level: EscalationLevel
    triggered_at: float = 0
    acknowledged: bool = False
    actions_taken: list[str] = field(default_factory=list)


DEFAULT_RULES = [
    EscalationRule(
        level=EscalationLevel.LEVEL_1,
        heat_index_min=32,
        actions=["log_reading", "update_dashboard"],
        channels=["console"],
        cooldown_minutes=60,
    ),
    EscalationRule(
        level=EscalationLevel.LEVEL_2,
        heat_index_min=41,
        actions=["log_reading", "send_notification", "update_dashboard"],
        channels=["console", "email"],
        cooldown_minutes=30,
    ),
    EscalationRule(
        level=EscalationLevel.LEVEL_3,
        heat_index_min=46,
        actions=["log_reading", "send_alert", "update_dashboard", "notify_supervisor"],
        channels=["console", "email", "slack"],
        cooldown_minutes=15,
    ),
    EscalationRule(
        level=EscalationLevel.LEVEL_4,
        heat_index_min=51,
        actions=["log_reading", "send_alert", "trigger_emergency_protocol", "update_dashboard"],
        channels=["console", "email", "slack", "webhook"],
        cooldown_minutes=5,
    ),
    EscalationRule(
        level=EscalationLevel.LEVEL_5,
        heat_index_min=54,
        actions=[
            "log_reading",
            "send_alert",
            "trigger_emergency_protocol",
            "activate_cooling",
            "update_dashboard",
        ],
        channels=["console", "email", "slack", "webhook"],
        cooldown_minutes=0,
    ),
]


class EscalationManager:
    def __init__(self, rules: list[EscalationRule] | None = None):
        self.rules = sorted(rules or DEFAULT_RULES, key=lambda r: r.heat_index_min)
        self._states: dict[str, EscalationState] = {}

    def evaluate(self, zone: str, heat_index: float, timestamp: float = 0) -> dict:
        rule = self._get_matching_rule(heat_index)
        current = self._states.get(zone)

        if current and current.level == rule.level:
            return {
                "escalated": False,
                "level": rule.level.value,
                "reason": "already_at_same_level",
            }

        if current and current.acknowledged:
            return {
                "escalated": False,
                "level": rule.level.value,
                "reason": "acknowledged",
            }

        state = EscalationState(level=rule.level, triggered_at=timestamp)
        self._states[zone] = state

        logger.warning(
            "ESCALATION [%s]: Level %s triggered (heat_index=%.1f)",
            zone,
            rule.level.value,
            heat_index,
        )

        return {
            "escalated": True,
            "level": rule.level.value,
            "actions": rule.actions,
            "channels": rule.channels,
            "cooldown_minutes": rule.cooldown_minutes,
        }

    def acknowledge(self, zone: str) -> bool:
        state = self._states.get(zone)
        if state:
            state.acknowledged = True
            logger.info("Escalation acknowledged for zone: %s", zone)
            return True
        return False

    def get_status(self, zone: str | None = None) -> dict:
        if zone:
            state = self._states.get(zone)
            if state:
                return {
                    "zone": zone,
                    "level": state.level.value,
                    "acknowledged": state.acknowledged,
                    "triggered_at": state.triggered_at,
                }
            return {"zone": zone, "level": "none"}

        return {
            z: {
                "level": s.level.value,
                "acknowledged": s.acknowledged,
            }
            for z, s in self._states.items()
        }

    def _get_matching_rule(self, heat_index: float) -> EscalationRule:
        matched = self.rules[0]
        for rule in self.rules:
            if heat_index >= rule.heat_index_min:
                matched = rule
        return matched
