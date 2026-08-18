from api.fortyguard import FortyGuardClient
from memory.session import SessionMemory
from utils.validation import validate_coords


class DeepAgent:
    def __init__(self, memory=None):
        self.api = FortyGuardClient()
        self.memory = memory or SessionMemory()

    def handle(self, query: str, session_id: str, params: dict) -> dict:
        latitude = params.get("latitude")
        longitude = params.get("longitude")
        date = params.get("date")
        zone = params.get("zone", "unknown")
        polygon_aoi = params.get("polygon_aoi")
        temperature = params.get("temperature", 35.0)

        if not all([latitude, longitude, date]):
            return {"error": "Missing required params: latitude, longitude, date"}

        try:
            validate_coords(latitude, longitude)
        except ValueError as e:
            return {"error": str(e)}

        self.memory.add_message(session_id, "user", query)

        results = {}
        steps = []

        env_id = self.api.create_env_params(
            latitude=latitude,
            longitude=longitude,
            temperature=temperature,
            start_date=date,
            start_time=params.get("time", "14:00"),
            filter_type=params.get("filter_type", 1),
        )
        if env_id:
            steps.append(("env_params", env_id))
            raw = self.api.wait_for_result(env_id)
            results["env_params"] = self._flatten_location_data(raw)

        if polygon_aoi:
            heatmap_id = self.api.create_heatmap(
                polygon_aoi=polygon_aoi,
                start_date=date,
                start_time=params.get("time", "14:00"),
                filter_type=params.get("filter_type", 1),
                granularity=params.get("granularity", 100),
            )
            if heatmap_id:
                steps.append(("heatmap", heatmap_id))
                results["heatmap"] = self.api.wait_for_result(heatmap_id)

        heat_index = temperature
        if "env_params" in results:
            heat_index = results["env_params"].get("heat_index_celsius", temperature)
            if isinstance(heat_index, list):
                heat_index = heat_index[0]

        intel_id = self.api.create_heat_intelligence(
            latitude=latitude,
            longitude=longitude,
            temperature=heat_index,
            date=date,
            analysis=["geographic", "environmental", "urban"],
        )
        if intel_id:
            steps.append(("heat_intelligence", intel_id))
            results["heat_intelligence"] = self.api.wait_for_result(intel_id)

        response = self._format_response(results)
        self.memory.add_message(session_id, "assistant", response)

        self.memory.update_session_context(session_id, "last_query", query)
        self.memory.update_session_context(session_id, "last_location", params)
        self.memory.log_decision(
            session_id,
            query,
            decision="deep",
            reasoning=f"Chained {len(steps)} endpoints: {', '.join(s[0] for s in steps)}",
            outcome="completed",
        )

        return {
            "agent": "deep",
            "response": response,
            "raw_data": results,
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
        lines = ["**Comprehensive Heat Risk Assessment:**\n"]

        if "env_params" in data:
            env = data["env_params"]
            lines.append("**Environmental Conditions:**")
            for key in ["heat_index_celsius", "apparent_temperature_celsius",
                        "relative_humidity_percent", "air_quality:idx"]:
                if key in env and env[key] is not None:
                    label = key.replace("_", " ").replace(":", " ").title()
                    lines.append(f"  - {label}: {env[key]}")
            lines.append("")

        if "heatmap" in data:
            hm = data["heatmap"]
            if "stats_data" in hm:
                stats = hm["stats_data"]
                lines.append("**Heatmap Statistics:**")
                if "Temperature_stats" in stats:
                    ts = stats["Temperature_stats"]
                    lines.append(f"  - Min: {ts.get('Minimum', 'N/A')}°C")
                    lines.append(f"  - Max: {ts.get('Maximum', 'N/A')}°C")
                    lines.append(f"  - Mean: {ts.get('Mean', 'N/A')}°C")
                lines.append("")

        if "heat_intelligence" in data:
            lines.append("**Heat Intelligence Report:**")
            lines.append("  - Multi-dimensional analysis complete")
            lines.append("  - Geographic, environmental, and urban factors analyzed")

        return "\n".join(lines)
