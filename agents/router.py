import re
from enum import Enum
from dataclasses import dataclass


class QueryComplexity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    COMPLEX = "complex"


class QueryUrgency(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class RoutingDecision:
    complexity: QueryComplexity
    urgency: QueryUrgency
    agent: str
    reasoning: str
    recommended_model: str
    confidence: float


COMPLEXITY_KEYWORDS = {
    QueryComplexity.SIMPLE: [
        "what is", "what's", "current", "right now", "today",
        "temperature", "heat index", "humidity",
    ],
    QueryComplexity.MODERATE: [
        "compare", "trend", "history", "this week", "forecast",
        "analysis", "report",
    ],
    QueryComplexity.COMPLEX: [
        "full assessment", "comprehensive", "deep dive", "intelligence",
        "risk assessment", "multi-day", "satellite", "streetview",
    ],
}

URGENCY_KEYWORDS = {
    QueryUrgency.CRITICAL: [
        "emergency", "dangerous", "extreme", "immediate", "now",
        "crisis", "evacuation",
    ],
    QueryUrgency.HIGH: [
        "alert", "warning", "high risk", "exceed", "threshold",
        "unsafe", "hazardous",
    ],
    QueryUrgency.MEDIUM: [
        "should i", "concerned", "worried", "check", "monitor",
    ],
    QueryUrgency.LOW: [
        "show me", "display", "list", "general", "overview",
    ],
}

MODEL_ROUTING = {
    (QueryComplexity.SIMPLE, QueryUrgency.LOW): "env_params",
    (QueryComplexity.SIMPLE, QueryUrgency.MEDIUM): "env_params",
    (QueryComplexity.MODERATE, QueryUrgency.LOW): "env_params + heatmap",
    (QueryComplexity.MODERATE, QueryUrgency.MEDIUM): "env_params + heatmap",
    (QueryComplexity.COMPLEX, QueryUrgency.LOW): "env_params + heatmap + heat_intelligence",
    (QueryComplexity.COMPLEX, QueryUrgency.MEDIUM): "env_params + heatmap + heat_intelligence",
}


def keyword_match(keyword, text):
    return bool(re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE))


def classify_complexity(query: str) -> QueryComplexity:
    """Classify query complexity based on keyword matching."""
    query_lower = query.lower()
    scores = {level: 0 for level in QueryComplexity}

    for level, keywords in COMPLEXITY_KEYWORDS.items():
        for keyword in keywords:
            if keyword_match(keyword, query_lower):
                scores[level] += 1

    max_score = max(scores.values())
    if max_score == 0:
        return QueryComplexity.SIMPLE

    for level, score in scores.items():
        if score == max_score:
            return level

    return QueryComplexity.SIMPLE


def classify_urgency(query: str) -> QueryUrgency:
    """Classify query urgency based on keyword matching."""
    query_lower = query.lower()
    scores = {level: 0 for level in QueryUrgency}

    for level, keywords in URGENCY_KEYWORDS.items():
        for keyword in keywords:
            if keyword_match(keyword, query_lower):
                scores[level] += 1

    max_score = max(scores.values())
    if max_score == 0:
        return QueryUrgency.LOW

    for level, score in scores.items():
        if score == max_score:
            return level

    return QueryUrgency.LOW


def calculate_confidence(complexity: QueryComplexity, urgency: QueryUrgency) -> float:
    """Calculate routing confidence based on score clarity."""
    base = 0.7
    if urgency in (QueryUrgency.CRITICAL, QueryUrgency.HIGH):
        base = 0.9
    elif complexity == QueryComplexity.COMPLEX:
        base = 0.85
    return base


def get_model_recommendation(complexity: QueryComplexity, urgency: QueryUrgency) -> str:
    """Get API endpoint recommendation based on complexity (like customer-support-agent)."""
    if urgency in (QueryUrgency.CRITICAL, QueryUrgency.HIGH):
        return "env_params + emergency_alert"

    key = (complexity, urgency)
    return MODEL_ROUTING.get(key, "env_params")


def route_query(query: str) -> RoutingDecision:
    """Route a query to the appropriate agent based on complexity and urgency."""
    complexity = classify_complexity(query)
    urgency = classify_urgency(query)
    confidence = calculate_confidence(complexity, urgency)
    model = get_model_recommendation(complexity, urgency)

    if urgency in (QueryUrgency.CRITICAL, QueryUrgency.HIGH):
        agent = "emergency"
    elif complexity == QueryComplexity.COMPLEX:
        agent = "deep"
    elif complexity == QueryComplexity.MODERATE:
        agent = "deep"
    else:
        agent = "quick"

    reasoning = f"Complexity: {complexity.value}, Urgency: {urgency.value}, Model: {model}"

    return RoutingDecision(
        complexity=complexity,
        urgency=urgency,
        agent=agent,
        reasoning=reasoning,
        recommended_model=model,
        confidence=confidence,
    )
