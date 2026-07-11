from __future__ import annotations

from unittest.mock import MagicMock

from rad_device_watch.alerts import channels
from rad_device_watch.alerts.channels import EmailChannel, WebhookChannel


def test_email_channel_reads_password_from_named_environment(monkeypatch) -> None:
    smtp = MagicMock()
    smtp.__enter__.return_value = smtp
    monkeypatch.setenv("TEST_SMTP_PASSWORD", "runtime-secret")
    monkeypatch.setattr(channels.smtplib, "SMTP", lambda *_args: smtp)

    sent = EmailChannel().send(
        "Dose monitor alert",
        config={
            "smtp_server": "smtp.example.test",
            "smtp_port": 2525,
            "sender": "alerts@example.test",
            "recipients": ["reviewer@example.test"],
            "username": "alerts",
            "password_env": "TEST_SMTP_PASSWORD",
            "use_tls": False,
        },
    )

    assert sent is True
    smtp.login.assert_called_once_with("alerts", "runtime-secret")
    smtp.send_message.assert_called_once()


def test_email_channel_refuses_plaintext_password(monkeypatch) -> None:
    smtp = MagicMock()
    monkeypatch.setattr(channels.smtplib, "SMTP", smtp)

    sent = EmailChannel().send(
        "alert",
        config={
            "recipients": ["reviewer@example.test"],
            "password": "do-not-use",
        },
    )

    assert sent is False
    smtp.assert_not_called()


def test_webhook_template_renders_nested_values_without_json_replacement(monkeypatch) -> None:
    response = MagicMock()
    post = MagicMock(return_value=response)
    monkeypatch.setattr(channels.httpx, "post", post)
    message = 'Scanner said "offline"\nNeeds review'

    sent = WebhookChannel().send(
        message,
        config={
            "url": "https://example.test/hook",
            "payload_template": {
                "text": "{{message}}",
                "nested": ["prefix: {{message}}", 3],
            },
        },
    )

    assert sent is True
    payload = post.call_args.kwargs["json"]
    assert payload["text"] == message
    assert payload["nested"] == [f"prefix: {message}", 3]
    response.raise_for_status.assert_called_once_with()
