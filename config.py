import logging
import os

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

FORTYGUARD_BASE_URL = "https://api.fortyguard.com/v1"

MONGO_DB = os.getenv("MONGO_DB", "heatmind")


def _validate_mongo_uri():
    if not os.environ.get("MONGO_URI"):
        logger.warning("MONGO_URI not set — running without persistent storage. Set MONGO_URI for production use.")


def _validate_api_key():
    if not os.environ.get("FORTYGUARD_API_KEY"):
        raise ValueError("FORTYGUARD_API_KEY is required. Set it in your .env file or environment.")


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

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASS = os.getenv("SMTP_PASS", "")
ALERT_EMAIL_TO = os.getenv("ALERT_EMAIL_TO", "")

MONITOR_INTERVAL_MINUTES = int(os.getenv("MONITOR_INTERVAL_MINUTES", "30"))
HEAT_THRESHOLD_C = float(os.getenv("HEAT_THRESHOLD_C", "40"))
HEAT_INDEX_THRESHOLD = float(os.getenv("HEAT_INDEX_THRESHOLD", "45"))
