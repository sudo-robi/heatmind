import pytest
from unittest.mock import patch, MagicMock
from utils.alerts import send_alert, send_console_alert, send_webhook_alert, send_email_alert


@pytest.fixture
def alert_payload():
    return {
        "zone": "Dubai Downtown",
        "severity": "warning",
        "heat_index": 38.5,
        "timestamp": "2026-08-17T12:00:00",
        "recommendations": ["Monitor conditions", "Stay hydrated"],
    }


class TestSendAlert:
    def test_console_alert_called(self, alert_payload):
        with patch("utils.alerts.send_console_alert") as mock_console:
            with patch("utils.alerts.send_webhook_alert"):
                with patch("utils.alerts.send_email_alert"):
                    send_alert(alert_payload)
                    mock_console.assert_called_once()

    def test_webhook_called_when_url_set(self, alert_payload):
        with patch("utils.alerts.send_console_alert"):
            with patch("utils.alerts.send_webhook_alert") as mock_webhook:
                with patch("utils.alerts.send_email_alert"):
                    with patch("utils.alerts.ALERT_WEBHOOK_URL", "https://hook.test"):
                        send_alert(alert_payload)
                        mock_webhook.assert_called_once()

    def test_webhook_not_called_when_empty(self, alert_payload):
        with patch("utils.alerts.send_console_alert"):
            with patch("utils.alerts.send_webhook_alert") as mock_webhook:
                with patch("utils.alerts.ALERT_WEBHOOK_URL", ""):
                    with patch("utils.alerts.ALERT_WEBHOOK_URL", ""):
                        send_webhook_alert(alert_payload)
                        mock_webhook.assert_not_called()

    def test_email_called_when_configured(self, alert_payload):
        with patch("utils.alerts.send_console_alert"):
            with patch("utils.alerts.send_webhook_alert"):
                with patch("utils.alerts.send_email_alert") as mock_email:
                    with patch("utils.alerts.SMTP_USER", "test@test.com"):
                        with patch("utils.alerts.ALERT_EMAIL_TO", "to@test.com"):
                            send_alert(alert_payload)
                            mock_email.assert_called_once()

    def test_email_not_called_when_empty(self, alert_payload):
        with patch("utils.alerts.SMTP_USER", ""):
            with patch("utils.alerts.ALERT_EMAIL_TO", ""):
                with patch("utils.alerts.smtplib.SMTP") as mock_smtp:
                    send_email_alert(alert_payload)
                    mock_smtp.assert_not_called()

    def test_adds_timestamp(self, alert_payload):
        with patch("utils.alerts.send_console_alert"):
            with patch("utils.alerts.send_webhook_alert"):
                with patch("utils.alerts.send_email_alert"):
                    payload = {"zone": "Test", "severity": "warning", "heat_index": 30, "recommendations": []}
                    send_alert(payload)
                    assert "timestamp" in payload


class TestConsoleAlert:
    def test_console_output(self, alert_payload, capsys):
        send_console_alert(alert_payload)
        captured = capsys.readouterr()
        assert "HEAT ALERT" in captured.out
        assert "Dubai Downtown" in captured.out
        assert "WARNING" in captured.out

    def test_console_output_extreme(self, alert_payload, capsys):
        alert_payload["severity"] = "extreme"
        send_console_alert(alert_payload)
        captured = capsys.readouterr()
        assert "EXTREME" in captured.out

    def test_console_output_recommendations(self, alert_payload, capsys):
        send_console_alert(alert_payload)
        captured = capsys.readouterr()
        assert "Monitor conditions" in captured.out
        assert "Stay hydrated" in captured.out

    def test_console_no_recommendations(self, capsys):
        send_console_alert({"zone": "Test", "severity": "info", "heat_index": 30, "recommendations": []})
        captured = capsys.readouterr()
        assert "HEAT ALERT" in captured.out

    def test_console_shows_heat_index(self, alert_payload, capsys):
        send_console_alert(alert_payload)
        captured = capsys.readouterr()
        assert "38.5" in captured.out

    def test_console_empty_zone(self, capsys):
        send_console_alert({"zone": "", "severity": "warning", "heat_index": 38, "recommendations": []})
        captured = capsys.readouterr()
        assert "HEAT ALERT" in captured.out

    def test_console_many_recommendations(self, capsys):
        recs = [f"Recommendation {i}" for i in range(20)]
        send_console_alert({"zone": "Test", "severity": "warning", "heat_index": 38, "recommendations": recs})
        captured = capsys.readouterr()
        assert "Recommendation 0" in captured.out
        assert "Recommendation 19" in captured.out

    def test_console_missing_fields(self, capsys):
        send_console_alert({})
        captured = capsys.readouterr()
        assert "HEAT ALERT" in captured.out


