import time

from api.fortyguard import FortyGuardClient
from memory.session import SessionMemory
from utils.metrics import get_metrics
from utils.middleware import HistoryMiddleware
from utils.validation import flatten_location_data, validate_coords


class QuickAgent:
    def __init__(self, memory=None):
        self.api = FortyGuardClient()
        self.memory = memory or SessionMemory()
        self._middleware = HistoryMiddleware(self.memory)
        self._metrics = get_metrics()

    def handle(self, query: str, session_id: str, params: dict) -> dict:
        start = time.time()
        latitude = params.get("latitude")
        longitude = params.get("longitude")
        date = params.get("date")
        temperature = params.get("temperature", 35.0)

        if not all([latitude, longitude, date]):
            return {"error": "Missing required params: latitude, longitude, date"}

        try:
            validate_coords(latitude, longitude)
        except ValueError as e:
            return {"error": str(e)}

        self._middleware.enrich_context(session_id, query)

        activity_id = self.api.create_env_params(
            latitude=latitude,
            longitude=longitude,
            temperature=temperature,
            start_date=date,
            start_time=params.get("time", "14:00"),
            filter_type=params.get("filter_type", 1),
        )

        if not activity_id:
            return {"error": "API request failed"}

        result = self.api.wait_for_result(activity_id)
        result = flatten_location_data(result)

        response = self._format_response(result)
        self._middleware.record_interaction(session_id, query, response)

        self.memory.update_session_context(session_id, "last_query", query)
        self.memory.update_session_context(session_id, "last_location", params)
        self.memory.log_event(
            session_id,
            "heat_reading",
            {"zone": params.get("zone", "unknown"), "data": result},
        )

        latency = (time.time() - start) * 1000
        self._metrics.record_agent_call("quick", latency, len(query))

        return {
            "agent": "quick",
            "response": response,
            "raw_data": result,
            "api_calls": self.api.get_call_log(),
        }

    def _format_response(self, data: dict) -> str:
        lines = ["**Current Heat Conditions:**"]
        for key in [
            "heat_index_celsius",
            "apparent_temperature_celsius",
            "relative_humidity_percent",
            "air_quality:idx",
        ]:
            if key in data and data[key] is not None:
                label = key.replace("_", " ").replace(":", " ").title()
                lines.append(f"- {label}: {data[key]}")
        return "\n".join(lines)
