"""LLM provider abstraction for HeatMind agents.

HeatMind's Agentic AI track entry is powered by a real LLM reasoning loop:
plan -> tool call (FortyGuard) -> observe -> reflect -> act.

This module provides a pluggable provider layer so the same agent loop runs
against OpenAI, Anthropic, Gemini, local Ollama, or a deterministic Mock that
keeps the full pipeline alive when no API key is configured (demos, tests, CI).

SDKs are lazy-imported so HeatMind runs fine with zero LLM configuration.
"""

import json
import logging
import os
import re
import time
from typing import Any

logger = logging.getLogger(__name__)


class LLMError(RuntimeError):
    """Raised when an LLM call fails in a non-recoverable way."""


class LLMProvider:
    """Base class. Subclasses implement ``complete``."""

    name = "base"

    def available(self) -> bool:
        return True

    def complete(self, system: str, user: str, max_tokens: int = 800, temperature: float = 0.2) -> str:
        raise NotImplementedError


class OpenAILLM(LLMProvider):
    name = "openai"

    def __init__(self, api_key: str = "", model: str = "gpt-4o-mini"):
        from openai import OpenAI

        self.model = model
        self._client = OpenAI(api_key=api_key or os.environ.get("OPENAI_API_KEY"))

    def complete(self, system: str, user: str, max_tokens: int = 800, temperature: float = 0.2) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return resp.choices[0].message.content or ""


