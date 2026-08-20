"""Multi-Agent Persona Debate — structured disagreement before synthesis.

Six specialist personas debate high-severity queries before the final answer.
Each persona has a unique lens (spatial, health, urban, cost, emergency, risk).
A selector picks 3-4 relevant personas by severity and context, collects their
opinions, then synthesizes consensus and dissent.

Uses the existing ``get_llm()`` / ``extract_json()`` from ``utils.llm``.
When the LLM is Mock, deterministic debate results are returned.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from utils.llm import MockLLM, extract_json, get_llm

logger = logging.getLogger(__name__)


@dataclass
class DebateOpinion:
    """One persona's opinion during the debate."""

    persona: str
    opinion: str
    recommended_action: str


@dataclass
class DebateResult:
    """Structured output of a multi-persona debate."""

    opinions: list[DebateOpinion] = field(default_factory=list)
    consensus_action: str = ""
    dissent: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "opinions": [
                {"persona": o.persona, "opinion": o.opinion, "recommended_action": o.recommended_action}
                for o in self.opinions
            ],
            "consensus_action": self.consensus_action,
            "dissent": self.dissent,
        }


# ---------------------------------------------------------------------------
# Persona definitions
# ---------------------------------------------------------------------------

PERSONAS: dict[str, dict[str, str]] = {
    "geo_analyst": {
        "name": "Geo Analyst",
        "role": "Spatial Data Scientist",
        "system_prompt": (
            "You are a spatial data scientist analyzing urban heat patterns. "
            "Focus on thermal distribution statistics: min/max/mean temperatures, "
            "hotspot clustering, spatial autocorrelation, and exceedance patterns. "
            "Always cite specific numbers from the observations. "
            'Return a JSON object: {"opinion": "...", "recommended_action": "..."}'
        ),
    },
    "health_officer": {
        "name": "Health Officer",
        "role": "Public Health Specialist",
        "system_prompt": (
            "You are a public health officer coordinating heat-emergency response. "
            "Focus on vulnerable populations: elderly, outdoor workers, children, "
            "people with chronic conditions. Classify severity honestly and never "
            "overstate a finding. Every recommendation must be actionable and specific. "
            'Return a JSON object: {"opinion": "...", "recommended_action": "..."}'
        ),
    },
    "urban_planner": {
        "name": "Urban Planner",
        "role": "Infrastructure Specialist",
        "system_prompt": (
            "You are an urban planner assessing infrastructure resilience. "
            "Focus on urban heat island effects: pavement, building density, "
            "green space deficit, HVAC load, and transit exposure. "
            "Recommend structural interventions. "
            'Return a JSON object: {"opinion": "...", "recommended_action": "..."}'
        ),
    },
    "cost_optimizer": {
        "name": "Cost Optimizer",
        "role": "Economic Analyst",
        "system_prompt": (
            "You are an economic analyst optimizing intervention costs. "
            "Focus on cost-effectiveness: budget constraints, resource allocation, "
            "ROI of cooling measures, and trade-offs between immediate and long-term spending. "
            'Return a JSON object: {"opinion": "...", "recommended_action": "..."}'
        ),
    },
    "emergency_coordinator": {
        "name": "Emergency Coordinator",
        "role": "Crisis Manager",
        "system_prompt": (
            "You are an emergency coordinator managing immediate crisis response. "
            "Focus on life-safety: evacuation routes, cooling center capacity, "
            "emergency communication channels, and resource deployment speed. "
            'Return a JSON object: {"opinion": "...", "recommended_action": "..."}'
        ),
    },
    "risk_assessor": {
        "name": "Risk Assessor",
        "role": "Probabilistic Risk Analyst",
        "system_prompt": (
            "You are a probabilistic risk analyst. "
            "Focus on likelihood and impact: what is the probability of adverse outcomes, "
            "what are the worst-case scenarios, and how do confidence intervals affect recommendations? "
            'Return a JSON object: {"opinion": "...", "recommended_action": "..."}'
        ),
    },
}

