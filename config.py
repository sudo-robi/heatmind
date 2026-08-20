import logging
import os
import re

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

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


FORTYGUARD_API_KEY = os.getenv("FORTYGUARD_API_KEY", "")
MONGO_URI = os.getenv("MONGO_URI", "")


LLM_PROVIDER = os.getenv("LLM_PROVIDER", "").lower()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "")
LLM_MODEL = os.getenv("LLM_MODEL", "")

HEATMIND_DEMO_MODE = os.getenv("HEATMIND_DEMO_MODE", "").lower() in ("1", "true", "yes", "demo")

ALERT_WEBHOOK_URL = os.getenv("ALERT_WEBHOOK_URL", "")
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL", "")

if ALERT_WEBHOOK_URL and not ALERT_WEBHOOK_URL.startswith("https://"):
    logger.warning("ALERT_WEBHOOK_URL should use HTTPS to prevent credential leakage")
if SLACK_WEBHOOK_URL and not SLACK_WEBHOOK_URL.startswith("https://"):
    logger.warning("SLACK_WEBHOOK_URL should use HTTPS to prevent credential leakage")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")

MONITOR_INTERVAL_MINUTES = int(os.getenv("MONITOR_INTERVAL_MINUTES", "30"))
HEAT_THRESHOLD_C = float(os.getenv("HEAT_THRESHOLD_C", "40"))
HEAT_INDEX_THRESHOLD = float(os.getenv("HEAT_INDEX_THRESHOLD", "45"))