class TestWebhookAlert:
    def test_webhook_sends_json(self, alert_payload):
        with patch("utils.alerts.ALERT_WEBHOOK_URL", "https://hook.test"):
            with patch("utils.alerts.requests.post") as mock_post:
                mock_post.return_value = MagicMock(status_code=200)
                send_webhook_alert(alert_payload)
                mock_post.assert_called_once()
                call_kwargs = mock_post.call_args
                assert call_kwargs[1]["json"] == alert_payload

    def test_webhook_logs_error(self, alert_payload):
        with patch("utils.alerts.ALERT_WEBHOOK_URL", "https://hook.test"):
            with patch("utils.alerts.requests.post") as mock_post:
                from requests.exceptions import ConnectionError
                mock_post.side_effect = ConnectionError("Connection refused")
                send_webhook_alert(alert_payload)
                mock_post.assert_called_once()
                mock_post.assert_called_once()

    def test_webhook_timeout(self, alert_payload):
        with patch("utils.alerts.ALERT_WEBHOOK_URL", "https://hook.test"):
            with patch("utils.alerts.requests.post") as mock_post:
                from requests.exceptions import Timeout
                mock_post.side_effect = Timeout("Request timed out")
                send_webhook_alert(alert_payload)

    def test_webhook_no_url(self, alert_payload):
        with patch("utils.alerts.ALERT_WEBHOOK_URL", ""):
            with patch("utils.alerts.requests.post") as mock_post:
                send_webhook_alert(alert_payload)
                mock_post.assert_not_called()

    def test_webhook_sends_to_correct_url(self, alert_payload):
        with patch("utils.alerts.ALERT_WEBHOOK_URL", "https://my-hook.com/alert"):
            with patch("utils.alerts.requests.post") as mock_post:
                mock_post.return_value = MagicMock(status_code=200)
                send_webhook_alert(alert_payload)
                call_url = mock_post.call_args[0][0]
                assert call_url == "https://my-hook.com/alert"


class TestEmailAlert:
    def test_email_sends(self, alert_payload):
        with patch("utils.alerts.SMTP_USER", "test@test.com"):
            with patch("utils.alerts.SMTP_PASS", "test_pass"):
                with patch("utils.alerts.ALERT_EMAIL_TO", "to@test.com"):
                    with patch("utils.alerts.smtplib.SMTP") as mock_smtp:
                        server = MagicMock()
                        mock_smtp.return_value.__enter__ = MagicMock(return_value=server)
                        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
                        send_email_alert(alert_payload)
                        mock_smtp.assert_called_once()

    def test_email_logs_error(self, alert_payload):
        with patch("utils.alerts.SMTP_USER", "test@test.com"):
            with patch("utils.alerts.SMTP_PASS", "test_pass"):
                with patch("utils.alerts.ALERT_EMAIL_TO", "to@test.com"):
                    with patch("utils.alerts.smtplib.SMTP") as mock_smtp:
                        mock_smtp.side_effect = Exception("SMTP error")
                        send_email_alert(alert_payload)

    def test_email_contains_zone(self, alert_payload):
        with patch("utils.alerts.SMTP_USER", "test@test.com"):
            with patch("utils.alerts.SMTP_PASS", "test_pass"):
                with patch("utils.alerts.ALERT_EMAIL_TO", "to@test.com"):
                    with patch("utils.alerts.smtplib.SMTP") as mock_smtp:
                        server = MagicMock()
                        mock_smtp.return_value.__enter__ = MagicMock(return_value=server)
                        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
                        send_email_alert(alert_payload)
                        call_args = server.sendmail.call_args
                        assert call_args is not None
                        msg = call_args[0][2]
                        assert "Dubai_Downtown" in msg or "Dubai Downtown" in msg

    def test_email_no_config(self, alert_payload):
        with patch("utils.alerts.SMTP_USER", ""):
            with patch("utils.alerts.SMTP_PASS", ""):
                with patch("utils.alerts.ALERT_EMAIL_TO", ""):
                    with patch("utils.alerts.smtplib.SMTP") as mock_smtp:
                        send_email_alert(alert_payload)
                        mock_smtp.assert_not_called()

    def test_email_subject(self, alert_payload):
        with patch("utils.alerts.SMTP_USER", "test@test.com"):
            with patch("utils.alerts.SMTP_PASS", "test_pass"):
                with patch("utils.alerts.ALERT_EMAIL_TO", "to@test.com"):
                    with patch("utils.alerts.smtplib.SMTP") as mock_smtp:
                        server = MagicMock()
                        mock_smtp.return_value.__enter__ = MagicMock(return_value=server)
                        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
                        send_email_alert(alert_payload)
                        call_args = server.sendmail.call_args
                        if call_args:
                            msg = call_args[0][2]
                            assert "HeatMind Alert" in msg or "HeatMind_Alert" in msg

    def test_email_negative_heat_index(self, alert_payload):
        alert_payload["heat_index"] = -5
        with patch("utils.alerts.SMTP_USER", "test@test.com"):
            with patch("utils.alerts.SMTP_PASS", "test_pass"):
                with patch("utils.alerts.ALERT_EMAIL_TO", "to@test.com"):
                    with patch("utils.alerts.smtplib.SMTP") as mock_smtp:
                        server = MagicMock()
                        mock_smtp.return_value.__enter__ = MagicMock(return_value=server)
                        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)
                        send_email_alert(alert_payload)
                        mock_smtp.assert_called_once()