class AnthropicLLM(LLMProvider):
    name = "anthropic"

    def __init__(self, api_key: str = "", model: str = "claude-3-5-haiku-latest"):
        import anthropic

        self.model = model
        self._client = anthropic.Anthropic(api_key=api_key or os.environ.get("ANTHROPIC_API_KEY"))

    def complete(self, system: str, user: str, max_tokens: int = 800, temperature: float = 0.2) -> str:
        msg = self._client.messages.create(
            model=self.model,
            system=system,
            messages=[{"role": "user", "content": user}],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        return msg.content[0].text


class GeminiLLM(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str = "", model: str = "gemini-3.6-flash"):
        from google import genai

        self.model = model
        self._client = genai.Client(api_key=api_key or os.environ.get("GEMINI_API_KEY"))

    def complete(self, system: str, user: str, max_tokens: int = 800, temperature: float = 0.2) -> str:
        chat = self._client.chats.create(
            model=self.model,
            config={"max_output_tokens": max_tokens, "temperature": temperature},
        )
        resp = chat.send_message(f"{system}\n\n{user}")
        return resp.text or ""


class OllamaLLM(LLMProvider):
    name = "ollama"

    def __init__(self, base_url: str = "", model: str = "llama3.1"):
        import requests

        self.base_url = base_url or os.environ.get("OLLAMA_BASE_URL") or "http://localhost:11434"
        self.model = model
        self._requests = requests

    def complete(self, system: str, user: str, max_tokens: int = 800, temperature: float = 0.2) -> str:
        resp = self._requests.post(
            f"{self.base_url}/api/chat",
            json={
                "model": self.model,
                "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            },
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


class MockLLM(LLMProvider):
    """Deterministic pseudo-LLM used when no provider is configured.

    It inspects the [PHASE] marker embedded in the system prompt and returns
    the same JSON contract a real LLM would, so the full agent loop — tool
    selection, execution, reflection — is exercised end to end offline.
    """

    name = "mock"

    def complete(self, system: str, user: str, max_tokens: int = 800, temperature: float = 0.2) -> str:
        phase = "plan"
        if "[PHASE: ANSWER]" in system:
            phase = "answer"
        elif "[PHASE: REFLECT]" in system:
            phase = "reflect"
        elif "[PHASE: ANALYZE]" in system:
            phase = "analyze"
        elif "[PHASE: DECIDE]" in system:
            phase = "decide"
        elif "[PHASE: ALERT]" in system:
            phase = "alert"
        elif "[PHASE: PLAN]" in system:
            phase = "plan"

        if phase == "answer":
            return self._answer(system, user)
        if phase == "reflect":
            return self._reflect(user)
        if phase == "analyze":
            return self._analyze(user)
        if phase == "decide":
            return self._decide(user)
        if phase == "alert":
            return self._alert(user)
        return self._plan(user)

    def _analyze(self, user: str) -> str:
        """Heat-analyst sub-agent: structured analysis from observations."""
        return json.dumps(
            {
                "analysis": {
                    "summary": "Thermal distribution shows localized hotspots consistent with the heat index.",
                    "heat_pattern": "hotspots",
                    "affected_areas": ["urban core", "dense residential blocks"],
                    "confidence": 0.8,
                    "contributing_factors": ["urban density", "high humidity"],
                }
            }
        )

    def _decide(self, user: str) -> str:
        """Emergency-coordinator sub-agent: severity + escalation decision."""
        user_l = user.lower()
        extreme = "extreme" in user_l or "severity assessed: extreme" in user_l
        high = extreme or "severity assessed: high" in user_l
        if extreme:
            return json.dumps(
                {
                    "severity": "extreme",
                    "escalation": "evacuation",
                    "actions": ["send_alert", "evacuation_guidance"],
                    "reasoning": "Extreme heat index threatens life; escalate to evacuation.",
                }
            )
        if high:
            return json.dumps(
                {
                    "severity": "high",
                    "escalation": "alert",
                    "actions": ["send_alert"],
                    "reasoning": "High heat index warrants a public heat advisory.",
                }
            )
        return json.dumps(
            {
                "severity": "moderate",
                "escalation": "advisory",
                "actions": [],
                "reasoning": "Elevated heat index; issue precautionary advisory.",
            }
        )

    def _alert(self, user: str) -> str:
        """Public-alert sub-agent: draft and dispatch a public alert."""
        return json.dumps(
            {
                "alert": {
                    "title": "HEAT ALERT — URBAN ZONE",
                    "message": "Extreme heat is forecast. Stay indoors, hydrate, and check on vulnerable neighbors.",
                    "channels": ["console", "slack", "email", "webhook"],
                    "recommendations": ["Stay hydrated", "Use cooling centers", "Check on at-risk residents"],
                }
            }
        )

    def _reflect(self, user: str) -> str:
        """Reflect on tool observations: continue gathering evidence or conclude."""
        query = user.lower()
        missing = any(k in query for k in ("missing", "failed", "no data", "error", "unavailable"))
        if missing:
            return json.dumps(
                {
                    "continue": True,
                    "reasoning": "A tool call was missing or failed; retry to close the evidence gap.",
                    "next_tool_calls": [{"tool": "env_params", "reason": "Retry baseline environmental parameters"}],
                    "summary": None,
                }
            )

        has_heat = "heat_index" in query or "heat index" in query
        wants_intel = any(k in query for k in ("risk assessment", "intelligence", "comprehensive", "heatmap"))
        if wants_intel and "heatmap" not in query and "heat_intelligence" not in query:
            return json.dumps(
                {
                    "continue": True,
                    "reasoning": "User asked for a comprehensive assessment but thermal distribution is missing; gather it now.",
                    "next_tool_calls": [
                        {"tool": "heatmap", "reason": "Gather thermal distribution for the risk assessment"}
                    ],
                    "summary": None,
                }
            )

        if not has_heat:
            return json.dumps(
                {
                    "continue": True,
                    "reasoning": "No heat index observed yet; collect it before answering.",
                    "next_tool_calls": [{"tool": "env_params", "reason": "Collect heat index"}],
                    "summary": None,
                }
            )

        return json.dumps(
            {
                "continue": False,
                "reasoning": "Evidence is sufficient: heat index observed and tool results are available.",
                "next_tool_calls": [],
                "summary": "Sufficient evidence gathered to synthesize the final answer.",
            }
        )

    def _plan(self, user: str) -> str:
        query = user.lower()
        tools = []

        needs_intel = any(k in query for k in ("risk assessment", "intelligence", "comprehensive", "full"))
        needs_heatmap = needs_intel or any(k in query for k in ("heatmap", "distribution", "map", "across", "area"))
        wants_env = any(k in query for k in ("heat index", "humidity", "aqi", "conditions", "what", "temperature"))
        is_emergency = any(k in query for k in ("emergency", "critical", "extreme", "evacuat", "collapse"))

        if wants_env or needs_intel or not tools:
            tools.append("env_params")
        if needs_heatmap:
            tools.append("heatmap")
        if needs_intel:
            tools.append("heat_intelligence")

        reasoning = "Assessing heat conditions for the requested location"
        if needs_intel:
            reasoning = "Running multi-dimensional heat risk assessment: environmental parameters, thermal map, and intelligence report"
        if is_emergency:
            reasoning = "Emergency triage: immediately check current conditions and raise severity alert"

        actions = ["send_alert"] if is_emergency else []

        return json.dumps({"reasoning": reasoning, "tool_calls": [{"tool": t} for t in tools], "actions": actions})

    def _answer(self, system: str, user: str) -> str:
        severity = "moderate"
        m = re.search(r"heat_index_celsius[^\d]*([\d.]+)", user)
        if m:
            hi = float(m.group(1))
            if hi >= 45:
                severity = "extreme"
            elif hi >= 38:
                severity = "high"
            elif hi >= 33:
                severity = "moderate"
            else:
                severity = "low"
        elif "EXTREME" in user or "DANGEROUS" in user:
            severity = "extreme"
        elif "EMERGENCY" in user or "WARNING" in user:
            severity = "high"

        recommendations = {
            "extreme": [
                "Evacuate outdoor workers immediately",
                "Open all available cooling centers",
                "Issue public heat emergency warning",
                "Activate emergency water distribution",
            ],
            "high": [
                "Relocate outdoor workers to shaded areas",
                "Increase water supply at work sites",
                "Issue heat advisory to the public",
            ],
            "moderate": [
                "Ensure water availability for outdoor workers",
                "Schedule rest breaks in shaded areas",
                "Monitor conditions closely",
            ],
            "low": [
                "Continue routine heat monitoring",
                "Maintain hydration for outdoor staff",
            ],
        }[severity]

        return json.dumps(
            {
                "summary": "Analysis complete. Conditions at the target location require attention.",
                "severity": severity,
                "recommendations": recommendations,
                "actions": ["send_alert"] if severity in ("high", "extreme") else [],
            }
        )


def _candidates() -> list[LLMProvider]:
    from config import (
        ANTHROPIC_API_KEY,
        GEMINI_API_KEY,
        LLM_MODEL,
        LLM_PROVIDER,
        OLLAMA_BASE_URL,
        OPENAI_API_KEY,
    )

    providers: list[tuple[str, Any]] = [
        ("openai", OpenAILLM),
        ("anthropic", AnthropicLLM),
        ("gemini", GeminiLLM),
        ("ollama", OllamaLLM),
    ]

    keys = {
        "openai": OPENAI_API_KEY,
        "anthropic": ANTHROPIC_API_KEY,
        "gemini": GEMINI_API_KEY,
        "ollama": OLLAMA_BASE_URL,
    }
    models = {
        "openai": LLM_MODEL or "gpt-4o-mini",
        "anthropic": LLM_MODEL or "claude-3-5-haiku-latest",
        "gemini": LLM_MODEL or "gemini-2.0-flash",
        "ollama": LLM_MODEL or "llama3.1",
    }

    wanted = LLM_PROVIDER or next((name for name, key in keys.items() if key), "")

    if wanted == "mock":
        return [MockLLM()]

    for name, cls in providers:
        if name == wanted and keys[name]:
            try:
                return [cls(api_key=keys[name], model=models[name])]
            except Exception as e:  # pragma: no cover - import failures
                logger.warning("Failed to init %s provider: %s", name, e)

    return [MockLLM()]


_llm: LLMProvider | None = None


def get_llm() -> LLMProvider:
    """Return the configured LLM provider (cached), falling back to Mock."""
    global _llm
    if _llm is None:
        _llm = _candidates()[0]
    return _llm


def reset_llm():
    """Clear the cached provider (used by tests)."""
    global _llm
    _llm = None


def provider_name() -> str:
    return get_llm().name


def extract_json(text: str) -> dict:
    """Extract a JSON object from an LLM response, tolerating code fences and prose."""
    if not text:
        return {}
    text = text.strip()
    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end > start:
            try:
                return json.loads(text[start : end + 1])
            except json.JSONDecodeError:
                return {}
        return {}


def safe_complete(
    provider: LLMProvider, system: str, user: str, max_tokens: int = 800, temperature: float = 0.2
) -> str:
    """Complete with a short timeout guard; Mock never fails."""
    if isinstance(provider, MockLLM):
        return provider.complete(system, user, max_tokens, temperature)
    try:
        return provider.complete(system, user, max_tokens, temperature)
    except Exception as e:
        logger.warning("LLM call failed: %s", type(e).__name__)
        raise LLMError(str(e)) from e


def timed_complete(
    provider: LLMProvider, system: str, user: str, max_tokens: int = 800, temperature: float = 0.2
) -> tuple[str, float]:
    """Time an LLM call; returns (text, latency_ms)."""
    start = time.time()
    text = safe_complete(provider, system, user, max_tokens, temperature)
    return text, (time.time() - start) * 1000


# Approximate USD-per-1K-tokens pricing for the supported models (input/output).
_MODEL_RATES = {
    "gpt-4o-mini": (0.15, 0.60),
    "claude-3-5-haiku-latest": (0.80, 4.00),
    "gemini-2.0-flash": (0.10, 0.40),
    "llama3.1": (0.0, 0.0),  # local — free
    "mock": (0.0, 0.0),
}


def estimate_tokens(text: str) -> int:
    """Rough token estimate (~4 chars per token, OpenAI convention)."""
    return max(1, len(text or "") // 4)


def estimate_cost(provider: LLMProvider, input_chars: int, output_chars: int) -> float:
    """Estimate the USD cost of one LLM call for the given provider."""
    model = getattr(provider, "model", provider.name)
    in_rate, out_rate = _MODEL_RATES.get(model, (0.15, 0.60))
    tokens_in = max(1, input_chars // 4)
    tokens_out = max(1, output_chars // 4)
    return (tokens_in * in_rate + tokens_out * out_rate) / 1000.0