# ---------------------------------------------------------------------------
# Persona selection by severity / context
# ---------------------------------------------------------------------------

_SEVERITY_PERSONAS: dict[str, list[str]] = {
    "extreme": ["emergency_coordinator", "health_officer", "risk_assessor", "geo_analyst"],
    "high": ["health_officer", "urban_planner", "cost_optimizer", "emergency_coordinator"],
    "moderate": ["geo_analyst", "urban_planner", "cost_optimizer"],
    "low": ["geo_analyst", "risk_assessor"],
}

_CONTEXT_KEYWORDS: dict[str, list[str]] = {
    "evacuation": ["emergency_coordinator", "health_officer", "risk_assessor"],
    "infrastructure": ["urban_planner", "cost_optimizer"],
    "cost": ["cost_optimizer", "urban_planner"],
    "vulnerable": ["health_officer", "emergency_coordinator"],
    "spatial": ["geo_analyst", "urban_planner"],
}


def select_personas(severity: str, query: str) -> list[str]:
    """Pick 3-4 relevant personas based on severity and query context."""
    candidates = list(_SEVERITY_PERSONAS.get(severity, _SEVERITY_PERSONAS["moderate"]))

    query_lower = query.lower()
    for keyword, extra in _CONTEXT_KEYWORDS.items():
        if keyword in query_lower:
            for p in extra:
                if p not in candidates:
                    candidates.append(p)

    return candidates[:4]


# ---------------------------------------------------------------------------
# Mock debate (deterministic, no LLM calls)
# ---------------------------------------------------------------------------

_MOCK_DEBATES: dict[str, dict[str, dict[str, str]]] = {
    "extreme": {
        "emergency_coordinator": {
            "opinion": "Extreme heat index demands immediate evacuation of outdoor workers.",
            "recommended_action": "Activate emergency evacuation protocol.",
        },
        "health_officer": {
            "opinion": "Vulnerable populations face life-threatening risk; cooling centers must open now.",
            "recommended_action": "Open all cooling centers and deploy medical teams.",
        },
        "risk_assessor": {
            "opinion": "Probability of heatstroke exceeds 40% in exposed areas; high-confidence emergency.",
            "recommended_action": "Issue public heat emergency warning immediately.",
        },
        "geo_analyst": {
            "opinion": "Thermal distribution shows 48.7°C max with tight clustering in urban core.",
            "recommended_action": "Focus evacuation on hotspot zones identified by spatial analysis.",
        },
    },
    "high": {
        "health_officer": {
            "opinion": "Outdoor workers and elderly at significant risk; targeted advisories needed.",
            "recommended_action": "Issue heat advisory targeting high-risk groups.",
        },
        "urban_planner": {
            "opinion": "Urban heat island effect intensifies exposure in dense corridors.",
            "recommended_action": "Deploy misting stations in high-density pedestrian zones.",
        },
        "cost_optimizer": {
            "opinion": "Targeted interventions offer better ROI than area-wide measures.",
            "recommended_action": "Allocate budget to water distribution and shade structures.",
        },
        "emergency_coordinator": {
            "opinion": "Conditions warrant heightened alert but full evacuation is premature.",
            "recommended_action": "Activate heat advisory and increase monitoring frequency.",
        },
    },
    "moderate": {
        "geo_analyst": {
            "opinion": "Thermal map shows moderate variation; no extreme hotspots detected.",
            "recommended_action": "Continue monitoring with standard spatial analysis cadence.",
        },
        "urban_planner": {
            "opinion": "Infrastructure load is elevated but within design tolerances.",
            "recommended_action": "Review HVAC scheduling to reduce peak demand.",
        },
        "cost_optimizer": {
            "opinion": "Preventive measures are cost-effective at this severity level.",
            "recommended_action": "Ensure water availability and schedule rest breaks.",
        },
    },
    "low": {
        "geo_analyst": {
            "opinion": "Conditions are within normal range; no anomalies detected.",
            "recommended_action": "Maintain routine monitoring schedule.",
        },
        "risk_assessor": {
            "opinion": "Probability of adverse outcomes is below 5%; no escalation needed.",
            "recommended_action": "Continue standard operations with periodic checks.",
        },
    },
}


