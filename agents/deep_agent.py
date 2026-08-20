import time
from concurrent.futures import ThreadPoolExecutor

from api.fortyguard import FortyGuardClient
from memory.session import SessionMemory
from utils.metrics import get_metrics
from utils.middleware import HistoryMiddleware
from utils.validation import flatten_location_data, format_env_conditions, format_heatmap_stats, validate_coords


class DeepAgent:
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
        polygon_aoi = params.get("polygon_aoi")
        temperature = params.get("temperature", 35.0)

        if not all([latitude, longitude, date]):
            return {"error": "Missing required params: latitude, longitude, date"}

        try:
            validate_coords(latitude, longitude)
        except ValueError as e:
            return {"error": str(e)}

        self._middleware.enrich_context(session_id, query)

        results = {}
        steps = []

        def fetch_env():
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
                return flatten_location_data(raw)
            return None

        def fetch_heatmap():
            if not polygon_aoi:
                return None
            heatmap_id = self.api.create_heatmap(
                polygon_aoi=polygon_aoi,
                start_date=date,
                start_time=params.get("time", "14:00"),
                filter_type=params.get("filter_type", 1),
                granularity=params.get("granularity", 100),
            )
            if heatmap_id:
                steps.append(("heatmap", heatmap_id))
                return self.api.wait_for_result(heatmap_id)
            return None

        with ThreadPoolExecutor(max_workers=2) as pool:
            env_future = pool.submit(fetch_env)
            heatmap_future = pool.submit(fetch_heatmap)
            env_result = env_future.result()
            heatmap_result = heatmap_future.result()

        if env_result is not None:
            results["env_params"] = env_result
        if heatmap_result is not None:
            results["heatmap"] = heatmap_result

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
        self._middleware.record_interaction(session_id, query, response)

        self.memory.update_session_context(session_id, "last_query", query)
        self.memory.update_session_context(session_id, "last_location", params)
        self.memory.log_decision(
            session_id,
            query,
            decision="deep",
            reasoning=f"Chained {len(steps)} endpoints: {', '.join(s[0] for s in steps)}",
            outcome="completed",
        )

        latency = (time.time() - start) * 1000
        self._metrics.record_agent_call("deep", latency, len(query))

        return {
            "agent": "deep",
            "response": response,
            "raw_data": results,
            "api_calls": self.api.get_call_log(),
        }

    def _format_response(self, data: dict) -> str:
        lines = ["**Comprehensive Heat Risk Assessment:**\n"]
        if "env_params" in data:
            lines.extend(format_env_conditions(data["env_params"]))
        lines.extend(format_heatmap_stats(data))

        if "heat_intelligence" in data:
            lines.append("**Heat Intelligence Report:**")
            lines.append("  - Multi-dimensional analysis complete")
            lines.append("  - Geographic, environmental, and urban factors analyzed")

        return "\n".join(lines)
