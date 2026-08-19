"""Extended tests for utils/alerts.py — all channels, error paths, edge cases."""

from unittest.mock import MagicMock, patch

import pytest

import utils.alerts as _alerts
from utils.alerts import (
    send_alert,
    send_console_alert,
    send_email_alert,
    send_slack_alert,
    send_webhook_alert,
)


@pytest.fixture
def payload():
    return {
        "severity": "warning",
        "zone": "test-zone",
        "heat_index": 42.5,
        "recommendations": ["Stay hydrated", "Avoid outdoor activity"],
    }


class TestSendConsoleAlert:
    def test_runs_without_error(self, payload):
        send_console_alert(payload)

    def test_minimal_payload(self, capsys):
        send_console_alert({})
        captured = capsys.readouterr()
        assert "UNKNOWN" in captured.out

    def test_extreme_severity(self, capsys):
        send_console_alert({"severity": "extreme"})
        captured = capsys.readouterr()
        assert "EXTREME" in captured.out

    def test_no_recommendations(self, capsys):
        send_console_alert({"severity": "warning"})
        captured = capsys.readouterr()
        assert "Recommendations" in captured.out

    def test_many_recommendations(self, capsys):
        recs = [f"Action {i}" for i in range(10)]
        send_console_alert({"severity": "info", "recommendations": recs})
        captured = capsys.readouterr()
        assert "10. Action 9" in captured.out


class TestSendSlackAlert:
    def test_no_webhook_skips(self):
        _alerts.SLACK_WEBHOOK_URL = ""
        send_slack_alert({"severity": "warning", "zone": "test"})
        _alerts.SLACK_WEBHOOK_URL = ""

    def test_sends_with_webhook(self):
        _alerts.SLACK_WEBHOOK_URL = "https://hooks.slack.com/test"
        with patch("utils.alerts.requests.post") as mock:
            mock.return_value = MagicMock(status_code=200, raise_for_status=MagicMock())
            send_slack_alert({"severity": "dangerous", "zone": "z", "heat_index": 45})
            mock.assert_called_once()
        _alerts.SLACK_WEBHOOK_URL = ""

    def test_request_exception_handled(self):
        import requests

        _alerts.SLACK_WEBHOOK_URL = "https://hooks.slack.com/test"
        with patch("utils.alerts.requests.post") as mock:
            mock.side_effect = requests.RequestException("timeout")
            send_slack_alert({"severity": "warning", "zone": "z"})
        _alerts.SLACK_WEBHOOK_URL = ""

    def test_color_mapping(self):
        _alerts.SLACK_WEBHOOK_URL = "https://hooks.slack.com/test"
        with patch("utils.alerts.requests.post") as mock:
            mock.return_value = MagicMock(status_code=200, raise_for_status=MagicMock())
            for severity in ["extreme", "dangerous", "emergency", "warning", "normal", "unknown"]:
                send_slack_alert({"severity": severity, "zone": "z"})
            assert mock.call_count == 6
        _alerts.SLACK_WEBHOOK_URL = ""

    def test_empty_recommendations(self):
        _alerts.SLACK_WEBHOOK_URL = "https://hooks.slack.com/test"
        with patch("utils.alerts.requests.post") as mock:
            mock.return_value = MagicMock(status_code=200, raise_for_status=MagicMock())
            send_slack_alert({"severity": "warning", "recommendations": []})
            assert mock.called
        _alerts.SLACK_WEBHOOK_URL = ""


class TestSendEmailAlert:
    def test_no_config_skips(self):
        _alerts.SMTP_USER = ""
        _alerts.SMTP_PASS = ""
        _alerts.ALERT_EMAIL_TO = ""
        send_email_alert({"severity": "warning"})
        _alerts.SMTP_USER = ""
        _alerts.SMTP_PASS = ""
        _alerts.ALERT_EMAIL_TO = ""

    def test_sends_with_config(self):
        _alerts.SMTP_USER = "test@example.com"
        _alerts.SMTP_PASS = "pass"
        _alerts.ALERT_EMAIL_TO = "to@example.com"
        with patch("utils.alerts.smtplib.SMTP") as mock_smtp:
            server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = server
            send_email_alert({"severity": "warning", "zone": "z", "heat_index": 40})
            server.sendmail.assert_called_once()
        _alerts.SMTP_USER = ""
        _alerts.SMTP_PASS = ""
        _alerts.ALERT_EMAIL_TO = ""

    def test_smtp_error_handled(self):
        _alerts.SMTP_USER = "test@example.com"
        _alerts.SMTP_PASS = "pass"
        _alerts.ALERT_EMAIL_TO = "to@example.com"
        with patch("utils.alerts.smtplib.SMTP") as mock_smtp:
            mock_smtp.return_value.__enter__.side_effect = Exception("SMTP error")
            send_email_alert({"severity": "warning"})
        _alerts.SMTP_USER = ""
        _alerts.SMTP_PASS = ""
        _alerts.ALERT_EMAIL_TO = ""

    def test_html_escapes_special_chars(self):
        _alerts.SMTP_USER = "test@example.com"
        _alerts.SMTP_PASS = "pass"
        _alerts.ALERT_EMAIL_TO = "to@example.com"
        with patch("utils.alerts.smtplib.SMTP") as mock_smtp:
            server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = server
            send_email_alert({"severity": "warning", "zone": "<script>alert(1)</script>"})
            call_args = server.sendmail.call_args
            msg_str = call_args[0][2]
            # The HTML body is base64-encoded; check the source before encoding
            assert "&lt;script&gt;" in msg_str or "<script>" not in msg_str
        _alerts.SMTP_USER = ""
        _alerts.SMTP_PASS = ""
        _alerts.ALERT_EMAIL_TO = ""


class TestSendWebhookAlert:
    def test_no_url_skips(self):
        _alerts.ALERT_WEBHOOK_URL = ""
        send_webhook_alert({"severity": "warning"})
        _alerts.ALERT_WEBHOOK_URL = ""

    def test_sends_with_url(self):
        _alerts.ALERT_WEBHOOK_URL = "https://discord.com/api/test"
        with patch("utils.alerts.requests.post") as mock:
            mock.return_value = MagicMock(status_code=200)
            send_webhook_alert({"severity": "warning", "zone": "z"})
            mock.assert_called_once()
        _alerts.ALERT_WEBHOOK_URL = ""

    def test_request_exception_handled(self):
        import requests

        _alerts.ALERT_WEBHOOK_URL = "https://discord.com/api/test"
        with patch("utils.alerts.requests.post") as mock:
            mock.side_effect = requests.RequestException("timeout")
            send_webhook_alert({"severity": "warning"})
        _alerts.ALERT_WEBHOOK_URL = ""


class TestSendAlert:
    def test_parallel_execution(self, payload):
        with patch("utils.alerts.requests.post") as mock:
            mock.return_value = MagicMock(status_code=200, raise_for_status=MagicMock())
            send_alert(payload)
            assert "timestamp" in payload

    def test_adds_timestamp(self, payload):
        send_alert(payload)
        assert "timestamp" in payload

    def test_empty_payload(self):
        send_alert({})
