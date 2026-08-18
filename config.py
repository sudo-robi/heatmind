import os

from dotenv import load_dotenv

load_dotenv()

FORTYGUARD_BASE_URL = "https://api.fortyguard.com/v1"

MONGO_DB = os.getenv("MONGO_DB", "heatmind")


def _validate_mongo_uri():
    if not os.environ.get("MONGO_URI"):
        raise ValueError(
            "MONGO_URI is required. Set it in your .env file or environment. "
            "Example: MONGO_URI=mongodb://user:password@host:27017/heatmind"
        )


def _validate_api_key():
    if not os.environ.get("FORTYGUARD_API_KEY"):
        raise ValueError("FORTYGUARD_API_KEY is required. Set it in your .env file or environment.")


FORTYGUARD_API_KEY = os.getenv("FORTYGUARD_API_KEY", "")
MONGO_URI = os.getenv("MONGO_URI", "")


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
