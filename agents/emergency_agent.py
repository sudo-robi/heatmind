from datetime import datetime, timezone
from api.fortyguard import FortyGuardClient
from memory.session import SessionMemory
from utils.alerts import send_alert
from utils.validation import validate_coords


class EmergencyAgent:
    def __init__(self, memory=None):
        self.api = FortyGuardClient()
        self.memory = memory or SessionMemory()

    def handle(self, query: str, session_id: str, params: dict) -> dict:
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

        self.memory.add_message(session_id, "user", query)

        env_id = self.api.create_env_params(
            latitude=latitude,
            longitude=longitude,
            temperature=temperature,
            start_date=date,
            start_time=params.get("time", "14:00"),
            filter_type=1,
        )

        env_data = {}
        if env_id:
            raw = self.api.wait_for_result(env_id)
            env_data = self._flatten_location_data(raw)

        heat_index = env_data.get("heat_index_celsius", temperature)
        if isinstance(heat_index, list):
            heat_index = heat_index[0]
        severity = self._assess_severity(heat_index, env_data)

        recommendations = self._generate_recommendations(severity, env_data)

        alert_payload = {
            "zone": zone,
            "severity": severity,
            "heat_index": heat_index,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "recommendations": recommendations,
        }
        send_alert(alert_payload)

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
        self.memory.add_message(session_id, "assistant", response)

        return {
            "agent": "emergency",
            "severity": severity,
            "response": response,
            "raw_data": {"env_params": env_data, "alert": alert_payload},
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

    def _generate_recommendations(self, severity: str, env_data: dict) -> list:
        recommendations = []
        if severity in ("extreme", "dangerous"):
            recommendations.extend([
                "Evacuate outdoor workers immediately",
                "Open all available cooling centers",
                "Issue public heat emergency warning",
                "Activate emergency water distribution",
            ])
        elif severity == "emergency":
            recommendations.extend([
                "Relocate outdoor workers to shaded areas",
                "Increase water supply at work sites",
                "Issue heat advisory to public",
            ])
        elif severity == "warning":
            recommendations.extend([
                "Ensure water availability for outdoor workers",
                "Schedule rest breaks in shaded areas",
                "Monitor conditions closely",
            ])
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
