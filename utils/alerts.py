import logging
import smtplib
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import requests

from config import (
    ALERT_EMAIL_TO,
    ALERT_WEBHOOK_URL,
    SLACK_WEBHOOK_URL,
    SMTP_HOST,
    SMTP_PASS,
    SMTP_PORT,
    SMTP_USER,
)

logger = logging.getLogger(__name__)


def send_slack_alert(payload: dict):
    """Send alert to Slack via incoming webhook."""
    if not SLACK_WEBHOOK_URL:
        return

    severity = payload.get("severity", "unknown").upper()
    zone = payload.get("zone", "unknown")
    heat_index = payload.get("heat_index", "N/A")
    timestamp = payload.get("timestamp", datetime.now(UTC).isoformat())
    recommendations = payload.get("recommendations", [])

    severity_colors = {
        "extreme": "#b71c1c",
        "dangerous": "#e65100",
        "emergency": "#f57f17",
        "warning": "#fbc02d",
        "normal": "#2e7d32",
    }

    color = severity_colors.get(severity, "#666666")

    rec_text = "\n".join(f"• {rec}" for rec in recommendations) if recommendations else "No recommendations"

    slack_message = {
        "attachments": [
            {
                "color": color,
                "blocks": [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": f"🌡️ HeatMind Alert — {severity}",
                            "emoji": True,
                        },
                    },
                    {
                        "type": "section",
                        "fields": [
                            {"type": "mrkdwn", "text": f"*Zone:*\n{zone}"},
                            {"type": "mrkdwn", "text": f"*Heat Index:*\n{heat_index}°C"},
                            {"type": "mrkdwn", "text": f"*Severity:*\n{severity}"},
                            {"type": "mrkdwn", "text": f"*Time:*\n{timestamp}"},
                        ],
                    },
                    {"type": "divider"},
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Recommended Actions:*\n{rec_text}",
                        },
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": "HeatMind — Multi-Agent Heat Intelligence System | FortyGuard Hackathon'26",
                            }
                        ],
                    },
                ],
            }
        ]
    }

    try:
        response = requests.post(
            SLACK_WEBHOOK_URL,
            json=slack_message,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        response.raise_for_status()
        logger.info("Alert sent to Slack")
    except requests.RequestException as e:
        logger.error("Failed to send Slack alert: %s", type(e).__name__)


def send_email_alert(payload: dict):
    """Send alert via email."""
    if not all([SMTP_USER, SMTP_PASS, ALERT_EMAIL_TO]):
        return

    from html import escape as html_escape

    severity = html_escape(payload.get("severity", "unknown").upper())
    zone = html_escape(payload.get("zone", "unknown"))
    heat_index = html_escape(str(payload.get("heat_index", "N/A")))
    timestamp = html_escape(payload.get("timestamp", datetime.now(UTC).isoformat()))
    recommendations = payload.get("recommendations", [])

    subject = f"HeatMind Alert — {severity} — {zone}"

    rec_html = "\n".join(f"<li style='padding: 4px;'>{html_escape(rec)}</li>" for rec in recommendations)

    html = f"""
    <html>
    <body style="font-family: Arial, sans-serif; padding: 20px;">
        <h2 style="color: #d32f2f;">HeatMind Alert — {severity}</h2>
        <table style="border-collapse: collapse; width: 100%; max-width: 600px;">
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Zone</b></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{zone}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Heat Index</b></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{heat_index}°C</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Severity</b></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{severity}</td></tr>
            <tr><td style="padding: 8px; border: 1px solid #ddd;"><b>Time</b></td>
                <td style="padding: 8px; border: 1px solid #ddd;">{timestamp}</td></tr>
        </table>
        <h3 style="margin-top: 20px;">Recommended Actions:</h3>
        <ol>
            {rec_html}
        </ol>
        <p style="color: #666; margin-top: 20px;">HeatMind — Multi-Agent Heat Intelligence System</p>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = SMTP_USER
    msg["To"] = ALERT_EMAIL_TO
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.sendmail(SMTP_USER, ALERT_EMAIL_TO, msg.as_string())
        logger.info("Alert sent to %s", ALERT_EMAIL_TO)
    except Exception as e:
        logger.error("Failed to send email alert: %s", type(e).__name__)


def send_webhook_alert(payload: dict):
    """Send alert to custom webhook (Discord, etc.)."""
    if not ALERT_WEBHOOK_URL:
        return
    try:
        requests.post(
            ALERT_WEBHOOK_URL,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        logger.info("Webhook alert sent")
    except requests.RequestException as e:
        logger.error("Failed to send webhook alert: %s", type(e).__name__)


def send_console_alert(payload: dict):
    """Print alert to console."""
    severity = payload.get("severity", "unknown").upper()
    zone = payload.get("zone", "unknown")
    heat_index = payload.get("heat_index", "N/A")
    timestamp = payload.get("timestamp", datetime.now(UTC).isoformat())
    recommendations = payload.get("recommendations", [])

    print(f"\n{'=' * 60}")
    print(f"HEAT ALERT — {severity}")
    print(f"Zone: {zone}")
    print(f"Heat Index: {heat_index}°C")
    print(f"Time: {timestamp}")
    print("\nRecommendations:")
    for i, rec in enumerate(recommendations, 1):
        print(f"  {i}. {rec}")
    print(f"{'=' * 60}\n")


def send_alert(payload: dict):
    """Send alert to all configured channels in parallel."""
    payload["timestamp"] = datetime.now(UTC).isoformat()
    channels = [
        ("console", send_console_alert),
        ("slack", send_slack_alert),
        ("webhook", send_webhook_alert),
        ("email", send_email_alert),
    ]
    with ThreadPoolExecutor(max_workers=4) as pool:
        list(pool.map(lambda c: c[1](payload), channels))
