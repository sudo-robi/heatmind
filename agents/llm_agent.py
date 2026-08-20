"""LLMAgent — the Agentic AI reasoning core of HeatMind.

Runs a plan -> tool-call -> observe -> reflect -> act loop powered by an LLM
provider (OpenAI / Anthropic / Gemini / Ollama / Mock). The five FortyGuard
endpoints are exposed as tools; the LLM plans which to call, results are
executed through ``FortyGuardClient``, and a final synthesis produces the
user-facing answer plus severity, recommendations, and optional alerts.

When the LLM is unavailable (no key, provider error, unparsable plan) the agent
degrades gracefully to the deterministic :class:`ChainAgent`, keeping the
system alive — every run emits an honest reasoning trace either way.
"""

import json
import logging
import time
from datetime import UTC, datetime

from agents.chain_agent import ChainAgent
from agents.nlp_parser import parse_query
from agents.router import route_query
from api.fortyguard import FortyGuardClient
from memory.learning import extract_pattern, patterns_to_prompt
from memory.session import SessionMemory
from utils.cost_ledger import CostLedger
from utils.demo import demo_env_params, demo_heat_intelligence, demo_heatmap, demo_satellite, demo_streetview
from utils.llm import LLMError, extract_json, get_llm, timed_complete
from utils.metrics import get_metrics
from utils.personas import (
    TOOL_WHITELIST,
    build_answer_system_prompt,
    build_plan_system_prompt,
    build_reflect_system_prompt,
    build_spec_system_prompt,
)
from utils.validation import flatten_location_data, validate_coords

logger = logging.getLogger(__name__)

DEFAULT_LAT, DEFAULT_LNG = 40.7128, -74.0060
MAX_REFLECTIONS = 2


def summarize_result(data) -> str:
    """Compact, LLM-safe summary of a tool result (truncates geo payloads)."""
    if data is None:
        return "None"
    if isinstance(data, dict):
        parts = []
        for k, v in list(data.items())[:8]:
            if isinstance(v, list):
                parts.append(f"{k}: [{len(v)} items]")
            elif isinstance(v, dict):
                parts.append(f"{k}: {{...{len(v)} keys}}")
            else:
                parts.append(f"{k}: {v}")
        return ", ".join(parts)
    return str(data)[:120]