def _mock_debate(severity: str, personas: list[str]) -> DebateResult:
    """Return deterministic debate results for mock LLM."""
    pool = _MOCK_DEBATES.get(severity, _MOCK_DEBATES["moderate"])
    opinions = []
    for p_id in personas:
        data = pool.get(p_id)
        if not data:
            continue
        opinions.append(
            DebateOpinion(persona=p_id, opinion=data["opinion"], recommended_action=data["recommended_action"])
        )

    if not opinions:
        opinions.append(
            DebateOpinion(
                persona="geo_analyst",
                opinion="Insufficient data for detailed debate.",
                recommended_action="Gather more observations.",
            )
        )

    consensus = opinions[0].recommended_action if opinions else "Continue monitoring."
    dissent = ""
    if len(opinions) >= 2:
        actions = [o.recommended_action for o in opinions]
        if len(set(actions)) > 1:
            dissent = f"Disagreement on action: {' vs '.join(actions[:2])}"

    return DebateResult(opinions=opinions, consensus_action=consensus, dissent=dissent)


# ---------------------------------------------------------------------------
# Real LLM debate
# ---------------------------------------------------------------------------


def _debate_persona(persona_id: str, query: str, observations: dict[str, Any]) -> DebateOpinion:
    """Get one persona's opinion via the LLM."""
    persona = PERSONAS[persona_id]
    llm = get_llm()

    system = persona["system_prompt"]
    user = f"Query: {query}\n\nObservations:\n{observations}\n\nGive your 1-2 sentence opinion and recommended action as JSON."

    try:
        text = llm.complete(system, user, max_tokens=200, temperature=0.3)
        data = extract_json(text)
        return DebateOpinion(
            persona=persona_id,
            opinion=data.get("opinion", "Unable to form opinion."),
            recommended_action=data.get("recommended_action", "Continue monitoring."),
        )
    except Exception as e:
        logger.warning("Debate persona %s failed: %s", persona_id, e)
        return DebateOpinion(
            persona=persona_id,
            opinion="Unable to form opinion due to error.",
            recommended_action="Continue monitoring.",
        )


def _llm_debate(severity: str, query: str, observations: dict[str, Any], personas: list[str]) -> DebateResult:
    """Run a real LLM debate across selected personas."""
    opinions = [_debate_persona(p, query, observations) for p in personas]

    if not opinions:
        return DebateResult(consensus_action="Continue monitoring.", dissent="No opinions gathered.")

    consensus = opinions[0].recommended_action
    dissent = ""
    actions = [o.recommended_action for o in opinions]
    if len(set(actions)) > 1:
        dissent = f"Disagreement on action: {' vs '.join(actions[:2])}"

    return DebateResult(opinions=opinions, consensus_action=consensus, dissent=dissent)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_debate(
    query: str,
    observations: dict[str, Any],
    severity: str = "moderate",
) -> dict[str, Any]:
    """Run a multi-persona debate and return structured results.

    Parameters
    ----------
    query:
        The user's original query or scenario description.
    observations:
        Tool observations (env_params, heatmap stats, etc.).
    severity:
        Current severity level (low / moderate / high / extreme).

    Returns
    -------
    dict with keys: opinions, consensus_action, dissent.
    """
    severity = severity.lower() if severity else "moderate"
    if severity not in _SEVERITY_PERSONAS:
        severity = "moderate"

    personas = select_personas(severity, query)

    llm = get_llm()
    if isinstance(llm, MockLLM):
        result = _mock_debate(severity, personas)
    else:
        result = _llm_debate(severity, query, observations, personas)

    return result.to_dict()
