import logging
import schedule
import time
import threading
from datetime import datetime, timezone
from api.fortyguard import FortyGuardClient
from memory.session import SessionMemory
from agents.emergency_agent import EmergencyAgent
from config import (
    MONITOR_INTERVAL_MINUTES,
    HEAT_THRESHOLD_C,
    HEAT_INDEX_THRESHOLD,
)

logger = logging.getLogger(__name__)


class MonitorLoop:
    def __init__(self, memory=None):
        self.api = FortyGuardClient()
        self.memory = memory or SessionMemory()
        self.emergency_agent = EmergencyAgent(memory=self.memory)
        self.zones = []
        self._shutdown_event = threading.Event()
        self._system_session_id = self.memory.create_session("monitor_system")

    def add_zone(self, name: str, polygon_aoi: dict, latitude: float, longitude: float):
        self.zones.append({
            "name": name,
            "polygon_aoi": polygon_aoi,
            "latitude": latitude,
            "longitude": longitude,
        })

    def _flatten_location_data(self, raw: dict) -> dict:
        locations = raw.get("locations", [])
        if locations:
            loc = locations[0]
            params = loc.get("parameters", {})
            flat = {}
            for key, val in params.items():
                if isinstance(val, list) and len(val) > 0:
                    flat[key] = val[0]
                else:
                    flat[key] = val
            return flat
        return raw

    def check_zone(self, zone: dict) -> dict:
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")

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
        env_result = self._flatten_location_data(env_result)

        reading = {
            "zone": zone["name"],
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "heatmap": heatmap_result,
            "env_params": env_result,
        }

        self.memory.log_event(self._system_session_id, "heat_reading", reading)

        return reading

    def analyze_reading(self, reading: dict) -> bool:
        env = reading.get("env_params", {})
        heat_index = env.get("heat_index_celsius", 0)

        if heat_index >= HEAT_INDEX_THRESHOLD:
            return True

        heatmap = reading.get("heatmap", {})
        stats = heatmap.get("stats_data", {})
        temp_stats = stats.get("Temperature_stats", {})
        max_temp = temp_stats.get("Maximum", 0)

        if max_temp >= HEAT_THRESHOLD_C:
            return True

        return False

    def trigger_emergency(self, zone: dict, reading: dict):
        date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        self.emergency_agent.handle(
            query=f"Emergency detected in {zone['name']}",
            session_id=self._system_session_id,
            params={
                "latitude": zone["latitude"],
                "longitude": zone["longitude"],
                "date": date,
                "zone": zone["name"],
                "temperature": reading.get("env_params", {}).get("heat_index_celsius", 35.0),
            },
        )

    def run_check(self):
        logger.info("Running heat check for %d zones...", len(self.zones))
        for zone in self.zones:
            try:
                reading = self.check_zone(zone)
                if self.analyze_reading(reading):
                    logger.warning("ALERT: %s: Threshold exceeded!", zone['name'])
                    self.trigger_emergency(zone, reading)
                else:
                    logger.info("  OK: %s: Normal conditions", zone['name'])
            except Exception as e:
                logger.error("  ERROR: %s: %s", zone['name'], type(e).__name__)

    def start(self):
        logger.info("Monitor started. Checking every %d minutes.", MONITOR_INTERVAL_MINUTES)
        schedule.every(MONITOR_INTERVAL_MINUTES).minutes.do(self.run_check)
        self.run_check()
        while not self._shutdown_event.is_set():
            schedule.run_pending()
            self._shutdown_event.wait(1)

    def stop(self):
        self._shutdown_event.set()
