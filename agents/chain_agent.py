import logging

from api.fortyguard import FortyGuardClient
from memory.session import SessionMemory
from utils.demo import demo_env_params, demo_heat_intelligence, demo_heatmap
from utils.validation import flatten_location_data, validate_coords

logger = logging.getLogger(__name__)


class ReasoningStep:
    def __init__(self, step_num: int, action: str, endpoint: str, reason: str):
        self.step_num = step_num
        self.action = action
        self.endpoint = endpoint
        self.reason = reason
        self.result = None
        self.error = None

    def to_dict(self):
        return {
            "step": self.step_num,
            "action": self.action,
            "endpoint": self.endpoint,
            "reason": self.reason,
            "status": "success" if self.result else ("error" if self.error else "pending"),
            "result_summary": self._summarize_result(),
        }

    def _summarize_result(self):
        if self.error:
            return f"Error: {self.error}"
        if not self.result:
            return "Pending"
        if isinstance(self.result, dict):
            keys = list(self.result.keys())[:5]
            return f"Keys: {', '.join(keys)}"
        return str(self.result)[:100]


class ChainAgent:
    def __init__(self, memory=None):
        try:
            self.api = FortyGuardClient()
        except ValueError:
            self.api = None
        self.memory = memory or SessionMemory()

    def execute_chain(
        self,
        query: str,
        session_id: str,
        endpoints: list[str],
        params: dict,
    ) -> dict:
        latitude = params.get("latitude")
        longitude = params.get("longitude")
        date = params.get("date")
        temperature = params.get("temperature", 35.0)
        polygon_aoi = params.get("polygon_aoi")
        start_time = params.get("time", "14:00")

        steps = []
        results = {}
        step_num = 0

        self.memory.add_message(session_id, "user", query)

        if "env_params" in endpoints:
            step_num += 1
            step = ReasoningStep(
                step_num=step_num,
                action="Fetch environmental parameters",
                endpoint="POST /v1/env_params",
                reason="Need current heat index, humidity, and AQI to assess conditions",
            )
            steps.append(step)
            try:
                validate_coords(latitude, longitude)
                if self.api is None:
                    step.result = demo_env_params(latitude, longitude)
                    results["env_params"] = step.result
                else:
                    activity_id = self.api.create_env_params(
                        latitude=latitude,
                        longitude=longitude,
                        temperature=temperature,
                        start_date=date,
                        start_time=start_time,
                        filter_type=1,
                    )
                    if activity_id:
                        step.result = self.api.wait_for_result(activity_id)
                        step.result = flatten_location_data(step.result)
                        results["env_params"] = step.result
                        if step.result:
                            temperature = step.result.get("heat_index_celsius", temperature)
                    else:
                        step.error = "API returned no activity_id"
            except Exception as e:
                step.error = str(e)[:200]

        if "heatmap" in endpoints and polygon_aoi:
            step_num += 1
            step = ReasoningStep(
                step_num=step_num,
                action="Generate thermal heatmap",
                endpoint="POST /v1/heatmap",
                reason=f"Visualize heat distribution across the area using {params.get('granularity', 100)}m granularity",
            )
            steps.append(step)
            try:
                if self.api is None:
                    step.result = demo_heatmap(latitude, longitude)
                    results["heatmap"] = step.result
                else:
                    activity_id = self.api.create_heatmap(
                        polygon_aoi=polygon_aoi,
                        start_date=date,
                        start_time=start_time,
                        filter_type=1,
                        granularity=params.get("granularity", 100),
                    )
                    if activity_id:
                        step.result = self.api.wait_for_result(activity_id)
                        results["heatmap"] = step.result
                    else:
                        step.error = "API returned no activity_id"
            except Exception as e:
                step.error = str(e)[:200]

        if "heat_intelligence" in endpoints:
            step_num += 1
            step = ReasoningStep(
                step_num=step_num,
                action="Generate heat intelligence report",
                endpoint="POST /v1/heat_intelligence",
                reason=f"Deep analysis using temperature {temperature}°C across geographic, environmental, and urban dimensions",
            )
            steps.append(step)
            try:
                if self.api is None:
                    step.result = demo_heat_intelligence(latitude, longitude)
                    results["heat_intelligence"] = step.result
                else:
                    activity_id = self.api.create_heat_intelligence(
                        latitude=latitude,
                        longitude=longitude,
                        temperature=temperature,
                        date=date,
                        analysis=["geographic", "environmental", "urban"],
                    )
                    if activity_id:
                        step.result = self.api.wait_for_result(activity_id)
                        results["heat_intelligence"] = step.result
                    else:
                        step.error = "API returned no activity_id"
            except Exception as e:
                step.error = str(e)[:200]

        response = self._format_chained_response(results, steps, query)
        self.memory.add_message(session_id, "assistant", response)
        self.memory.log_decision(
            session_id,
            query,
            decision=f"chain:{','.join(endpoints)}",
            reasoning=self._build_reasoning_text(steps),
            outcome="completed",
        )

        api_calls = self.api.get_call_log() if self.api else []

        return {
            "agent": "chain",
            "response": response,
            "raw_data": results,
            "reasoning": [s.to_dict() for s in steps],
            "api_calls": api_calls,
            "endpoints_used": endpoints,
        }

    def _format_chained_response(self, results: dict, steps: list, query: str) -> str:
        lines = ["**Heat Intelligence Analysis**\n"]

        lines.append("**Reasoning Chain:**")
        for step in steps:
            status = "✓" if step.result else ("✗" if step.error else "○")
            lines.append(f"  {status} Step {step.step_num}: {step.action}")
            lines.append(f"    Endpoint: `{step.endpoint}`")
            lines.append(f"    Why: {step.reason}")
            if step.error:
                lines.append(f"    Result: Error - {step.error}")
            elif step.result:
                lines.append("    Result: Success")
        lines.append("")

        if "env_params" in results:
            env = results["env_params"]
            lines.append("**Environmental Conditions:**")
            for key in [
                "heat_index_celsius",
                "apparent_temperature_celsius",
                "relative_humidity_percent",
                "air_quality:idx",
            ]:
                if key in env and env[key] is not None:
                    label = key.replace("_", " ").replace(":", " ").title()
                    lines.append(f"  - {label}: {env[key]}")
            lines.append("")

        if "heatmap" in results:
            hm = results["heatmap"]
            if "stats_data" in hm:
                stats = hm["stats_data"]
                lines.append("**Heatmap Statistics:**")
                if "Temperature_stats" in stats:
                    ts = stats["Temperature_stats"]
                    lines.append(f"  - Min: {ts.get('Minimum', 'N/A')}°C")
                    lines.append(f"  - Max: {ts.get('Maximum', 'N/A')}°C")
                    lines.append(f"  - Mean: {ts.get('Mean', 'N/A')}°C")
                lines.append("")

        if "heat_intelligence" in results:
            lines.append("**Heat Intelligence Report:**")
            lines.append("  - Multi-dimensional analysis complete")
            lines.append("  - Geographic, environmental, and urban factors analyzed")
            lines.append("")

        return "\n".join(lines)

    def _build_reasoning_text(self, steps: list) -> str:
        parts = []
        for step in steps:
            status = "success" if step.result else "failed"
            parts.append(f"{step.endpoint} ({status}): {step.reason}")
        return " | ".join(parts)
