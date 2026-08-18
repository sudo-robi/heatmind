from api.fortyguard import FortyGuardClient
from memory.session import SessionMemory
from utils.validation import validate_coords


class QuickAgent:
    def __init__(self, memory=None):
        self.api = FortyGuardClient()
        self.memory = memory or SessionMemory()

    def handle(self, query: str, session_id: str, params: dict) -> dict:
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

        self.memory.add_message(session_id, "user", query)

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
        result = self._flatten_location_data(result)

        response = self._format_response(result)
        self.memory.add_message(session_id, "assistant", response)

        self.memory.update_session_context(session_id, "last_query", query)
        self.memory.update_session_context(session_id, "last_location", params)
        self.memory.log_event(
            session_id,
            "heat_reading",
            {"zone": params.get("zone", "unknown"), "data": result},
        )

        return {
            "agent": "quick",
            "response": response,
            "raw_data": result,
            "api_calls": self.api.get_call_log(),
        }

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
