import logging
import time
from datetime import UTC, datetime

from api.fortyguard import FortyGuardClient
from memory.session import SessionMemory
from utils.alerts import send_alert
from utils.demo import demo_env_params
from utils.escalation import EscalationManager
from utils.llm import LLMError, MockLLM, extract_json, get_llm, timed_complete
from utils.metrics import get_metrics
from utils.middleware import HistoryMiddleware
from utils.personas import HEALTH_OFFICER_PERSONA
from utils.validation import flatten_location_data, validate_coords

logger = logging.getLogger(__name__)


class EmergencyAgent:
    def __init__(self, memory=None, llm=None):
        try:
            self.api = FortyGuardClient()
        except ValueError:
            self.api = None
        self.llm = llm or get_llm()
        self.memory = memory or SessionMemory()
        self._middleware = HistoryMiddleware(self.memory)
        self._escalation = EscalationManager()
        self._metrics = get_metrics()

    def handle(self, query: str, session_id: str, params: dict) -> dict:
        start = time.time()
        latitude = params.get("latitude")
        longitude = params.get("longitude")
        date = params.get("date")
        zone = params.get("zone", "unknown")
        temperature = params.get("temperature", 35.0)

        if not all([latitude, longitude, date]):
            return {"error": "Missing required params: latitude, longitude, date"}

        try:
            validate_coords(latitude, longitude)
        except ValueError as e:
            return {"error": str(e)}

        self._middleware.enrich_context(session_id, query)

        env_data = {}
        if self.api is not None:
            env_id = self.api.create_env_params(
                latitude=latitude,
                longitude=longitude,
                temperature=temperature,
                start_date=date,
                start_time=params.get("time", "14:00"),
                filter_type=1,
            )
            if env_id:
                raw = self.api.wait_for_result(env_id)
                env_data = flatten_location_data(raw)
        else:
            env_data = demo_env_params(latitude, longitude)

        heat_index = env_data.get("heat_index_celsius", temperature)
        if isinstance(heat_index, list):
            heat_index = heat_index[0]
        severity = self._assess_severity(heat_index, env_data)

        recommendations = self._generate_recommendations(severity, env_data, heat_index, zone)

        alert_payload = {
            "zone": zone,
            "severity": severity,
            "heat_index": heat_index,
            "timestamp": datetime.now(UTC).isoformat(),
            "recommendations": recommendations,
        }
        send_alert(alert_payload)
        self._metrics.record_alert_sent()

        escalation = self._escalation.evaluate(zone, heat_index, time.time())
        if escalation.get("escalated"):
            self._metrics.record_escalation(zone, escalation["level"])

        self.memory.log_event(
            session_id,
            "emergency_detected",
            {"zone": zone, "severity": severity, "data": env_data},
        )
        self.memory.log_decision(
            session_id,
            query,
            decision=f"Emergency response: {severity}",
            reasoning=f"Heat index {heat_index}°C triggered {severity} alert",
            outcome="alert_sent",
        )

        response = self._format_response(severity, heat_index, recommendations)
        self._middleware.record_interaction(session_id, query, response)

        latency = (time.time() - start) * 1000
        self._metrics.record_agent_call("emergency", latency, len(query))

        return {
            "agent": "emergency",
            "severity": severity,
            "response": response,
            "raw_data": {"env_params": env_data, "alert": alert_payload},
            "api_calls": self.api.get_call_log() if self.api else [],
            "llm_mode": self.llm.name,
            "recommendations": recommendations,
        }

    def _assess_severity(self, heat_index: float, env_data: dict) -> str:
        if heat_index >= 54:
            return "extreme"
        elif heat_index >= 46:
            return "dangerous"
        elif heat_index >= 41:
            return "emergency"
        elif heat_index >= 32:
            return "warning"
        return "normal"

    def _generate_recommendations(
        self, severity: str, env_data: dict, heat_index: float | None = None, zone: str = ""
    ) -> list:
        fallback = self._hardcoded_recommendations(severity)

        if isinstance(self.llm, MockLLM):
            return fallback

        system = (
            f"{HEALTH_OFFICER_PERSONA}\n\n"
            "Respond with ONLY a JSON array of 3-5 specific, actionable recommendations "
            "for the given heat emergency. No prose."
        )
        user = (
            f"Zone: {zone}\nSeverity: {severity}\nHeat index: {heat_index}°C\n"
            f"Humidity: {env_data.get('relative_humidity_percent', 'n/a')}%\n"
            f"AQI: {env_data.get('air_quality:idx', 'n/a')}\n"
            "Recommendations:"
        )
        try:
            text, _ms = timed_complete(self.llm, system, user, max_tokens=300, temperature=0.3)
            parsed = extract_json(text)
            items = parsed if isinstance(parsed, list) else parsed.get("recommendations", [])
            if isinstance(items, list) and items:
                return [str(r)[:160] for r in items[:5]]
        except LLMError as e:
            logger.warning("LLM recommendations failed, using fallback: %s", e)

        return fallback

    def _hardcoded_recommendations(self, severity: str) -> list:
        recommendations = []
        if severity in ("extreme", "dangerous"):
            recommendations.extend(
                [
                    "Evacuate outdoor workers immediately",
                    "Open all available cooling centers",
                    "Issue public heat emergency warning",
                    "Activate emergency water distribution",
                ]
            )
        elif severity == "emergency":
            recommendations.extend(
                [
                    "Relocate outdoor workers to shaded areas",
                    "Increase water supply at work sites",
                    "Issue heat advisory to public",
                ]
            )
        elif severity == "warning":
            recommendations.extend(
                [
                    "Ensure water availability for outdoor workers",
                    "Schedule rest breaks in shaded areas",
                    "Monitor conditions closely",
                ]
            )
        return recommendations

    def _format_response(self, severity: str, heat_index: float, recommendations: list) -> str:
        severity_label = {
            "extreme": "EXTREME",
            "dangerous": "DANGEROUS",
            "emergency": "EMERGENCY",
            "warning": "WARNING",
            "normal": "NORMAL",
        }
        lines = [
            f"**{severity_label.get(severity, 'UNKNOWN')} HEAT ALERT**",
            f"Heat Index: {heat_index}°C\n",
            "**Recommended Actions:**",
        ]
        for i, rec in enumerate(recommendations, 1):
            lines.append(f"  {i}. {rec}")
        return "\n".join(lines)
