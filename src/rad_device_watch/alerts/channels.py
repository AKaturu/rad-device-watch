from __future__ import annotations

import logging
import os
import smtplib
import ssl
from email.message import EmailMessage
from typing import Protocol

import httpx

logger = logging.getLogger(__name__)
DEFAULT_SMTP_PASSWORD_ENV = "RAD_DEVICE_WATCH_SMTP_PASSWORD"


class AlertChannel(Protocol):
    def send(self, message: str, config: dict | None = None) -> bool: ...


class ConsoleChannel:
    def send(self, message: str, config: dict | None = None) -> bool:
        logger.warning("ALERT: %s", message)
        print(f"[ALERT] {message}")
        return True


class EmailChannel:
    def send(self, message: str, config: dict | None = None) -> bool:
        cfg = config or {}
        smtp_server = cfg.get("smtp_server", "localhost")
        smtp_port = cfg.get("smtp_port", 587)
        sender = cfg.get("sender", "rad-device-watch@localhost")
        recipients = cfg.get("recipients", [])
        username = cfg.get("username")
        if "password" in cfg:
            logger.error("Email alert refused: plaintext SMTP passwords are not supported")
            return False
        password_env = str(cfg.get("password_env") or DEFAULT_SMTP_PASSWORD_ENV)
        password = os.getenv(password_env)
        use_tls = cfg.get("use_tls", True)

        if isinstance(recipients, str):
            recipients = [r.strip() for r in recipients.split(",")]

        if not recipients:
            logger.warning("Email alert skipped: no recipients configured")
            return False
        if username and not password:
            logger.warning("Email alert skipped: SMTP password environment variable %s is unset", password_env)
            return False

        msg = EmailMessage()
        msg["Subject"] = "[rad-device-watch] Alert"
        msg["From"] = sender
        msg["To"] = ", ".join(recipients)
        msg.set_content(message)

        try:
            context = ssl.create_default_context() if use_tls else None
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                if use_tls:
                    server.starttls(context=context)
                if username and password:
                    server.login(username, password)
                server.send_message(msg)
            logger.info("Email alert sent to %s", recipients)
            return True
        except Exception as exc:
            logger.error("Failed to send email alert: %s", exc)
            return False


class SlackChannel:
    def send(self, message: str, config: dict | None = None) -> bool:
        cfg = config or {}
        webhook_url = cfg.get("webhook_url", "")
        if not webhook_url:
            logger.warning("Slack alert skipped: no webhook_url configured")
            return False
        try:
            resp = httpx.post(webhook_url, json={"text": message}, timeout=10)
            resp.raise_for_status()
            logger.info("Slack alert sent")
            return True
        except Exception as exc:
            logger.error("Failed to send Slack alert: %s", exc)
            return False


class WebhookChannel:
    def send(self, message: str, config: dict | None = None) -> bool:
        cfg = config or {}
        url = cfg.get("url", "")
        if not url:
            logger.warning("Webhook alert skipped: no url configured")
            return False
        headers = cfg.get("headers", {"Content-Type": "application/json"})
        payload = cfg.get("payload_template", {"text": "{{message}}"})
        rendered = _render_payload(payload, message)
        try:
            resp = httpx.post(url, json=rendered, headers=headers, timeout=10)
            resp.raise_for_status()
            logger.info("Webhook alert sent to %s", url)
            return True
        except Exception as exc:
            logger.error("Failed to send webhook alert: %s", exc)
            return False


def get_channel(name: str) -> AlertChannel:
    mapping: dict[str, AlertChannel] = {
        "console": ConsoleChannel(),
        "email": EmailChannel(),
        "slack": SlackChannel(),
        "webhook": WebhookChannel(),
    }
    return mapping.get(name, ConsoleChannel())


def _render_payload(value: object, message: str) -> object:
    """Render message placeholders without serializing and reparsing JSON."""
    if isinstance(value, str):
        return value.replace("{{message}}", message)
    if isinstance(value, list):
        return [_render_payload(item, message) for item in value]
    if isinstance(value, dict):
        return {key: _render_payload(item, message) for key, item in value.items()}
    return value