class LLMAgent:
    def __init__(self, memory=None, llm=None, demo_mode: bool = False):
        self.memory = memory or SessionMemory()
        self.llm = llm or get_llm()
        if demo_mode:
            self._api = None
        else:
            try:
                self._api = FortyGuardClient()
            except ValueError:
                self._api = None
        self._chain = ChainAgent(memory=self.memory)
        self._metrics = get_metrics()
        self._costs = CostLedger()
        self._delegations: list[dict] = []

    # ── Public entry ──────────────────────────────────────────────────────

    def handle(self, query: str, session_id: str, params: dict) -> dict:
        start = time.time()
        parsed = parse_query(query)
        routing = route_query(query)

        lat = params.get("latitude") or parsed.latitude
        lng = params.get("longitude") or parsed.longitude
        if not lat or not lng:
            lat, lng = DEFAULT_LAT, DEFAULT_LNG
            parsed.location = "New York (default)"
        try:
            validate_coords(lat, lng)
        except ValueError:
            lat, lng = DEFAULT_LAT, DEFAULT_LNG

        date = params.get("date") or parsed.date or datetime.now(UTC).strftime("%Y-%m-%d")
        time_of_day = params.get("time") or parsed.time or "14:00"
        zone = params.get("zone") or parsed.location or "unknown"

        self.memory.add_message(session_id, "user", query)
        trace = []

        plan = self._plan(query, routing.agent, parsed.location, lat, lng, date)
        if plan is None:
            return self._fallback(query, session_id, params, routing, reason="llm_plan_unavailable", start=start)

        trace.append(
            {
                "step": 1,
                "action": "Plan analysis strategy",
                "endpoint": "LLM",
                "reason": plan.get("reasoning", "Decide which tools answer the query"),
                "status": "success",
                "result_summary": f"Planned {len(plan.get('tool_calls') or [])} tool call(s)",
            }
        )

        observations, obs_trace = self._execute_calls(
            plan.get("tool_calls") or [], lat, lng, date, time_of_day, zone, start_step=2
        )
        trace.extend(obs_trace)

        # Reflective ReAct loop: inspect observations, gather more if needed.
        for _rnd in range(MAX_REFLECTIONS):
            reflect = self._reflect(query, parsed, observations)
            if reflect is None:
                break
            trace.append(
                {
                    "step": len(trace) + 1,
                    "action": "Reflect on observations",
                    "endpoint": "LLM",
                    "reason": reflect.get("reasoning", "Decide whether more evidence is needed"),
                    "status": "success",
                    "result_summary": (
                        "Evidence sufficient, concluding"
                        if not reflect.get("continue")
                        else f"Gather {len(reflect.get('next_tool_calls') or [])} more result(s)"
                    ),
                }
            )
            next_calls = [
                c
                for c in (reflect.get("next_tool_calls") or [])
                if isinstance(c, dict) and c.get("tool") in TOOL_WHITELIST
            ]
            if not reflect.get("continue") or not next_calls:
                break
            more_obs, more_trace = self._execute_calls(
                next_calls, lat, lng, date, time_of_day, zone, start_step=len(trace) + 1
            )
            observations.update(more_obs)
            trace.extend(more_trace)

        answer = self._synthesize(query, parsed, routing, observations, plan)
        if answer is None:
            return self._fallback(query, session_id, params, routing, reason="llm_answer_unavailable", start=start)

        trace.append(
            {
                "step": len(trace) + 1,
                "action": "Synthesize final answer",
                "endpoint": "LLM",
                "reason": "Combine observations into severity, recommendations, and response",
                "status": "success",
                "result_summary": f"Severity: {answer.get('severity', 'unknown')}",
            }
        )

        # Sub-agent handoffs: delegate dangerous conditions to specialists.
        sev = answer.get("severity", "low")
        if sev in ("high", "extreme"):
            delegation = self._delegate_emergency(query, zone, observations, answer, sev)
            for entry in delegation["trace"]:
                entry["step"] = len(trace) + 1
                trace.append(entry)
            if delegation.get("alert"):
                self._send_alert(zone, delegation["alert"], observations)
                trace.append(
                    {
                        "step": len(trace) + 1,
                        "action": "Trigger alert",
                        "endpoint": "alerts",
                        "reason": "Emergency coordinator authorized autonomous notification",
                        "status": "success",
                        "result_summary": "Alert dispatched via public-alert agent",
                    }
                )
        elif sev == "moderate":
            delegation = self._delegate_analyst(query, observations)
            if delegation["trace"] is not None:
                delegation["trace"]["step"] = len(trace) + 1
                trace.append(delegation["trace"])

        actions = answer.get("actions") or []
        if "send_alert" in actions and sev not in ("high", "extreme"):
            self._send_alert(zone, answer, observations)
            trace.append(
                {
                    "step": len(trace) + 1,
                    "action": "Trigger alert",
                    "endpoint": "alerts",
                    "reason": "Severity warrants autonomous notification",
                    "status": "success",
                    "result_summary": "Alert dispatched",
                }
            )

        response = self._format_response(answer, observations, parsed)
        self.memory.add_message(session_id, "assistant", response)

        # Extract and store learning pattern from this run
        tool_calls_used = [s.get("endpoint", "").replace("POST /v1/", "") for s in trace if s.get("status") == "success" and s.get("endpoint", "").startswith("POST")]
        trace_id = f"tr_{int(start * 1000)}"
        pattern = extract_pattern({
            "trace_id": trace_id,
            "zone": zone,
            "query": query,
            "severity": answer.get("severity", "unknown"),
            "outcome": "success",
            "confidence": plan.get("confidence", 0.7),
            "tool_calls": tool_calls_used,
            "user_feedback": None,
        })
        if pattern:
            try:
                self.memory.record_pattern(pattern)
            except Exception:
                pass  # Non-critical

        self.memory.log_decision(
            session_id,
            query,
            decision=f"llm:{routing.agent}",
            reasoning=plan.get("reasoning", ""),
            outcome="completed",
            extra={
                "trace_id": trace_id,
                "severity": answer.get("severity", "unknown"),
                "llm_mode": self.llm.name,
                "cost_usd": self._costs.total_usd(),
                "delegations": [d["agent"] for d in self._delegations],
                "tool_calls": [s.get("endpoint") for s in trace if s.get("status") == "success"],
            },
        )

        latency_ms = (time.time() - start) * 1000
        self._metrics.record_agent_call("llm", latency_ms, len(query))

        return {
            "agent": "llm",
            "response": response,
            "trace_id": trace_id,
            "raw_data": observations,
            "reasoning": trace,
            "llm_mode": self.llm.name,
            "plan": plan,
            "map_data": {
                "latitude": lat,
                "longitude": lng,
                "zone": zone,
                "heat_index": observations.get("env_params", {}).get("heat_index_celsius"),
                "heatmap": observations.get("heatmap"),
            },
            "api_calls": self._api.get_call_log() if self._api else [],
            "response_time_ms": latency_ms,
            "severity": answer.get("severity", "unknown"),
            "recommendations": answer.get("recommendations", []),
            "cost": self._costs.summary(),
            "delegations": self._delegations,
        }

    # ── Phases ────────────────────────────────────────────────────────────

    def _plan(self, query: str, agent: str, location: str | None, lat: float, lng: float, date: str) -> dict | None:
        # Load learned patterns for this zone/query type
        learned = ""
        try:
            from memory.learning import _classify_query

            query_type = _classify_query(query)
            zone = location or "unknown"
            patterns = self.memory.get_successful_patterns(zone=zone, query_type=query_type, limit=5)
            if patterns:
                learned = patterns_to_prompt(patterns)
        except Exception:
            pass  # Non-critical — proceed without patterns

        system = build_plan_system_prompt(agent, learned_patterns=learned)
        user = f"Location: {location or 'unknown'} ({lat:.4f}, {lng:.4f})\nDate: {date}\nUser query: {query}"
        try:
            text, ms = timed_complete(self.llm, system, user, max_tokens=400, temperature=0.2)
        except LLMError as e:
            logger.warning("Plan phase failed: %s", e)
            return None
        self._costs.record_llm(self.llm, "plan", len(system) + len(user), len(text), ms)
        plan = extract_json(text)
        if not isinstance(plan.get("tool_calls"), list):
            plan["tool_calls"] = []
        return plan

    def _synthesize(self, query: str, parsed, routing, observations: dict, plan: dict) -> dict | None:
        system = build_answer_system_prompt(routing.agent)
        user = self._answer_user(query, parsed, observations, plan)
        try:
            text, ms = timed_complete(self.llm, system, user, max_tokens=800, temperature=0.3)
        except LLMError as e:
            logger.warning("Synthesize phase failed: %s", e)
            return None
        self._costs.record_llm(self.llm, "synthesize", len(system) + len(user), len(text), ms)
        answer = extract_json(text)
        if not answer.get("summary"):
            return None
        return answer

    def _reflect(self, query: str, parsed, observations: dict) -> dict | None:
        system = build_reflect_system_prompt()
        user = f"User query: {query}\nLocation: {parsed.location or 'unknown'}\n" + "\n".join(
            f"--- {tool} ---\n{json.dumps(data, default=str)[:1500]}" for tool, data in observations.items()
        )
        try:
            text, ms = timed_complete(self.llm, system, user, max_tokens=300, temperature=0.2)
        except LLMError as e:
            logger.warning("Reflect phase failed: %s", e)
            return None
        self._costs.record_llm(self.llm, "reflect", len(system) + len(user), len(text), ms)
        return extract_json(text)

    def _answer_user(self, query: str, parsed, observations: dict, plan: dict) -> str:
        lines = [
            f"User query: {query}",
            f"Location: {parsed.location or 'unknown'}",
            f"Original plan: {plan.get('reasoning', '')}",
            "\nObservations from tool calls:",
        ]
        for tool, data in observations.items():
            lines.append(f"--- {tool} ---")
            lines.append(json.dumps(data, default=str)[:2500])
        return "\n".join(lines)

    def _execute_calls(
        self, calls: list, lat: float, lng: float, date: str, time_of_day: str, zone: str, start_step: int = 2
    ) -> tuple[dict, list]:
        observations: dict = {}
        trace: list = []
        for i, call in enumerate(calls[:6], start=start_step):
            if not isinstance(call, dict):
                continue
            tool = call.get("tool")
            if tool not in TOOL_WHITELIST:
                trace.append(
                    {
                        "step": i,
                        "action": f"Call {tool}",
                        "endpoint": "unknown",
                        "reason": "Requested tool is not in the whitelist",
                        "status": "skipped",
                        "result_summary": "Ignored",
                    }
                )
                continue
            args = call.get("args") or {}
            data, err = self._run_tool(tool, args, lat, lng, date, time_of_day)
            observations[tool] = data
            self._costs.record_tool(tool)
            trace.append(
                {
                    "step": i,
                    "action": f"Call {tool}",
                    "endpoint": f"POST /v1/{tool}",
                    "reason": call.get("reason", "Execute planned tool"),
                    "status": "error" if err else "success",
                    "result_summary": err or summarize_result(data),
                }
            )
        return observations, trace

    # ── Tools ─────────────────────────────────────────────────────────────

    def _run_tool(
        self, tool: str, args: dict, lat: float, lng: float, date: str, time_of_day: str
    ) -> tuple[dict, str | None]:
        try:
            if tool == "env_params":
                return self._tool_env_params(args, lat, lng, date, time_of_day)
            if tool == "heatmap":
                return self._tool_heatmap(args, lat, lng, date)
            if tool == "heat_intelligence":
                return self._tool_heat_intelligence(args, lat, lng, date)
            if tool == "satellite":
                return self._tool_satellite(args, lat, lng, date)
            if tool == "streetview":
                return self._tool_streetview(args, lat, lng)
            return {}, "unknown tool"
        except Exception as e:
            logger.warning("%s tool failed (%s); falling back to demo data", tool, type(e).__name__)
            demo = self._demo_for(tool, args, lat, lng, date, time_of_day)
            demo["demo"] = True
            demo["fallback_reason"] = f"{type(e).__name__}: {str(e)[:120]}"
            return demo, None

    def _demo_for(self, tool: str, args, lat: float, lng: float, date: str, time_of_day: str) -> dict:
        if tool == "env_params":
            return demo_env_params(lat, lng)
        if tool == "heatmap":
            return demo_heatmap(lat, lng)
        if tool == "heat_intelligence":
            return demo_heat_intelligence(lat, lng)
        if tool == "satellite":
            return demo_satellite(lat, lng)
        if tool == "streetview":
            return demo_streetview(lat, lng)
        return {}

    def _tool_env_params(self, args, lat, lng, date, time_of_day):
        if self._api is None:
            return demo_env_params(lat, lng), None
        aid = self._api.create_env_params(
            latitude=args.get("latitude", lat),
            longitude=args.get("longitude", lng),
            temperature=args.get("temperature", 35.0),
            start_date=args.get("date", date),
            start_time=args.get("time", time_of_day),
            filter_type=1,
        )
        if not aid:
            return {"error": "No activity_id returned"}, "api_error"
        return flatten_location_data(self._api.wait_for_result(aid, timeout=120)), None

    def _tool_heatmap(self, args, lat, lng, date):
        if self._api is None:
            return demo_heatmap(lat, lng), None
        polygon_aoi = args.get("polygon_aoi") or {
            "type": "FeatureCollection",
            "features": [
                {
                    "type": "Feature",
                    "properties": {},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [
                            [
                                [lng - 0.01, lat - 0.01],
                                [lng + 0.01, lat - 0.01],
                                [lng + 0.01, lat + 0.01],
                                [lng - 0.01, lat + 0.01],
                                [lng - 0.01, lat - 0.01],
                            ]
                        ],
                    },
                }
            ],
        }
        aid = self._api.create_heatmap(
            polygon_aoi=polygon_aoi,
            start_date=args.get("date", date),
            start_time=args.get("time"),
            filter_type=1,
            granularity=args.get("granularity", 100),
        )
        if not aid:
            return {"error": "No activity_id returned"}, "api_error"
        return self._api.wait_for_result(aid, timeout=180), None

    def _tool_heat_intelligence(self, args, lat, lng, date):
        if self._api is None:
            return demo_heat_intelligence(lat, lng), None
        aid = self._api.create_heat_intelligence(
            latitude=args.get("latitude", lat),
            longitude=args.get("longitude", lng),
            temperature=args.get("temperature", 35.0),
            date=args.get("date", date),
            analysis=args.get("analysis", ["geographic", "environmental", "urban"]),
        )
        if not aid:
            return {"error": "No activity_id returned"}, "api_error"
        return self._api.wait_for_result(aid, timeout=300), None

    def _tool_satellite(self, args, lat, lng, date):
        if self._api is None:
            return demo_satellite(lat, lng), None
        aid = self._api.create_satellite(
            latitude=args.get("latitude", lat),
            longitude=args.get("longitude", lng),
            start_date=args.get("date", date),
            start_time=args.get("time"),
            filter_type=1,
            granularity=args.get("granularity", 80),
        )
        if not aid:
            return {"error": "No activity_id returned"}, "api_error"
        return self._api.wait_for_result(aid, timeout=180), None

    def _tool_streetview(self, args, lat, lng):
        if self._api is None:
            return demo_streetview(lat, lng), None
        aid = self._api.create_streetview(
            latitude=args.get("latitude", lat),
            longitude=args.get("longitude", lng),
            vertical_angle=args.get("vertical_angle", 10.0),
            horizontal_angle=args.get("horizontal_angle", 90.0),
            back_view=bool(args.get("back_view", False)),
        )
        if not aid:
            return {"error": "No activity_id returned"}, "api_error"
        return self._api.wait_for_result(aid, timeout=180), None

    # ── Output ────────────────────────────────────────────────────────────

    def _format_response(self, answer: dict, observations: dict, parsed) -> str:
        sev = answer.get("severity", "unknown")
        sev_label = {"low": "LOW", "moderate": "MODERATE", "high": "HIGH", "extreme": "EXTREME"}.get(sev, sev.upper())
        lines = [
            f"**{sev_label} — HeatMind Analysis**\n",
            answer.get("summary", "").strip() or "Analysis complete.",
        ]

        env = observations.get("env_params") or {}
        if env and isinstance(env, dict):
            lines.append("\n**Measured Conditions:**")
            for key, label in [
                ("heat_index_celsius", "Heat Index"),
                ("apparent_temperature_celsius", "Apparent Temp"),
                ("relative_humidity_percent", "Humidity"),
                ("air_quality:idx", "AQI"),
            ]:
                val = env.get(key)
                if isinstance(val, (int, float)):
                    unit = "%" if key == "relative_humidity_percent" else "°C" if "celsius" in key else ""
                    lines.append(f"  - {label}: **{val}{unit}**")

        hm = observations.get("heatmap") or {}
        stats = (hm.get("stats_data") or {}).get("Temperature_stats") if isinstance(hm, dict) else None
        if stats:
            lines.append("\n**Thermal Distribution:**")
            lines.append(
                f"  - Min **{stats.get('Minimum', '—')}°C** · Max **{stats.get('Maximum', '—')}°C** · Mean **{stats.get('Mean', '—')}°C**"
            )

        recs = answer.get("recommendations") or []
        if recs:
            lines.append("\n**Recommended Actions:**")
            for i, rec in enumerate(recs[:5], 1):
                lines.append(f"  {i}. {rec}")

        if observations.get("env_params", {}).get("demo"):
            lines.append("\n_* Demo data (no FORTYGUARD_API_KEY set)._")

        return "\n".join(lines)

    def _send_alert(self, zone: str, answer: dict, observations: dict):
        from utils.alerts import send_alert

        env = observations.get("env_params") or {}
        payload = {
            "zone": zone,
            "severity": answer.get("severity", "unknown"),
            "heat_index": env.get("heat_index_celsius"),
            "timestamp": datetime.now(UTC).isoformat(),
            "recommendations": answer.get("recommendations", []),
        }
        send_alert(payload)
        self._metrics.record_alert_sent()

    # ── Sub-agent delegation ─────────────────────────────────────────────

    def _delegate(self, spec_name: str, phase: str, payload: str) -> dict:
        """Hand off a scoped task to a spec-defined sub-agent.

        Each sub-agent reads its own agents/specs/<name>.md operating manual
        and runs a single phase (DECIDE / ALERT / ANALYZE). Returns
        {result, trace, success} and records the LLM cost in the ledger.
        """
        system = build_spec_system_prompt(spec_name, phase)
        try:
            text, ms = timed_complete(self.llm, system, payload, max_tokens=500, temperature=0.2)
        except LLMError as e:
            logger.warning("Sub-agent %s failed: %s", spec_name, e)
            return {"result": None, "trace": None, "success": False}
        self._costs.record_llm(self.llm, f"{spec_name}:{phase.lower()}", len(system) + len(payload), len(text), ms)
        result = extract_json(text)
        self._delegations.append({"agent": spec_name, "phase": phase, "result": result})
        trace = {
            "step": None,
            "action": f"Delegate to {spec_name}",
            "endpoint": spec_name,
            "reason": f"Handed off {phase.lower()} work to the {spec_name} sub-agent",
            "status": "success" if result else "error",
            "result_summary": (
                f"Sub-agent {spec_name} returned its {phase.lower()} output"
                if result
                else "Sub-agent returned no output"
            ),
        }
        return {"result": result, "trace": trace, "success": bool(result)}

    def _delegate_emergency(self, query: str, zone: str, observations: dict, answer: dict, sev: str) -> dict:
        payload = (
            f"Zone: {zone}\nSeverity assessed: {sev}\n"
            f"Conditions: {summarize_result(observations.get('env_params'))}\n"
            f"Recommendations so far: {answer.get('recommendations') or []}\n"
            f"Task: Decide escalation and the autonomous response plan."
        )
        handoff = self._delegate("emergency-coordinator", "DECIDE", payload)
        traces = []
        if handoff["trace"] is not None:
            traces.append(handoff["trace"])
        alert = None
        if handoff["success"] and isinstance(handoff["result"], dict):
            decision = handoff["result"]
            alert_payload = (
                f"Zone: {zone}\nSeverity: {decision.get('severity') or sev}\n"
                f"Heat index: {observations.get('env_params', {}).get('heat_index_celsius')}\n"
                f"Recommendations: {decision.get('actions') or answer.get('recommendations') or []}\n"
                f"Task: Draft and dispatch the public alert."
            )
            alert_handoff = self._delegate("public-alert", "ALERT", alert_payload)
            if alert_handoff["trace"] is not None:
                traces.append(alert_handoff["trace"])
            if alert_handoff["success"]:
                alert = alert_handoff["result"]
        return {"trace": traces, "alert": alert}

    def _delegate_analyst(self, query: str, observations: dict) -> dict:
        payload = (
            f"User query: {query}\n"
            + "\n".join(
                f"--- {tool} ---\n{json.dumps(data, default=str)[:1200]}" for tool, data in observations.items()
            )
            + "\nTask: Produce a structured heat analysis from these observations."
        )
        return self._delegate("heat-analyst", "ANALYZE", payload)

    # ── Fallback ──────────────────────────────────────────────────────────

    def _fallback(self, query, session_id, params, routing, reason: str, start: float) -> dict:
        logger.info("Falling back to ChainAgent (%s)", reason)
        result = self._chain.execute_chain(
            query=query,
            session_id=session_id,
            endpoints=routing.recommended_model.replace(" + ", ",").split(","),
            params=params,
        )
        result["agent"] = "chain"
        result["llm_mode"] = "fallback"
        result["fallback_reason"] = reason
        result["response_time_ms"] = (time.time() - start) * 1000
        return result
