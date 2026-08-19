import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import schedule

from agents.emergency_agent import EmergencyAgent
from api.fortyguard import FortyGuardClient
from config import (
    HEAT_INDEX_THRESHOLD,
    HEAT_THRESHOLD_C,
    MONITOR_INTERVAL_MINUTES,
)
from memory.session import SessionMemory
from utils.anomaly import AnomalyDetector
from utils.escalation import EscalationManager
from utils.validation import flatten_location_data

logger = logging.getLogger(__name__)


class MonitorLoop:
    def __init__(self, memory=None):
        self.api = FortyGuardClient()
        self.memory = memory or SessionMemory()
        self.emergency_agent = EmergencyAgent(memory=self.memory)
        self.zones = []
        self._shutdown_event = threading.Event()
        self._system_session_id = self.memory.create_session("monitor_system")
        self._anomaly_detector = AnomalyDetector(window_size=10, z_score_threshold=2.0)
        self._escalation_manager = EscalationManager()

    def add_zone(self, name: str, polygon_aoi: dict, latitude: float, longitude: float):
        self.zones.append(
            {
                "name": name,
                "polygon_aoi": polygon_aoi,
                "latitude": latitude,
                "longitude": longitude,
            }
        )

    def check_zone(self, zone: dict) -> dict:
        date = datetime.now(UTC).strftime("%Y-%m-%d")

        heatmap_id = self.api.create_heatmap(
            polygon_aoi=zone["polygon_aoi"],
            start_date=date,
            filter_type=1,
            granularity=100,
        )
        heatmap_result = self.api.wait_for_result(heatmap_id) if heatmap_id else {}

        env_id = self.api.create_env_params(
            latitude=zone["latitude"],
            longitude=zone["longitude"],
            temperature=35.0,
            start_date=date,
            start_time="14:00",
            filter_type=1,
        )
        env_result = self.api.wait_for_result(env_id) if env_id else {}
        env_result = flatten_location_data(env_result)

        reading = {
            "zone": zone["name"],
            "timestamp": datetime.now(UTC).isoformat(),
            "heatmap": heatmap_result,
            "env_params": env_result,
        }

        heat_index = env_result.get("heat_index_celsius", 0)
        if heat_index > 0:
            self._anomaly_detector.add_reading(zone["name"], heat_index, reading["timestamp"])

        self.memory.log_event(self._system_session_id, "heat_reading", reading)

        return reading

    def analyze_reading(self, reading: dict) -> bool:
        env = reading.get("env_params", {})
        heat_index = env.get("heat_index_celsius", 0)
        zone_name = reading.get("zone", "unknown")

        if heat_index >= HEAT_INDEX_THRESHOLD:
            return True

        heatmap = reading.get("heatmap", {})
        stats = heatmap.get("stats_data", {})
        temp_stats = stats.get("Temperature_stats", {})
        max_temp = temp_stats.get("Maximum", 0)

        if max_temp >= HEAT_THRESHOLD_C:
            return True

        anomaly = self._anomaly_detector.detect_anomaly(zone_name, heat_index)
        if anomaly["is_anomaly"]:
            logger.warning(
                "ANOMALY detected in %s: z_score=%.2f, deviation=%.1f",
                zone_name,
                anomaly["z_score"],
                anomaly["deviation"],
            )
            return True

        trend = self._anomaly_detector.detect_trend(zone_name)
        if trend["direction"] == "rising" and heat_index >= HEAT_INDEX_THRESHOLD - 5:
            logger.warning(
                "RISING TREND in %s: slope=%.3f, current=%.1f",
                zone_name,
                trend["slope"],
                heat_index,
            )
            return True

        return False

    def trigger_emergency(self, zone: dict, reading: dict):
        heat_index = reading.get("env_params", {}).get("heat_index_celsius", 35.0)
        escalation = self._escalation_manager.evaluate(zone["name"], heat_index, time.time())

        if escalation.get("escalated"):
            logger.warning(
                "ESCALATION [%s]: Level %s — actions: %s",
                zone["name"],
                escalation["level"],
                escalation.get("actions", []),
            )

        date = datetime.now(UTC).strftime("%Y-%m-%d")
        self.emergency_agent.handle(
            query=f"Emergency detected in {zone['name']}",
            session_id=self._system_session_id,
            params={
                "latitude": zone["latitude"],
                "longitude": zone["longitude"],
                "date": date,
                "zone": zone["name"],
                "temperature": heat_index,
                "escalation_level": escalation.get("level", "unknown"),
            },
        )

    def run_check(self):
        logger.info("Running heat check for %d zones...", len(self.zones))

        def _check_one(zone):
            try:
                reading = self.check_zone(zone)
                if self.analyze_reading(reading):
                    logger.warning("ALERT: %s: Threshold exceeded!", zone["name"])
                    self.trigger_emergency(zone, reading)
                else:
                    logger.info("  OK: %s: Normal conditions", zone["name"])
            except Exception as e:
                logger.error("  ERROR: %s: %s", zone["name"], type(e).__name__)

        with ThreadPoolExecutor(max_workers=min(len(self.zones), 4)) as pool:
            list(pool.map(_check_one, self.zones))

    def start(self):
        logger.info("Monitor started. Checking every %d minutes.", MONITOR_INTERVAL_MINUTES)
        schedule.every(MONITOR_INTERVAL_MINUTES).minutes.do(self.run_check)
        self.run_check()
        while not self._shutdown_event.is_set():
            schedule.run_pending()
            self._shutdown_event.wait(1)

    def stop(self):
        self._shutdown_event.set()
