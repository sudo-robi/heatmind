import logging
import os
import re

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

# Streamlit Cloud secrets fallback — reads from st.secrets when env vars are empty
def _secret(key: str, default: str = "") -> str:
    """Get config value from env var, falling back to Streamlit secrets."""
    val = os.getenv(key, "")
    if val:
        return val
    try:
        import streamlit as st
        return str(st.secrets.get(key, default))
    except Exception:
        return default

FORTYGUARD_BASE_URL = "https://api.fortyguard.com/v1"

MONGO_DB = os.getenv("MONGO_DB", "heatmind")

# Allowed characters for API keys — prevents injection via malformed keys
_API_KEY_RE = re.compile(r"^[A-Za-z0-9_\-]{1,512}$")


def _validate_mongo_uri():
    """Validate MONGO_URI is set and well-formed. Does NOT log the URI value."""
    uri = os.environ.get("MONGO_URI", "")
    if not uri:
        logger.warning("MONGO_URI not set — running without persistent storage. Set MONGO_URI for production use.")
    elif not re.match(r"^mongodb(\+srv)?://", uri):
        logger.warning("MONGO_URI does not look like a valid MongoDB connection string")


def _validate_api_key():
    """Validate FORTYGUARD_API_KEY is set and well-formed. Does NOT log the key value."""
    key = os.environ.get("FORTYGUARD_API_KEY", "")
    if not key:
        raise ValueError("FORTYGUARD_API_KEY is required. Set it in your .env file or environment.")
    if not _API_KEY_RE.match(key):
        raise ValueError(
            "FORTYGUARD_API_KEY contains invalid characters. Only alphanumeric, dash, and underscore are allowed."
        )


FORTYGUARD_API_KEY = _secret("FORTYGUARD_API_KEY")
MONGO_URI = _secret("MONGO_URI", "")


LLM_PROVIDER = _secret("LLM_PROVIDER", "").lower()
OPENAI_API_KEY = _secret("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = _secret("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = _secret("GEMINI_API_KEY", "")
OLLAMA_BASE_URL = _secret("OLLAMA_BASE_URL", "")
LLM_MODEL = _secret("LLM_MODEL", "")

HEATMIND_DEMO_MODE = _secret("HEATMIND_DEMO_MODE", "").lower() in ("1", "true", "yes", "demo")

ALERT_WEBHOOK_URL = _secret("ALERT_WEBHOOK_URL", "")
SLACK_WEBHOOK_URL = _secret("SLACK_WEBHOOK_URL", "")

if ALERT_WEBHOOK_URL and not ALERT_WEBHOOK_URL.startswith("https://"):
    logger.warning("ALERT_WEBHOOK_URL should use HTTPS to prevent credential leakage")
if SLACK_WEBHOOK_URL and not SLACK_WEBHOOK_URL.startswith("https://"):
    logger.warning("SLACK_WEBHOOK_URL should use HTTPS to prevent credential leakage")

SMTP_HOST = _secret("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(_secret("SMTP_PORT", "587"))
SMTP_USER = _secret("SMTP_USER", "")
SMTP_PASS = _secret("SMTP_PASS", "")
ALERT_EMAIL_TO = _secret("ALERT_EMAIL_TO", "")

MONITOR_INTERVAL_MINUTES = int(_secret("MONITOR_INTERVAL_MINUTES", "30"))
HEAT_THRESHOLD_C = float(_secret("HEAT_THRESHOLD_C", "40"))
HEAT_INDEX_THRESHOLD = float(_secret("HEAT_INDEX_THRESHOLD", "45"))

# Cost-aware routing
DAILY_BUDGET_USD = float(_secret("DAILY_BUDGET_USD", "2.0"))
COST_ROUTING_ENABLED = _secret("COST_ROUTING_ENABLED", "0").lower() in ("1", "true", "yes")

# Event-driven automation
AUTOMATION_ENABLED = _secret("AUTOMATION_ENABLED", "1").lower() in ("1", "true", "yes")

# Human-in-the-loop trust gates
TRUST_THRESHOLD = float(_secret("TRUST_THRESHOLD", "0.6"))
AUTO_APPROVE_ABOVE = float(_secret("AUTO_APPROVE_ABOVE", "0.7"))
