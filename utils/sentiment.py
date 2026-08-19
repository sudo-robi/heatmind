"""Sentiment analysis for user queries (Winner 4: Customer Support Agent).

Keyword-based sentiment scoring with escalation triggers. Detects frustration,
urgency, and emotional state to inform routing and escalation decisions.
"""

import re
from dataclasses import dataclass
from enum import Enum


class Sentiment(Enum):
    VERY_NEGATIVE = "very_negative"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    VERY_POSITIVE = "very_positive"


@dataclass
class SentimentResult:
    sentiment: Sentiment
    score: float
    escalation_trigger: bool
    emotions: list[str]
    confidence: float


_NEGATIVE_PATTERNS = {
    "frustration": [
        r"\b(annoying|frustrated|frustrating|irritated|fed up|sick of|tired of)\b",
        r"\b(waste of time|useless|broken|doesn't work|not working)\b",
        r"\b(why can't|why won't|this is stupid|terrible)\b",
    ],
    "anger": [
        r"\b(angry|furious|outraged|livid|pissed|mad as)\b",
        r"\b(unacceptable|incompetent|disgraceful|horrible)\b",
        r"\b(refund|cancel|sue|lawyer|report)\b",
    ],
    "fear": [
        r"\b(scared|afraid|terrified|panic|worried sick|life threatening)\b",
        r"\b(dying|death|hospital|ambulance|paramedic)\b",
        r"\b(emergency|critical|dire|catastrophic)\b",
    ],
    "sadness": [
        r"\b(sad|depressed|hopeless|helpless|desperate)\b",
        r"\b(disappointed|let down|heartbroken)\b",
    ],
}

_POSITIVE_PATTERNS = {
    "satisfaction": [
        r"\b(great|excellent|amazing|perfect|wonderful|fantastic)\b",
        r"\b(thank|thanks|appreciate|grateful)\b",
        r"\b(happy|pleased|love it|impressed)\b",
    ],
    "urgency_positive": [
        r"\b(please help|need help|quickly|asap|hurry)\b",
    ],
}

_ESCALATION_KEYWORDS = [
    r"\b(evacuate|evacuation|collapse|collapsing|hospitalized)\b",
    r"\b(death|dying|fatal|casualty|casualties)\b",
    r"\b(lawsuit|legal|attorney|sue)\b",
    r"\b(cancel subscription|cancel account|file complaint)\b",
    r"\b(unsafe|dangerous|hazard|threat to life)\b",
]

_ESCALATION_THRESHOLD = -0.6


def _score_patterns(text: str, pattern_groups: dict[str, list[str]]) -> dict[str, float]:
    scores = {}
    for emotion, patterns in pattern_groups.items():
        count = 0
        for pattern in patterns:
            count += len(re.findall(pattern, text, re.IGNORECASE))
        scores[emotion] = min(count * 0.2, 1.0)
    return scores


def _has_escalation_trigger(text: str) -> bool:
    return any(re.search(pattern, text, re.IGNORECASE) for pattern in _ESCALATION_KEYWORDS)


def analyze_sentiment(text: str) -> SentimentResult:
    negative_scores = _score_patterns(text, _NEGATIVE_PATTERNS)
    positive_scores = _score_patterns(text, _POSITIVE_PATTERNS)

    neg_total = sum(negative_scores.values())
    pos_total = sum(positive_scores.values())

    raw_score = pos_total - neg_total
    score = max(-1.0, min(1.0, raw_score))

    if score <= -0.6:
        sentiment = Sentiment.VERY_NEGATIVE
    elif score <= -0.2:
        sentiment = Sentiment.NEGATIVE
    elif score <= 0.2:
        sentiment = Sentiment.NEUTRAL
    elif score <= 0.6:
        sentiment = Sentiment.POSITIVE
    else:
        sentiment = Sentiment.VERY_POSITIVE

    emotions = [e for e, s in {**negative_scores, **positive_scores}.items() if s > 0]
    escalation = _has_escalation_trigger(text) or score <= _ESCALATION_THRESHOLD

    confidence = min(abs(score) + 0.3, 0.95)
    if not emotions:
        confidence = 0.5

    return SentimentResult(
        sentiment=sentiment,
        score=score,
        escalation_trigger=escalation,
        emotions=emotions,
        confidence=confidence,
    )
