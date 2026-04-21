"""
notifications/test_notifications.py
=====================================
Tests for notifications/gmail_alert.py

All SMTP and external calls are mocked.

Run from project root:
    pytest notifications/test_notifications.py -v
"""

import sys
import os
from unittest.mock import MagicMock, patch

import pytest

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


class TestGmailAlert:

    # ── Success path ──────────────────────────────────────────

    @patch("notifications.gmail_alert.smtplib.SMTP")
    @patch("notifications.gmail_alert.GMAIL_SENDER",      "sender@test.com")
    @patch("notifications.gmail_alert.GMAIL_APP_PASSWORD", "app-pass")
    @patch("notifications.gmail_alert.GMAIL_RECEIVER",    "recv@test.com")
    def test_send_alert_returns_true_on_success(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        from notifications.gmail_alert import send_alert
        result = send_alert({
            "severity": "critical", "category": "rescue",
            "description": "People trapped after earthquake",
            "disaster_type": "earthquake", "help_needed": "rescue",
            "lat": 26.0, "lng": 80.0, "flag": "verified"
        })
        assert result is True

    @patch("notifications.gmail_alert.smtplib.SMTP")
    @patch("notifications.gmail_alert.GMAIL_SENDER",      "sender@test.com")
    @patch("notifications.gmail_alert.GMAIL_APP_PASSWORD", "app-pass")
    @patch("notifications.gmail_alert.GMAIL_RECEIVER",    "recv@test.com")
    def test_send_alert_calls_send_message(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        from notifications.gmail_alert import send_alert
        send_alert({"severity": "high", "category": "food",
                    "description": "Hunger crisis in camp",
                    "disaster_type": "flood", "help_needed": "food",
                    "lat": 0.0, "lng": 0.0, "flag": "verified"})
        mock_server.send_message.assert_called_once()

    @patch("notifications.gmail_alert.smtplib.SMTP")
    @patch("notifications.gmail_alert.GMAIL_SENDER",      "sender@test.com")
    @patch("notifications.gmail_alert.GMAIL_APP_PASSWORD", "app-pass")
    @patch("notifications.gmail_alert.GMAIL_RECEIVER",    "recv@test.com")
    def test_send_alert_uses_starttls(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        from notifications.gmail_alert import send_alert
        send_alert({"severity": "medium"})
        mock_server.starttls.assert_called_once()

    @patch("notifications.gmail_alert.smtplib.SMTP")
    @patch("notifications.gmail_alert.GMAIL_SENDER",      "sender@test.com")
    @patch("notifications.gmail_alert.GMAIL_APP_PASSWORD", "app-pass")
    @patch("notifications.gmail_alert.GMAIL_RECEIVER",    "recv@test.com")
    def test_send_alert_logs_in_with_credentials(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        from notifications.gmail_alert import send_alert
        send_alert({"severity": "low"})
        mock_server.login.assert_called_once_with("sender@test.com", "app-pass")

    @patch("notifications.gmail_alert.smtplib.SMTP")
    @patch("notifications.gmail_alert.GMAIL_SENDER",      "sender@test.com")
    @patch("notifications.gmail_alert.GMAIL_APP_PASSWORD", "app-pass")
    @patch("notifications.gmail_alert.GMAIL_RECEIVER",    "recv@test.com")
    def test_send_alert_subject_contains_severity(self, mock_smtp):
        """The email subject should mention the severity level."""
        captured_msg = {}

        def capture_msg(msg):
            captured_msg["msg"] = msg

        mock_server = MagicMock()
        mock_server.send_message.side_effect = capture_msg
        mock_smtp.return_value.__enter__.return_value = mock_server

        from notifications.gmail_alert import send_alert
        send_alert({"severity": "CRITICAL"})

        assert "msg" in captured_msg
        assert "CRITICAL" in captured_msg["msg"]["Subject"]

    # ── Missing credentials ────────────────────────────────────

    @patch("notifications.gmail_alert.GMAIL_SENDER",      "")
    @patch("notifications.gmail_alert.GMAIL_APP_PASSWORD", "")
    def test_send_alert_skips_when_no_sender(self):
        from notifications.gmail_alert import send_alert
        result = send_alert({"severity": "high"})
        assert result is False

    @patch("notifications.gmail_alert.GMAIL_SENDER",      "sender@test.com")
    @patch("notifications.gmail_alert.GMAIL_APP_PASSWORD", "")
    def test_send_alert_skips_when_no_password(self):
        from notifications.gmail_alert import send_alert
        result = send_alert({"severity": "high"})
        assert result is False

    @patch("notifications.gmail_alert.GMAIL_SENDER",      None)
    @patch("notifications.gmail_alert.GMAIL_APP_PASSWORD", None)
    def test_send_alert_skips_when_none_credentials(self):
        from notifications.gmail_alert import send_alert
        result = send_alert({"severity": "high"})
        assert result is False

    # ── Error handling ────────────────────────────────────────

    @patch("notifications.gmail_alert.smtplib.SMTP")
    @patch("notifications.gmail_alert.GMAIL_SENDER",      "sender@test.com")
    @patch("notifications.gmail_alert.GMAIL_APP_PASSWORD", "app-pass")
    def test_send_alert_returns_false_on_smtp_error(self, mock_smtp):
        mock_smtp.side_effect = Exception("SMTP connection refused")
        from notifications.gmail_alert import send_alert
        result = send_alert({"severity": "critical"})
        assert result is False

    @patch("notifications.gmail_alert.smtplib.SMTP")
    @patch("notifications.gmail_alert.GMAIL_SENDER",      "sender@test.com")
    @patch("notifications.gmail_alert.GMAIL_APP_PASSWORD", "app-pass")
    def test_send_alert_returns_false_on_login_error(self, mock_smtp):
        mock_server = MagicMock()
        mock_server.login.side_effect = Exception("Authentication failed")
        mock_smtp.return_value.__enter__.return_value = mock_server
        from notifications.gmail_alert import send_alert
        result = send_alert({"severity": "high"})
        assert result is False

    # ── Payload robustness ────────────────────────────────────

    @patch("notifications.gmail_alert.smtplib.SMTP")
    @patch("notifications.gmail_alert.GMAIL_SENDER",      "sender@test.com")
    @patch("notifications.gmail_alert.GMAIL_APP_PASSWORD", "app-pass")
    @patch("notifications.gmail_alert.GMAIL_RECEIVER",    "recv@test.com")
    def test_send_alert_handles_empty_payload(self, mock_smtp):
        """send_alert should not raise even with an empty dict payload."""
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        from notifications.gmail_alert import send_alert
        try:
            result = send_alert({})
            assert result in (True, False)  # just must not raise
        except Exception as e:
            pytest.fail(f"send_alert raised unexpectedly: {e}")

    @patch("notifications.gmail_alert.smtplib.SMTP")
    @patch("notifications.gmail_alert.GMAIL_SENDER",      "sender@test.com")
    @patch("notifications.gmail_alert.GMAIL_APP_PASSWORD", "app-pass")
    @patch("notifications.gmail_alert.GMAIL_RECEIVER",    "recv@test.com")
    def test_send_alert_handles_none_severity(self, mock_smtp):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        from notifications.gmail_alert import send_alert
        result = send_alert({"severity": None, "category": "food"})
        assert result in (True, False)