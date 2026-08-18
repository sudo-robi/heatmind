import logging
import time

import requests

from config import FORTYGUARD_API_KEY, FORTYGUARD_BASE_URL

logger = logging.getLogger(__name__)


class FortyGuardClient:
    def __init__(self, api_key: str = FORTYGUARD_API_KEY):
        if not api_key:
            raise ValueError("FORTYGUARD_API_KEY is required")
        self.api_key = api_key
        self.base_url = FORTYGUARD_BASE_URL
        self.headers = {
            "api-key": self.api_key,
            "Content-Type": "application/json",
        }
        self._call_log = []

    def _post(self, endpoint: str, payload: dict) -> dict:
        url = f"{self.base_url}/{endpoint}"
        self._call_log.append({"method": "POST", "url": url, "timestamp": time.time()})
        logger.info("POST %s", url)
        response = requests.post(url, headers=self.headers, json=payload, timeout=30)
        response.raise_for_status()
        return response.json()

    def _get(self, endpoint: str) -> dict:
        url = f"{self.base_url}/{endpoint}"
        self._call_log.append({"method": "GET", "url": url, "timestamp": time.time()})
        logger.info("GET %s", url)
        response = requests.get(url, headers=self.headers, timeout=30)
        response.raise_for_status()
        return response.json()

    def get_call_log(self) -> list:
        log = self._call_log.copy()
        self._call_log.clear()
        return log

    def create_heatmap(
        self,
        polygon_aoi: dict,
        start_date: str,
        start_time: str | None = None,
        end_time: str | None = None,
        end_date: str | None = None,
        filter_type: int = 1,
        granularity: int = 100,
    ) -> str | None:
        try:
            date_time = {"start_date": start_date, "filter_type": filter_type}
            if start_time:
                date_time["start_time"] = start_time
            if end_time:
                date_time["end_time"] = end_time
            if end_date:
                date_time["end_date"] = end_date

            payload = {
                "polygon_aoi": polygon_aoi,
                "date_time": date_time,
                "granularity": granularity,
            }
            result = self._post("heatmap", payload)
            return result.get("data", {}).get("activity_id")
        except Exception as e:
            logger.error("create_heatmap failed: %s", type(e).__name__)
            return None

    def create_satellite(
        self,
        latitude: float,
        longitude: float,
        start_date: str,
        start_time: str | None = None,
        filter_type: int = 1,
        granularity: int = 80,
    ) -> str | None:
        try:
            date_time = {"start_date": start_date, "filter_type": filter_type}
            if start_time:
                date_time["start_time"] = start_time

            payload = {
                "sat": {"latitude": latitude, "longitude": longitude},
                "date_time": date_time,
                "granularity": granularity,
            }
            result = self._post("satellite", payload)
            return result.get("data", {}).get("activity_id")
        except Exception as e:
            logger.error("create_satellite failed: %s", type(e).__name__)
            return None

    def create_streetview(
        self,
        latitude: float,
        longitude: float,
        vertical_angle: float = 10.0,
        horizontal_angle: float = 90.0,
        back_view: bool = False,
    ) -> str | None:
        try:
            payload = {
                "latitude": latitude,
                "longitude": longitude,
                "vertical_angle": vertical_angle,
                "horizontal_angle": horizontal_angle,
                "back_view": back_view,
            }
            result = self._post("streetview", payload)
            return result.get("data", {}).get("activity_id")
        except Exception as e:
            logger.error("create_streetview failed: %s", type(e).__name__)
            return None

    def create_heat_intelligence(
        self,
        latitude: float,
        longitude: float,
        temperature: float,
        date: str,
        analysis: list[str],
    ) -> str | None:
        try:
            payload = {
                "latitude": latitude,
                "longitude": longitude,
                "temperature": temperature,
                "date": date,
                "analysis": analysis,
            }
            result = self._post("heat_intelligence", payload)
            return result.get("data", {}).get("activity_id")
        except Exception as e:
            logger.error("create_heat_intelligence failed: %s", type(e).__name__)
            return None

    def create_env_params(
        self,
        latitude: float,
        longitude: float,
        temperature: float,
        start_date: str,
        start_time: str | None = None,
        filter_type: int = 1,
    ) -> str | None:
        try:
            date_time = {"start_date": start_date, "filter_type": filter_type}
            if start_time:
                date_time["start_time"] = start_time

            payload = {
                "latitude": latitude,
                "longitude": longitude,
                "temperature": temperature,
                "date_time": date_time,
            }
            result = self._post("env_params", payload)
            return result.get("data", {}).get("activity_id")
        except Exception as e:
            logger.error("create_env_params failed: %s", type(e).__name__)
            return None

    def get_status(self, activity_id: str) -> dict:
        try:
            return self._get(f"status/{activity_id}")
        except Exception as e:
            logger.error("get_status failed: %s", type(e).__name__)
            return {"data": {"status": "error"}}

    def get_credits(self) -> dict:
        try:
            return self._get("system/fetch-api-key-usage")
        except Exception as e:
            logger.error("get_credits failed: %s", type(e).__name__)
            return {"error": str(e)}

    def wait_for_result(self, activity_id: str, timeout: int = 300, poll_interval: int = 5) -> dict | None:
        start = time.time()
        while time.time() - start < timeout:
            try:
                status_data = self.get_status(activity_id)
                status = status_data.get("data", {}).get("status", "").lower()
                if status in ("completed", "succeeded"):
                    return status_data["data"].get("result", status_data["data"])
                elif status in ("failed", "error"):
                    raise RuntimeError(f"Task {activity_id} failed")
            except (RuntimeError, TimeoutError):
                raise
            except Exception as e:
                logger.error("poll failed: %s", type(e).__name__)
            time.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.5, 15)
        raise TimeoutError(f"Task {activity_id} timed out after {timeout}s")
