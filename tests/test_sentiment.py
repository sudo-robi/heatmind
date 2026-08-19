"""Tests for sentiment analysis."""

from utils.sentiment import Sentiment, SentimentResult, analyze_sentiment


class TestSentimentAnalysis:
    def test_positive_sentiment(self):
        result = analyze_sentiment("This is great and amazing, I love it!")
        assert result.sentiment in (Sentiment.POSITIVE, Sentiment.VERY_POSITIVE)
        assert result.score > 0

    def test_negative_sentiment(self):
        result = analyze_sentiment("This is terrible and awful, I hate it")
        assert result.sentiment in (Sentiment.NEGATIVE, Sentiment.VERY_NEGATIVE)
        assert result.score < 0

    def test_neutral_sentiment(self):
        result = analyze_sentiment("The temperature is 85 degrees")
        assert result.sentiment == Sentiment.NEUTRAL

    def test_escalation_trigger_keywords(self):
        result = analyze_sentiment("This is dangerous, people are dying!")
        assert result.escalation_trigger is True

    def test_escalation_trigger_negative_score(self):
        result = analyze_sentiment("terrible terrible terrible horrible awful")
        assert result.escalation_trigger is True

    def test_no_escalation_trigger(self):
        result = analyze_sentiment("Nice weather today")
        assert result.escalation_trigger is False

    def test_empty_text(self):
        result = analyze_sentiment("")
        assert result.sentiment == Sentiment.NEUTRAL
        assert result.score == 0.0

    def test_returns_sentiment_result(self):
        result = analyze_sentiment("test")
        assert isinstance(result, SentimentResult)

    def test_emotions_detected(self):
        result = analyze_sentiment("I am frustrated and angry about this")
        assert len(result.emotions) > 0

    def test_confidence_range(self):
        result = analyze_sentiment("Great wonderful amazing!")
        assert 0 <= result.confidence <= 1.0


class TestHasEscalationTrigger:
    def test_returns_true_for_emergency_words(self):
        from utils.sentiment import _has_escalation_trigger

        assert _has_escalation_trigger("evacuate immediately") is True
        assert _has_escalation_trigger("people are dying") is True
        assert _has_escalation_trigger("dangerous situation") is True

    def test_returns_false_for_normal_text(self):
        from utils.sentiment import _has_escalation_trigger

        assert _has_escalation_trigger("nice weather") is False
        assert _has_escalation_trigger("temperature is 85") is False
